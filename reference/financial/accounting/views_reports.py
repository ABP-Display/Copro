'''
Describe report accounting viewer for Django

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals
import sys
import re
from datetime import date, datetime
from logging import getLogger

from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.db.models.aggregates import Sum
from django.utils import formats

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, CLOSE_NO, FORMTYPE_REFRESH, WrapAction, convert_date, ActionsManage, SELECT_MULTI, \
    FORMTYPE_MODAL, SELECT_SINGLE
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompImage, XferCompSelect, XferCompLabelForm, XferCompGrid, XferCompEdit, XferCompCheck, XferCompDate
from lucterios.framework.xferadvance import TITLE_PRINT, TITLE_CLOSE, TITLE_EDIT
from lucterios.framework.xferbasic import NULL_VALUE
from lucterios.contacts.models import LegalEntity
from lucterios.CORE.parameters import Params
from lucterios.CORE.xferprint import XferPrintAction

from diacamma.accounting.models import FiscalYear, EntryLineAccount, ChartsAccount, CostAccounting, Third, EntryAccount
from diacamma.accounting.tools import correct_accounting_code, current_system_account, format_with_devise
from diacamma.accounting.tools_reports import get_spaces, convert_query_to_account, add_cell_in_grid, fill_grid, add_item_in_grid
from diacamma.accounting.views_entries import add_fiscalyear_result

MenuManage.add_sub("bookkeeping_report", "financial", short_icon='mdi:mdi-bank-check', caption=_("Reports"), desc=_("Report of Bookkeeping"), pos=30)


class FiscalYearReport(XferContainerCustom):
    short_icon = 'mdi:mdi-finance'
    model = FiscalYear
    field_id = 'year'
    add_filtering = False
    force_date_filter = False
    saving_pdfreport = False
    methods_allowed = ('GET', )

    def __init__(self, **kwargs):
        XferContainerCustom.__init__(self, **kwargs)
        self.filter = None
        self.lastfilter = None
        self.budgetfilter_left = None
        self.budgetfilter_right = None
        self.total_summary_left = (0, 0, 0)
        self.total_summary_right = (0, 0, 0)
        self.result = (0, 0, 0)
        self.line_offset = 0
        hfield = format_with_devise(5).split(';')
        self.format_str = ";".join(hfield[1:])
        self.hfield = hfield[0]
        self.budgetfilter_right = Q()
        self.budgetfilter_left = Q()
        self.account_codes_left = []
        self.account_codes_right = []

    def fillresponse(self):
        self.fill_header()
        self.calcul_table()
        self.fill_body()
        self.fill_buttons()

    def define_gridheader(self):
        pass

    def fill_filterheader(self):
        pass

    def fill_filterCode(self):
        if self.add_filtering:
            self.filtercode = self.getparam('filtercode', Params.getvalue("accounting-code-report-filter"))
            edt = XferCompEdit('filtercode')
            edt.set_value(self.filtercode)
            edt.is_default = True
            edt.description = _("accounting code starting with")
            edt.set_location(1, 3, 3)
            edt.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
            self.add_component(edt)
            if self.filtercode != '':
                self.filter &= Q(account__code__startswith=self.filtercode)

    def fill_header(self):
        self.item = FiscalYear.get_current(self.getparam("year"))
        new_begin = convert_date(self.getparam("begin"), self.item.begin)
        new_end = convert_date(self.getparam("end"), self.item.end)
        if (new_begin >= self.item.begin) and (new_end <= self.item.end):
            self.item.begin = new_begin
            self.item.end = new_end
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 3)
        self.add_component(img)

        select_year = XferCompSelect(self.field_id)
        select_year.set_location(1, 0, 5)
        select_year.set_select_query(FiscalYear.objects.all())
        select_year.set_value(self.item.id)
        select_year.set_needed(True)
        select_year.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(select_year)
        self.filter = Q(entry__year=self.item)
        if self.force_date_filter or self.item.status != 2:
            self.fill_from_model(1, 1, False, ['begin'])
            self.fill_from_model(3, 1, False, ['end'])
            begin_filter = self.get_components('begin')
            begin_filter.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
            end_filter = self.get_components('end')
            end_filter.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
            self.filter &= Q(entry__date_value__gte=self.item.begin)
            self.filter &= Q(entry__date_value__lte=self.item.end)
        self.fill_filterCode()
        add_fiscalyear_result(self, 0, 8, 6, self.item, 'result')
        self.fill_filterheader()
        self.define_gridheader()

    def _compute_result_get_position(self, total_in_left, total1_left, total2_left, totalb_left, total1_right, total2_right, totalb_right):
        result_n = total1_right - total1_left
        if (total2_left is not None) and (total2_right is not None):
            result_n_1 = total2_right - total2_left
        else:
            result_n_1 = 0.0
        if (totalb_left is not None) and (totalb_right is not None):
            result_b = totalb_right - totalb_left
        else:
            result_b = 0.0
        self.result = result_n, result_n_1, result_b
        if total_in_left:
            if result_n > 0:
                pos_n = 'left_n'
            else:
                pos_n = 'right_n'
            if result_n_1 > 0:
                pos_n_1 = 'left_n_1'
            else:
                pos_n_1 = 'right_n_1'
            if result_b > 0:
                pos_b = 'left_b'
            else:
                pos_b = 'right_b'
        else:
            result_n = -1 * result_n
            result_n_1 = -1 * result_n_1
            if result_n > 0:
                pos_n = 'right_n'
            else:
                pos_n = 'left_n'
            if result_n_1 > 0:
                pos_n_1 = 'right_n_1'
            else:
                pos_n_1 = 'left_n_1'
            if result_b > 0:
                pos_b = 'right_b'
            else:
                pos_b = 'left_b'
        return pos_n, pos_n_1, pos_b

    def _add_result_line(self, totalb_left, line_idx, pos_n, pos_n_1, pos_b):
        add_cell_in_grid(self.grid, self.line_offset + line_idx, pos_n, abs(self.result[0]))
        if (totalb_left is not None) and (abs(self.result[2]) > 0.0001):
            add_cell_in_grid(self.grid, self.line_offset + line_idx, pos_b, abs(self.result[2]))
        else:
            pos_b = ""
        if (self.lastfilter is not None) and (abs(self.result[1]) > 0.0001):
            add_cell_in_grid(self.grid, self.line_offset + line_idx, pos_n_1, abs(self.result[1]))
        else:
            pos_n_1 = ""
        if (pos_n != 'left_n') and (pos_n_1 != 'left_n_1') and (pos_b != 'left_b'):
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left', '')
        if (pos_n != 'right_n') and (pos_n_1 != 'right_n_1') and (pos_b != 'right_b'):
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right', '')

    def add_total_in_grid(self, total_in_left, total1_left, total2_left, totalb_left, total1_right, total2_right, totalb_right, line_idx):
        self.result = (0.0, 0.0, 0.0)
        if (total2_left is None) or (total2_right is None):
            self.total_summary_left = (max(total1_left, total1_right), None, max(totalb_left, totalb_right))
            self.total_summary_right = (max(total1_left, total1_right), None, max(totalb_left, totalb_right))
        else:
            self.total_summary_left = (total1_left, total2_left, totalb_left)
            self.total_summary_right = (total1_right, total2_right, totalb_right)
        line_idx += 1
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left', '')
        line_idx += 1
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % _('total'))
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left_n', total1_left, "{[u]}{[b]}%s{[/b]}{[/u]}")
        if self.lastfilter is not None:
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left_n_1', total2_left, "{[u]}{[b]}%s{[/b]}{[/u]}")
        if self.budgetfilter_left is not None:
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left_b', totalb_left, "{[u]}{[b]}%s{[/b]}{[/u]}")
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % _('total'))
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right_n', total1_right, "{[u]}{[b]}%s{[/b]}{[/u]}")
        if self.lastfilter is not None:
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right_n_1', total2_right, "{[u]}{[b]}%s{[/b]}{[/u]}")
        if self.budgetfilter_right is not None:
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right_b', totalb_right, "{[u]}{[b]}%s{[/b]}{[/u]}")
        if (abs(total1_left - total1_right) > 0.0001) or ((total2_left is not None) and (total2_right is not None) and (abs(total2_left - total2_right) > 0.0001)):
            line_idx += 1
            if total_in_left:
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % _('result (profit)'))
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right', get_spaces(5) + "{[i]}%s{[/i]}" % _('result (deficit)'))
            else:
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % _('result (deficit)'))
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right', get_spaces(5) + "{[i]}%s{[/i]}" % _('result (profit)'))
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right_n', '')
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right_n_1', '')
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'right_b', '')
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left_n', '')
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left_n_1', '')
            add_cell_in_grid(self.grid, self.line_offset + line_idx, 'left_b', '')
            pos_n, pos_n_1, pos_b = self._compute_result_get_position(total_in_left, total1_left, total2_left, totalb_left, total1_right, total2_right, totalb_right)
            self._add_result_line(totalb_left, line_idx, pos_n, pos_n_1, pos_b)
        return line_idx

    def _add_left_right_accounting(self, left_filter, rigth_filter, total_in_left):
        data_line_left, total1_left, total2_left, totalb_left, self.account_codes_left = convert_query_to_account(
            self.filter & left_filter, self.lastfilter & left_filter if self.lastfilter is not None else None, self.budgetfilter_left)
        data_line_right, total1_right, total2_right, totalb_right, self.account_codes_right = convert_query_to_account(
            self.filter & rigth_filter, self.lastfilter & rigth_filter if self.lastfilter is not None else None, self.budgetfilter_right)
        line_idx = 0
        for line_idx in range(max(len(data_line_left), len(data_line_right))):
            if line_idx < len(data_line_left):
                add_item_in_grid(self.grid, self.line_offset + line_idx, 'left', data_line_left[line_idx])
            if line_idx < len(data_line_right):
                add_item_in_grid(self.grid, self.line_offset + line_idx, 'right', data_line_right[line_idx])
        return self.add_total_in_grid(total_in_left, total1_left, total2_left, totalb_left, total1_right, total2_right, totalb_right, line_idx)

    def calcul_rubric(self, left_line_idx, right_line_idx, left_filter, rigth_filter, rubric_name):
        rubric_title = rubric_name if rubric_name != '' else _('others')
        rubric_filter = Q(account__rubric=rubric_name)
        data_line_left, subtotal1_left, subtotal2_left, subtotalb_left, account_codes_left = convert_query_to_account(self.filter & left_filter & rubric_filter, self.lastfilter & left_filter if self.lastfilter is not None else None, self.budgetfilter_left, old_accountcode=self.account_codes_left if rubric_name == '' else None)
        if len(data_line_left) > 0:
            add_cell_in_grid(self.grid, self.line_offset + left_line_idx, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % rubric_title)
            left_line_idx += 1
            left_line_idx = fill_grid(self.grid, self.line_offset + left_line_idx, 'left', data_line_left)
            add_item_in_grid(self.grid, self.line_offset + left_line_idx, 'left', (get_spaces(10) + "%s" % _('Sub-total'), subtotal1_left, subtotal2_left, subtotalb_left), "{[i]}%s{[/i]}")
            left_line_idx += 1
            add_cell_in_grid(self.grid, self.line_offset + left_line_idx, 'left', '')
            left_line_idx += 1
        data_line_right, subtotal1_right, subtotal2_right, subtotalb_right, account_codes_right = convert_query_to_account(self.filter & rigth_filter & rubric_filter, self.lastfilter & rigth_filter if self.lastfilter is not None else None, self.budgetfilter_right, old_accountcode=self.account_codes_right if rubric_name == '' else None)
        if len(data_line_right) > 0:
            add_cell_in_grid(self.grid, self.line_offset + right_line_idx, 'right', get_spaces(5) + "{[i]}%s{[/i]}" % rubric_title)
            right_line_idx += 1
            right_line_idx = fill_grid(self.grid, self.line_offset + right_line_idx, 'right', data_line_right)
            add_item_in_grid(self.grid, self.line_offset + right_line_idx, 'right', (get_spaces(10) + "%s" % _('Sub-total'), subtotal1_right, subtotal2_right, subtotalb_right), "{[i]}%s{[/i]}")
            right_line_idx += 1
            add_cell_in_grid(self.grid, self.line_offset + right_line_idx, 'right', '')
            right_line_idx += 1
        self.account_codes_left.extend(account_codes_left)
        self.account_codes_right.extend(account_codes_right)
        self.total_summary_left = (self.total_summary_left[0] + subtotal1_left, self.total_summary_left[1] + subtotal2_left, self.total_summary_left[2] + subtotalb_left)
        self.total_summary_right = (self.total_summary_right[0] + subtotal1_right, self.total_summary_right[1] + subtotal2_right, self.total_summary_right[2] + subtotalb_right)
        return left_line_idx, right_line_idx

    def _add_left_right_accounting_with_rubric(self, left_filter, rigth_filter, total_in_left, rubric_names):
        left_line_idx, right_line_idx = 0, 0
        for rubric_name in rubric_names:
            left_line_idx, right_line_idx = self.calcul_rubric(left_line_idx, right_line_idx, left_filter, rigth_filter, rubric_name)
        left_line_idx, right_line_idx = self.calcul_rubric(left_line_idx, right_line_idx, left_filter, rigth_filter, "")
        total1_left, total2_left, totalb_left = self.total_summary_left
        total1_right, total2_right, totalb_right = self.total_summary_right
        line_idx = self.add_total_in_grid(total_in_left, total1_left, total2_left, totalb_left, total1_right, total2_right, totalb_right, max(left_line_idx, right_line_idx))
        return line_idx

    def calcul_table(self):
        pass

    def fill_body(self):
        self.grid.no_pager = True
        self.grid.set_location(0, 10, 6)
        self.grid.set_height(500)
        self.add_component(self.grid)

    def fill_buttons(self):
        self.add_action(FiscalYearReportPrint.get_action(TITLE_PRINT, short_icon='mdi:mdi-printer-outline'),
                        close=CLOSE_NO, params={'classname': self.__class__.__name__})
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@MenuManage.describ('accounting.change_fiscalyear', FORMTYPE_NOMODAL, 'bookkeeping_report', _('Show balance sheet for current fiscal year'))
class FiscalYearBalanceSheet(FiscalYearReport):
    caption = _("Balance sheet")
    saving_pdfreport = True

    def fill_filterheader(self):
        if self.item.last_fiscalyear is not None:
            self.lastfilter = Q(entry__year=self.item.last_fiscalyear)
            lbl = XferCompLabelForm('sep_last')
            lbl.set_value("{[br/]}{[br/]}")
            lbl.set_location(2, 11, 3)
            self.add_component(lbl)
            lbl = XferCompLabelForm('lbllast_year')
            lbl.set_value_as_name(self.item.last_fiscalyear.get_identify())
            lbl.set_location(1, 12)
            self.add_component(lbl)
            lbl = XferCompLabelForm('last_year')
            lbl.set_value(str(self.item.last_fiscalyear))
            lbl.set_location(2, 12, 4)
            self.add_component(lbl)
            add_fiscalyear_result(self, 0, 13, 6, self.item.last_fiscalyear, 'last_result')

    def define_gridheader(self):
        self.grid = XferCompGrid('report_%d' % self.item.id)
        self.grid.add_header('left', _('Assets'))
        self.grid.add_header('left_n', self.item.get_identify(), self.hfield, 0, self.format_str)
        if self.lastfilter is not None:
            self.grid.add_header('left_n_1', self.item.last_fiscalyear.get_identify(), self.hfield, 0, self.format_str)
        self.grid.add_header('space', '')
        self.grid.add_header('right', _('Liabilities'))
        self.grid.add_header('right_n', self.item.get_identify(), self.hfield, 0, self.format_str)
        if self.lastfilter is not None:
            self.grid.add_header('right_n_1', self.item.last_fiscalyear.get_identify(), self.hfield, 0, self.format_str)

    def calcul_table(self):
        current_system_account().fill_fiscalyear_balancesheet(self.grid, self.filter, self.lastfilter)


@MenuManage.describ('accounting.change_fiscalyear', FORMTYPE_NOMODAL, 'bookkeeping_report', _('Show income statement for current fiscal year'))
class FiscalYearIncomeStatement(FiscalYearReport):
    caption = _("Income statement")
    saving_pdfreport = True

    def define_gridheader(self):
        self.grid = XferCompGrid('report_%d' % self.item.id)
        self.grid.add_header('left', _('Expense'))
        self.grid.add_header('left_n', self.item.get_identify(), self.hfield, 0, self.format_str)
        self.grid.add_header('left_b', _('Budget'), self.hfield, 0, self.format_str)
        if self.lastfilter is not None:
            self.grid.add_header('left_n_1', self.item.last_fiscalyear.get_identify(), self.hfield, 0, self.format_str)
        self.grid.add_header('space', '')
        self.grid.add_header('right', _('Revenue'))
        self.grid.add_header('right_n', self.item.get_identify(), self.hfield, 0, self.format_str)
        self.grid.add_header('right_b', _('Budget'), self.hfield, 0, self.format_str)
        if self.lastfilter is not None:
            self.grid.add_header('right_n_1', self.item.last_fiscalyear.get_identify(), self.hfield, 0, self.format_str)

    def get_rubric_list(self):
        return self.item.get_rubric_list(type_of_account=(3, 4))

    def select_rubric(self):
        self.rubric_names = self.get_rubric_list()
        if len(self.rubric_names) > 0:
            with_rubric = self.getparam("with_rubric", True)
            check = XferCompCheck('with_rubric')
            check.set_value(with_rubric)
            check.set_location(1, 6, 2)
            check.description = _('show with rubrics')
            check.set_action(self.request, self.get_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(check)
            if not with_rubric:
                self.rubric_names = []

    def fill_filterheader(self):
        self.select_rubric()
        if self.item.last_fiscalyear is not None:
            self.lastfilter = Q(entry__year=self.item.last_fiscalyear)
            lbl = XferCompLabelForm('sep_last')
            lbl.set_value("{[br/]}{[br/]}")
            lbl.set_location(2, 11, 3)
            self.add_component(lbl)
            lbl = XferCompLabelForm('lbllast_year')
            lbl.set_value_as_name(self.item.last_fiscalyear.get_identify())
            lbl.set_location(1, 12)
            self.add_component(lbl)
            lbl = XferCompLabelForm('last_year')
            lbl.set_value(str(self.item.last_fiscalyear))
            lbl.set_location(2, 12, 4)
            self.add_component(lbl)
            add_fiscalyear_result(self, 0, 13, 6, self.item.last_fiscalyear, "last_result")

    def show_annexe(self, line_idx, budgetfilter, excludefilter):
        add_cell_in_grid(self.grid, self.line_offset + line_idx + 1, 'left', '')
        other_filter = Q(account__code__regex=current_system_account().get_annexe_mask()) & ~excludefilter
        budget_other = Q(code__regex=current_system_account().get_annexe_mask())
        data_line_left, anx_total1_left, anx_total2_left, anx_totalb_left, _account_codes_left = convert_query_to_account(self.filter & other_filter,
                                                                                                                          self.lastfilter & other_filter if self.lastfilter is not None else None,
                                                                                                                          budgetfilter & budget_other,
                                                                                                                          sign_value=-1)
        data_line_right, anx_total1_right, anx_total2_right, anx_totalb_right, _account_codes_right = convert_query_to_account(self.filter & other_filter,
                                                                                                                               self.lastfilter & other_filter if self.lastfilter is not None else None,
                                                                                                                               budgetfilter & budget_other,
                                                                                                                               sign_value=1)
        if (len(data_line_left) > 0) or (len(data_line_right) > 0):
            add_cell_in_grid(self.grid, self.line_offset + line_idx + 1, 'left', get_spaces(20) + "{[i]}%s{[/i]}" % _('annexe'))
            add_cell_in_grid(self.grid, self.line_offset + line_idx + 1, 'right', get_spaces(20) + "{[i]}%s{[/i]}" % _('annexe'))
            left_line_idx = fill_grid(self.grid, self.line_offset + line_idx + 2, 'left', data_line_left)
            right_line_idx = fill_grid(self.grid, self.line_offset + line_idx + 2, 'right', data_line_right)
            max_line_idx = max(left_line_idx, right_line_idx)
            total1_left, total2_left, totalb_left = self.total_summary_left
            total1_right, total2_right, totalb_right = self.total_summary_right
            total1_left += anx_total1_left
            total1_right += anx_total1_right
            add_cell_in_grid(self.grid, max_line_idx, 'left', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % _('total with annexe'))
            add_cell_in_grid(self.grid, max_line_idx, 'right', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % _('total with annexe'))
            add_cell_in_grid(self.grid, max_line_idx, 'left_n', max(total1_left, total1_right), "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, max_line_idx, 'right_n', max(total1_left, total1_right), "{[u]}{[b]}%s{[/b]}{[/u]}")
            if self.lastfilter is not None:
                total2_left += anx_total2_left
                total2_right += anx_total2_right
                add_cell_in_grid(self.grid, max_line_idx, 'left_n_1', max(total2_left, total2_right), "{[u]}{[b]}%s{[/b]}{[/u]}")
                add_cell_in_grid(self.grid, max_line_idx, 'right_n_1', max(total2_left, total2_right), "{[u]}{[b]}%s{[/b]}{[/u]}")
            if self.budgetfilter_left is not None:
                totalb_left += anx_totalb_left
                totalb_right += anx_totalb_right
                add_cell_in_grid(self.grid, max_line_idx, 'left_b', max(totalb_left, totalb_right), "{[u]}{[b]}%s{[/b]}{[/u]}")
                add_cell_in_grid(self.grid, max_line_idx, 'right_b', max(totalb_left, totalb_right), "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, max_line_idx + 1, 'left', '')
            add_cell_in_grid(self.grid, max_line_idx + 1, 'right', '')
        else:
            max_line_idx = self.line_offset - 1
        return max_line_idx + 1 - self.line_offset

    def calcul_table(self):
        filter_exclude = Q(entry__in=[entry for entry in EntryAccount.objects.filter(journal_id=5, entrylineaccount__account__code__in=current_system_account().result_accounting_codes)])
        self.budgetfilter_right = Q(year=self.item) & Q(code__regex=current_system_account().get_revenue_mask())
        self.budgetfilter_left = Q(year=self.item) & Q(code__regex=current_system_account().get_expence_mask())

        if len(self.rubric_names) > 0:
            line_idx = self._add_left_right_accounting_with_rubric(Q(account__type_of_account=4) & ~filter_exclude, Q(account__type_of_account=3) & ~filter_exclude, True, self.rubric_names)
        else:
            line_idx = self._add_left_right_accounting(Q(account__type_of_account=4) & ~filter_exclude, Q(account__type_of_account=3) & ~filter_exclude, True)
        self.show_annexe(line_idx, Q(year=self.item), filter_exclude)


@MenuManage.describ('accounting.change_fiscalyear', FORMTYPE_NOMODAL, 'bookkeeping_report', _('Show ledger for current fiscal year'))
class FiscalYearLedger(FiscalYearReport):
    caption = _("Ledger")
    add_filtering = True
    force_date_filter = True

    def __init__(self, **kwargs):
        FiscalYearReport.__init__(self, **kwargs)
        self.last_account = None
        self.last_third_id = None
        self.last_total = [0.0, 0.0]
        self.line_idx = 1

    def _add_full_description(self):
        self.full_description = self.getparam('full_description', False)
        edt = XferCompCheck('full_description')
        edt.set_value(self.full_description)
        edt.set_location(1, self.get_max_row() + 1)
        edt.description = _("full description")
        edt.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)

    def fill_filterCode(self):
        row = self.get_max_row() + 1
        self.only_nonull = self.getparam('only_nolink', False)
        edt = XferCompCheck('only_nolink')
        edt.set_value(self.only_nonull)
        edt.set_location(1, row)
        edt.description = _("only entry without link")
        edt.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)
        if self.only_nonull:
            self.filter &= (Q(link__isnull=True) | Q(link__date_max__gt=self.item.end)) & Q(third__isnull=False)
            if self.getparam('filtercode', '') == '':
                third_mask = current_system_account().get_third_mask()
                while re.match("[0-9a-zA-Z]", third_mask[0]) is None:
                    third_mask = third_mask[1:]
                num_letter = 0
                while re.match("[0-9a-zA-Z]", third_mask[num_letter]) is not None:
                    num_letter += 1
                third_mask = third_mask[:num_letter]
                self.params['filtercode'] = third_mask
        FiscalYearReport.fill_filterCode(self)
        self._add_full_description()

    def define_gridheader(self):
        grid_name = 'report_%d' % self.item.id
        self.grid = XferCompGrid(grid_name)
        self.grid.add_header('entry.num', _('numeros'))
        self.grid.add_header('entry.date_entry', _('date entry'))
        self.grid.add_header('entry.date_value', _('date value'))
        self.grid.add_header('designation_ref_with_third', _('name'))
        self.grid.add_header('link_costaccounting', _('link/cost accounting'))
        self.grid.add_header('debit', _('debit'), self.hfield, formatstr=';'.join([self.format_str, self.format_str, '']))
        self.grid.add_header('credit', _('credit'), self.hfield, formatstr=';'.join([self.format_str, self.format_str, '']))
        self.grid.add_action(self.request, FiscalYearLedgerShow.get_action(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE, params={'gridname': grid_name})

    def _add_total_account(self, third=False):
        current_total = self.last_third_total if third else self.last_total
        if (self.last_account is not None and not third) or (self.last_third_id is not None and third):
            add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'designation_ref_with_third', get_spaces(40 if third else 30) + "{[i]}%s{[/i]}" % (_('sub-total') if third else _('total')))
            if self.last_account.credit_debit_way() == -1:
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'debit', current_total[0], "{[i]}%s{[/i]}")
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'credit', current_total[1], "{[i]}%s{[/i]}")
            else:
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'debit', current_total[1], "{[i]}%s{[/i]}")
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'credit', current_total[0], "{[i]}%s{[/i]}")
            self.line_idx += 1
            last_total = current_total[0] - current_total[1]
            add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'designation_ref_with_third', get_spaces(40 if third else 30) + "{[u]}{[i]}%s{[/i]}{[/u]}" % (_('sub-balance') if third else _('balance')))
            add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'debit', max((0, -1 * self.last_account.credit_debit_way() * last_total)), "{[u]}{[i]}%s{[/i]}{[/u]}")
            add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'credit', max((0, self.last_account.credit_debit_way() * last_total)), "{[u]}{[i]}%s{[/i]}{[/u]}")
            self.line_idx += 1
            add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'designation_ref_with_third', '{[br/]}')
            if not third:
                self.line_idx += 1
                self.last_total = [0.0, 0.0]
            self.last_third_total = [0.0, 0.0]

    def calcul_table(self):
        self.line_idx = 1
        self.last_account = None
        self.last_third_id = None
        self.last_total = [0.0, 0.0]
        self.last_third_total = [0.0, 0.0]
        for line in EntryLineAccount.objects.filter(self.filter).select_related('account', 'entry').distinct().order_by('account__code', 'third', 'entry__date_value'):
            line.full_eval = self.full_description
            if self.last_account != line.account:
                self._add_total_account(True)
                self._add_total_account(False)
                self.last_account = line.account
                self.last_third_id = None
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'designation_ref_with_third', get_spaces(15) + "{[u]}{[b]}%s{[/b]}{[/u]}" % str(self.last_account))
                self.line_idx += 1
                self.last_third_id = None
            if self.last_third_id != line.third_id:
                self._add_total_account(True)
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, 'designation_ref_with_third', get_spaces(8) + "{[b]}%s{[/b]}" % str(line.entry_account))
                self.line_idx += 1
                self.last_third_id = line.third_id
            for header in self.grid.headers:
                value = getattr(line, header.name, None)
                if value is None:
                    value = line.evaluate('#' + header.name)
                add_cell_in_grid(self.grid, self.line_offset + self.line_idx, header.name, value, line_ident=line.entry.id)
            if line.amount > 0:
                self.last_total[0] += line.amount
                self.last_third_total[0] += line.amount
            else:
                self.last_total[1] -= line.amount
                self.last_third_total[1] -= line.amount
            self.line_idx += 1
        self._add_total_account(True)
        self._add_total_account(False)


@MenuManage.describ('accounting.change_fiscalyear')
class FiscalYearLedgerShow(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-finance'
    caption = _("Ledger")
    methods_allowed = ('GET', )

    def fillresponse(self, gridname):
        try:
            ledger_id = self.getparam(gridname, '')
            _rowid, entryid = ledger_id.split('-')
            entryid = int(entryid)
            if entryid != 0:
                self.redirect_action(ActionsManage.get_action_url(EntryAccount.get_long_name(), 'OpenFromLine', self), params={'entryaccount': entryid})
        except Exception:
            getLogger("diacamma.accounting").exception('Ledget show')


@MenuManage.describ('accounting.change_fiscalyear', FORMTYPE_NOMODAL, 'bookkeeping_report', _('Show trial balance for current fiscal year'))
class FiscalYearTrialBalance(FiscalYearReport):
    caption = _("Trial balance")
    add_filtering = True
    force_date_filter = True

    def fill_filterCode(self):
        FiscalYearReport.fill_filterCode(self)
        row = self.get_max_row() + 1

        self.only_nonull = self.getparam('only_nonull', False)
        edt = XferCompCheck('only_nonull')
        edt.set_value(self.only_nonull)
        edt.set_location(1, row)
        edt.description = _("only no null")
        edt.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)

        self.with_third = self.getparam('with_third', False)
        edt = XferCompCheck('with_third')
        edt.set_value(self.with_third)
        edt.set_location(2, row, 2)
        edt.description = _("detail by third")
        edt.set_action(self.request, self.__class__.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)

    def define_gridheader(self):
        self.grid = XferCompGrid('report_%d' % self.item.id)
        self.grid.add_header('designation', _('name'))
        self.grid.add_header('total_debit', _('debit sum'), self.hfield, 0, self.format_str)
        self.grid.add_header('total_credit', _('credit sum'), self.hfield, 0, self.format_str)
        self.grid.add_header('solde_debit', _('debit'), self.hfield, 0, self.format_str)
        self.grid.add_header('solde_credit', _('credit'), self.hfield, 0, self.format_str)

    def _get_balance_values(self):
        balance_values = {}
        if self.with_third:
            fields = ['account', 'third']
        else:
            fields = ['account']
        data_line_positifs = list(EntryLineAccount.objects.filter(self.filter & Q(amount__gt=0)).order_by(*fields).values(*fields).annotate(data_sum=Sum('amount')))
        data_line_negatifs = list(EntryLineAccount.objects.filter(self.filter & Q(amount__lt=0)).order_by(*fields).values(*fields).annotate(data_sum=Sum('amount')))
        for data_line in data_line_positifs + data_line_negatifs:
            if abs(data_line['data_sum']) > 0.0001:
                account = ChartsAccount.objects.get(id=data_line['account'])
                account_code = correct_accounting_code(account.code)
                if ('third' in data_line.keys()) and (data_line['third'] is not None):
                    account_code = "%s#%s" % (account_code, data_line['third'])
                if account_code not in balance_values.keys():
                    if ('third' in data_line.keys()) and (data_line['third'] is not None):
                        third = Third.objects.get(id=data_line['third'])
                        account_title = "[%s %s]" % (account.code, str(third))
                    else:
                        account_title = account.get_name()
                    balance_values[account_code] = [account_title, 0, 0]
                if (account.credit_debit_way() * data_line['data_sum']) > 0.0001:
                    balance_values[account_code][2] += account.credit_debit_way() * data_line['data_sum']
                else:
                    balance_values[account_code][1] += -1 * account.credit_debit_way() * data_line['data_sum']
        return balance_values

    def calcul_table(self):
        balance_total = [_('total'), 0, 0, 0, 0]
        line_idx = 1
        balance_values = self._get_balance_values()
        keys = sorted(balance_values.keys())
        for key in keys:
            diff = balance_values[key][1] - balance_values[key][2]
            if (self.only_nonull is False) or (abs(diff) > 0.0001):
                balance_total[1] += balance_values[key][1]
                balance_total[2] += balance_values[key][2]
                balance_total[3] += max(0, diff)
                balance_total[4] += max(0, -1 * diff)
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'designation', balance_values[key][0])
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'total_debit', balance_values[key][1])
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'total_credit', balance_values[key][2])
                add_cell_in_grid(self.grid, self.line_offset + line_idx, 'solde_debit', max(0, diff))
                if abs(diff) < 0.0001:
                    add_cell_in_grid(self.grid, self.line_offset + line_idx, 'solde_credit', 0)
                else:
                    add_cell_in_grid(self.grid, self.line_offset + line_idx, 'solde_credit', max(0, -1 * diff))
                line_idx += 1
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'designation', "")
        line_idx += 1
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'designation', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % balance_total[0])
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'total_debit', balance_total[1], "{[u]}{[b]}%s{[/b]}{[/u]}")
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'total_credit', balance_total[2], "{[u]}{[b]}%s{[/b]}{[/u]}")
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'solde_debit', balance_total[3], "{[u]}{[b]}%s{[/b]}{[/u]}")
        add_cell_in_grid(self.grid, self.line_offset + line_idx, 'solde_credit', balance_total[4], "{[u]}{[b]}%s{[/b]}{[/u]}")


@MenuManage.describ('accounting.change_fiscalyear')
class FiscalYearReportPrint(XferPrintAction):
    caption = _("Print report fiscal year")
    short_icon = 'mdi:mdi-finance'
    model = FiscalYear
    field_id = 'year'
    with_text_export = True
    tab_change_page = True

    def __init__(self):
        XferPrintAction.__init__(self)
        self.action_class = self.__class__.action_class
        if self.action_class is None:
            self.caption = self.__class__.caption
        else:
            self.caption = self.action_class.caption

    def _get_persistent_pdfreport(self, recreate):
        self.action_class = getattr(sys.modules[self.getparam("modulename", __name__)], self.getparam("classname", ''))
        if getattr(self.action_class, 'saving_pdfreport', False) is True:
            if self.action_class is None:
                self.caption = self.__class__.caption
            else:
                self.caption = self.action_class.caption
            doc = self.item.get_reports(self.action_class, recreate=recreate)
            if doc is not None:
                return doc.content.read()
        return None

    def get_persistent_renew(self):
        return self.item.status != FiscalYear.STATUS_FINISHED

    def get_report_generator(self):
        self.action_class = getattr(sys.modules[self.getparam("modulename", __name__)], self.getparam("classname", ''))
        if self.action_class is None:
            self.caption = self.__class__.caption
        else:
            self.caption = self.action_class.caption
        gen = XferPrintAction.get_report_generator(self)
        own_struct = LegalEntity.objects.get(id=1)
        if self.item.status != 2:
            date_txt = formats.date_format(date.today(), "DATE_FORMAT")
        else:
            date_txt = ''
        gen.title = "{[u]}{[b]}%s{[/b]}{[/u]}{[br/]}{[i]}%s{[/i]}{[br/]}{[b]}%s{[/b]}" % (own_struct, self.action_class.caption, date_txt)
        gen.page_width = 297
        gen.page_height = 210
        return gen


@MenuManage.describ('accounting.change_fiscalyear')
class CostAccountingReportPrint(XferPrintAction):
    caption = _("Print report cost accounting")
    short_icon = 'mdi:mdi-finance'
    model = CostAccounting
    field_id = 'costaccounting'
    with_text_export = True
    tab_change_page = True

    def __init__(self):
        XferPrintAction.__init__(self)
        self.action_class = self.__class__.action_class
        self.caption = self.__class__.caption

    def get_report_generator(self):
        self.action_class = getattr(sys.modules[self.getparam("modulename", __name__)], self.getparam("classname", ''))
        gen = XferPrintAction.get_report_generator(self)
        own_struct = LegalEntity.objects.get(id=1)
        gen.title = "{[u]}{[b]}%s{[/b]}{[/u]}{[br/]}{[i]}%s{[/i]}{[br/]}{[b]}%s{[/b]}" % (
            own_struct, self.action_class.caption, formats.date_format(date.today(), "DATE_FORMAT"))
        gen.page_width = 297
        gen.page_height = 210
        return gen


class CostAccountingReport(FiscalYearReport):
    short_icon = 'mdi:mdi-finance'
    model = CostAccounting
    field_id = 'costaccounting'

    def fillresponse(self):
        self.fill_header()
        self.addNameCol = False
        for self.item in self.items:
            self.new_tab(str(self.item))
            self.filter = Q(costaccounting=self.item)
            if self.date_begin != NULL_VALUE:
                self.filter &= Q(entry__date_value__gte=self.date_begin)
            if self.date_end != NULL_VALUE:
                self.filter &= Q(entry__date_value__lte=self.date_end)
            if self.add_filtering and self.filtercode != '':
                self.filter &= Q(account__code__startswith=self.filtercode)
            self.define_gridheader()
            self.fill_filterheader()
            self.calcul_table()
            self.fill_body()
        self.fill_buttons()

    def define_gridheader(self):
        self.grid = XferCompGrid('report_%d' % self.item.id)
        if self.addNameCol:
            self.grid.add_header('name', _('Cost accounting'))
        self.grid.add_header('left', _('Expenses'))
        self.grid.add_header('left_n', _('Value'), self.hfield, 0, self.format_str)
        self.grid.add_header('left_b', _('Budget'), self.hfield, 0, self.format_str)
        if self.lastfilter is not None:
            self.grid.add_header('left_n_1', _('Last'), self.hfield, 0, self.format_str)
        self.grid.add_header('space', '')
        self.grid.add_header('right', _('Revenues'))
        self.grid.add_header('right_n', _('Value'), self.hfield, 0, self.format_str)
        self.grid.add_header('right_b', _('Budget'), self.hfield, 0, self.format_str)
        if self.lastfilter is not None:
            self.grid.add_header('right_n_1', _('Last'), self.hfield, 0, self.format_str)

    def fill_filterheader(self):
        pass

    def fill_header(self):
        datereadonly = self.getparam("datereadonly", False)
        self.date_begin = self.getparam("begin_date", NULL_VALUE)
        self.date_end = self.getparam("end_date", NULL_VALUE)
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 3)
        self.add_component(img)
        if len(self.items) == 1:
            lbl = XferCompLabelForm('name')
            lbl.set_value(str(self.items[0]))
            lbl.set_location(1, 2, 4)
            lbl.description = self.model._meta.verbose_name
            self.add_component(lbl)

        if datereadonly:
            begin_filter = XferCompLabelForm('begin_date')
            begin_filter.set_value(datetime.strptime(self.date_begin, "%Y-%m-%d").date())
            begin_filter.set_format("D")
            begin_filter.set_needed(True)
            end_filter = XferCompLabelForm('end_date')
            end_filter.set_value(datetime.strptime(self.date_end, "%Y-%m-%d").date())
            end_filter.set_needed(True)
            end_filter.set_format("D")
        else:
            begin_filter = XferCompDate('begin_date')
            begin_filter.set_value(self.date_begin)
            begin_filter.set_needed(False)
            begin_filter.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            end_filter = XferCompDate('end_date')
            end_filter.set_value(self.date_end)
            end_filter.set_needed(False)
            end_filter.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        begin_filter.set_location(1, 4)
        end_filter.set_location(2, 4)
        begin_filter.description = _('begin')
        end_filter.description = _('end')
        self.add_component(begin_filter)
        self.add_component(end_filter)
        self.filter = Q(costaccounting=self.item)
        if self.date_begin != NULL_VALUE:
            self.filter &= Q(entry__date_value__gte=self.date_begin)
        if self.date_end != NULL_VALUE:
            self.filter &= Q(entry__date_value__lte=self.date_end)
        self.fill_filterCode()

    def fill_buttons(self):
        self.add_action(CostAccountingReportPrint.get_action(TITLE_PRINT, short_icon='mdi:mdi-printer-outline'),
                        close=CLOSE_NO, params={'classname': self.__class__.__name__})
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@ActionsManage.affect_grid(_("Report"), short_icon='mdi:mdi-printer-pos-outline', unique=SELECT_MULTI, modal=FORMTYPE_NOMODAL)
@MenuManage.describ('accounting.change_entryaccount')
class CostAccountingIncomeStatement(CostAccountingReport, FiscalYearIncomeStatement):
    caption = _("Income statement of cost accounting")

    def fill_header(self):
        CostAccountingReport.fill_header(self)

    def fillresponse(self):
        self.fill_header()
        all_have_last = False
        tot_n, tot_b, tot_n1 = (0, 0, 0)
        res1, res2, resb = (0, 0, 0)
        self.addNameCol = True
        self.lastfilter = True
        self.item = self.items[len(self.items) - 1]
        self.define_gridheader()
        for self.item in self.items:
            self.total_summary_left = (0, 0, 0)
            self.total_summary_right = (0, 0, 0)
            add_cell_in_grid(self.grid, self.line_offset, 'name', '{[b]}{[u]}%s{[/u]}{[/b]}' % self.item)
            self.line_offset += 1
            self.filter = Q(costaccounting=self.item)
            if self.date_begin != NULL_VALUE:
                self.filter &= Q(entry__date_value__gte=self.date_begin)
            if self.date_end != NULL_VALUE:
                self.filter &= Q(entry__date_value__lte=self.date_end)
            if self.add_filtering and self.filtercode != '':
                self.filter &= Q(account__code__startswith=self.filtercode)
            self.fill_filterheader()
            all_have_last = all_have_last or (self.lastfilter is not None)
            self.calcul_table()
            total1_left, total2_left, totalb_left = self.total_summary_left
            if total1_left:
                tot_n += total1_left
            if totalb_left:
                tot_b += totalb_left
            if total2_left:
                tot_n1 += total2_left
            subres1, subres2, subresb = self.result
            res1 -= subres1
            res2 -= subres2
            resb -= subresb
            self.fill_body()
            last_record_id = sorted(self.grid.records.keys())[-1].split('-')[0]
            while not last_record_id.isnumeric() and len(last_record_id) > 0:
                last_record_id = last_record_id[1:]
            self.line_offset = int('0' + last_record_id) + 1
        if not all_have_last:
            self.grid.delete_header('left_n_1')
            self.grid.delete_header('right_n_1')
        if len(self.items) > 1:
            add_cell_in_grid(self.grid, self.line_offset + 1, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % _('general result (profit)'))
            add_cell_in_grid(self.grid, self.line_offset + 1, 'right', get_spaces(5) + "{[i]}%s{[/i]}" % _('general result (deficit)'))
            if res1 < 0:
                add_cell_in_grid(self.grid, self.line_offset + 1, 'left_n', -1 * res1)
                tot_n -= res1
            else:
                add_cell_in_grid(self.grid, self.line_offset + 1, 'right_n', res1)
            if res2 < 0:
                add_cell_in_grid(self.grid, self.line_offset + 1, 'left_n_1', -1 * res2)
                tot_n1 -= res2
            else:
                add_cell_in_grid(self.grid, self.line_offset + 1, 'right_n_1', res2)
            if resb < 0:
                add_cell_in_grid(self.grid, self.line_offset + 1, 'left_b', -1 * resb)
                tot_b -= resb
            else:
                add_cell_in_grid(self.grid, self.line_offset + 1, 'right_b', resb)
            add_cell_in_grid(self.grid, self.line_offset + 2, 'left', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % _('general total'))
            add_cell_in_grid(self.grid, self.line_offset + 2, 'left_n', tot_n, "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, self.line_offset + 2, 'left_b', tot_b, "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, self.line_offset + 2, 'left_n_1', tot_n1, "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, self.line_offset + 2, 'right', get_spaces(10) + "{[u]}{[b]}%s{[/b]}{[/u]}" % _('general total'))
            add_cell_in_grid(self.grid, self.line_offset + 2, 'right_n', tot_n, "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, self.line_offset + 2, 'right_b', tot_b, "{[u]}{[b]}%s{[/b]}{[/u]}")
            add_cell_in_grid(self.grid, self.line_offset + 2, 'right_n_1', tot_n1, "{[u]}{[b]}%s{[/b]}{[/u]}")
        else:
            self.grid.delete_header('name')
        self.fill_buttons()

    def get_rubric_list(self):
        return ChartsAccount.get_rubriclist_from_entryline(self.filter)

    def fill_filterheader(self):
        self.select_rubric()
        if self.item.last_costaccounting is not None:
            self.lastfilter = Q(costaccounting=self.item.last_costaccounting)
        else:
            self.lastfilter = None

    def calcul_table(self):
        if (self.date_begin != NULL_VALUE) or (self.date_end != NULL_VALUE):
            self.budgetfilter_right = None
            self.budgetfilter_left = None
            self.lastfilter = None
            self.grid.delete_header('left_b')
            self.grid.delete_header('left_n_1')
            self.grid.delete_header('right_b')
            self.grid.delete_header('right_n_1')
        else:
            self.budgetfilter_right = Q(cost_accounting=self.item) & Q(code__regex=current_system_account().get_revenue_mask())
            self.budgetfilter_left = Q(cost_accounting=self.item) & Q(code__regex=current_system_account().get_expence_mask())

        filter_exclude = Q(entry__in=[entry for entry in EntryAccount.objects.filter(journal_id=5, entrylineaccount__account__code__in=current_system_account().result_accounting_codes)])
        if len(self.rubric_names) > 0:
            line_idx = self._add_left_right_accounting_with_rubric(Q(account__type_of_account=4) & ~filter_exclude, Q(account__type_of_account=3) & ~filter_exclude, True, self.rubric_names)
        else:
            line_idx = self._add_left_right_accounting(Q(account__type_of_account=4) & ~filter_exclude, Q(account__type_of_account=3) & ~filter_exclude, True)
        self.show_annexe(line_idx, Q(cost_accounting=self.item), filter_exclude)


@ActionsManage.affect_grid(_("Ledger"), short_icon='mdi:mdi-printer-pos-outline', unique=SELECT_MULTI, modal=FORMTYPE_NOMODAL)
@MenuManage.describ('accounting.change_entryaccount')
class CostAccountingLedger(CostAccountingReport, FiscalYearLedger):
    caption = _("Ledger of cost accounting")
    add_filtering = True

    def fill_header(self):
        CostAccountingReport.fill_header(self)

    def define_gridheader(self):
        FiscalYearLedger.define_gridheader(self)

    def calcul_table(self):
        FiscalYearLedger.calcul_table(self)

    def fill_filterCode(self):
        FiscalYearReport.fill_filterCode(self)
        self._add_full_description()


@ActionsManage.affect_grid(_("Trial balance"), short_icon='mdi:mdi-printer-pos-outline', unique=SELECT_MULTI, modal=FORMTYPE_NOMODAL)
@MenuManage.describ('accounting.change_entryaccount')
class CostAccountingTrialBalance(CostAccountingReport, FiscalYearTrialBalance):
    caption = _("Trial balance of cost accounting")
    add_filtering = True

    def fill_header(self):
        CostAccountingReport.fill_header(self)

    def define_gridheader(self):
        FiscalYearTrialBalance.define_gridheader(self)

    def calcul_table(self):
        FiscalYearTrialBalance.calcul_table(self)

    def fill_filterCode(self):
        FiscalYearReport.fill_filterCode(self)
        self.with_third = False
        self.only_nonull = False
