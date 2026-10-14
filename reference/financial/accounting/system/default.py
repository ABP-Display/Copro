# -*- coding: utf-8 -*-
'''
lucterios.contacts package

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
from functools import reduce
from logging import getLogger
import re

from django.utils.translation import gettext_lazy as _
from django.db.models.aggregates import Sum
from django.db.models import Q

from lucterios.framework.xferadvance import TITLE_OK, TITLE_CANCEL
from lucterios.framework.error import LucteriosException

from diacamma.accounting.tools import get_amount_from_format_devise, correct_accounting_code


class DefaultSystemAccounting(object):

    CLOSE_TITLE_RESULT = _("Fiscal year closing - Result")
    CLOSE_TITLE_THIRD = _("Fiscal year closing - Third")

    NEGATIF_ACCOUNT = ""
    POSITIF_ACCOUNT = ""

    GENERAL_CHARTS_ACCOUNT = []

    GENERAL_MASK = r'X'

    CASH_MASK = r'X'

    CASH_MASK_BEGIN = ''

    PROVIDER_MASK = r'X'

    CUSTOMER_MASK = r'X'

    EMPLOYED_MASK = r'X'

    SOCIETARY_MASK = r'X'

    REVENUE_MASK = r'X'

    EXPENSE_MASK = r'X'

    # THIRD_MASK = "%s|%s|%s|%s" % (PROVIDER_MASK, CUSTOMER_MASK, EMPLOYED_MASK, SOCIETARY_MASK)
    THIRD_MASK = r'X'

    ANNEXE_MASK = r'X'

    VAT_DEDUCTIVE_MASK = r'-'
    VAT_COLLECTED_MASK = r'-'
    VAT_INTRACOMMUNITY_MASK = r''
    EINVOICE = ''

    @classmethod
    def find_charts(cls, code):
        current_charts = None
        for chart_item in cls.GENERAL_CHARTS_ACCOUNT:
            if chart_item[1] is None:
                if code[:len(chart_item[0])] == chart_item[0]:
                    current_charts = chart_item
                elif current_charts is not None:
                    break
            else:
                if (chart_item[0] <= code) and (code <= chart_item[1]):
                    current_charts = chart_item
                    break
        return current_charts

    @property
    def result_accounting_codes(self):
        from diacamma.accounting.models import ChartsAccount
        return tuple({correct_accounting_code(chart_account.code) for chart_account in ChartsAccount.objects.filter(Q(code__startswith=self.NEGATIF_ACCOUNT) | Q(code__startswith=self.POSITIF_ACCOUNT))})

    def has_minium_code_size(self):
        return True

    def get_general_mask(self):
        return self.GENERAL_MASK

    def get_cash_mask(self):
        return self.CASH_MASK

    def get_cash_begin(self):
        return self.CASH_MASK_BEGIN

    def get_provider_mask(self):
        return self.PROVIDER_MASK

    def get_customer_mask(self):
        return self.CUSTOMER_MASK

    def get_employed_mask(self):
        return self.EMPLOYED_MASK

    def get_societary_mask(self):
        return self.SOCIETARY_MASK

    def get_third_mask(self):
        return self.THIRD_MASK

    def get_revenue_mask(self):
        return self.REVENUE_MASK

    def get_expence_mask(self):
        return self.EXPENSE_MASK

    def get_annexe_mask(self):
        return self.ANNEXE_MASK

    def get_vat_deductible_mask(self):
        return self.VAT_DEDUCTIVE_MASK

    def get_vat_collected_mask(self):
        return self.VAT_COLLECTED_MASK

    def get_vat_intracommunity_mask(self):
        return self.VAT_INTRACOMMUNITY_MASK

    def get_einvoice_format(self):
        return self.EINVOICE

    def new_charts_account(self, code):
        code = code.strip()
        if code == '':
            return '', -1
        pattern = re.compile(self.GENERAL_MASK)
        if pattern.match(code):
            current_charts = self.find_charts(code)
            if current_charts is not None:
                return current_charts[-2], current_charts[-1]
        return '', -2

    def _create_custom_for_profit(self, year, custom, val_profit):
        from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompSelect
        if val_profit > 0.0001:
            type_profit = _('profit')
        else:
            type_profit = _('deficit')
        img = XferCompImage("img")
        img.set_location(0, 0)
        img.set_value('mdi:mdi-bank-transfer', '#')
        custom.add_component(img)
        lbl = XferCompLabelForm("title")
        lbl.set_value_as_headername(_("Profit and deficit"))
        lbl.set_location(1, 0)
        custom.add_component(lbl)
        text = _("{[i]}You have a %(type)s of %(value)s.{[br/]}You must to define the account to affect.{[br/]}{[/i]}") % {'type': type_profit, 'value': get_amount_from_format_devise(abs(val_profit), 7)}
        text += _("{[br/]}After validation, you begin '%s'.{[br/]}{[br/]}{[i]}{[u]}Warning:{[/u]} Your retained earnings must be completed.{[/i]}") % str(year)
        lbl = XferCompLabelForm("info")
        lbl.set_value(text)
        lbl.set_location(0, 1, 2)
        custom.add_component(lbl)
        sel_cmpt = []
        query = Q(code__startswith=self.NEGATIF_ACCOUNT) | Q(code__startswith=self.POSITIF_ACCOUNT)
        for account in year.chartsaccount_set.filter(type_of_account=2).exclude(query).order_by('code'):
            sel_cmpt.append((account.id, str(account)))
        sel = XferCompSelect("profit_account")
        sel.set_select(sel_cmpt)
        sel.set_location(1, 2)
        custom.add_component(sel)
        return custom

    def _get_profit(self, year):
        from diacamma.accounting.models import EntryLineAccount, get_amount_sum
        query = Q(account__code__startswith=self.NEGATIF_ACCOUNT) | Q(account__code__startswith=self.POSITIF_ACCOUNT)
        query &= Q(account__year=year)
        val_profit = get_amount_sum(EntryLineAccount.objects.filter(query).aggregate(Sum('amount')))
        return val_profit

    def _create_profit_entry(self, year, profit_account):
        from diacamma.accounting.models import Journal, EntryAccount, EntryLineAccount, ChartsAccount
        paym_journ = Journal.objects.get(id=5)
        paym_desig = _('Affect of profit/deficit')
        new_entry = EntryAccount.objects.create(year=year, journal=paym_journ, designation=paym_desig, date_value=year.begin)
        query = Q(account__code__startswith=self.NEGATIF_ACCOUNT) | Q(account__code__startswith=self.POSITIF_ACCOUNT)
        query &= Q(account__year=year)
        sum_profit = 0
        for new_line in EntryLineAccount.objects.filter(query).distinct():
            sum_profit += new_line.amount
            new_line.id = None
            new_line.entry = new_entry
            new_line.amount = -1 * new_line.amount
            new_line.save()
        new_line = EntryLineAccount()
        new_line.entry = new_entry
        new_line.amount = sum_profit
        new_line.account = ChartsAccount.objects.get(id=profit_account)
        new_line.save()
        new_entry.closed()
        return True

    def check_begin(self, year, xfer):
        profit_account = xfer.getparam('profit_account', 0)
        if profit_account > 0:
            return self._create_profit_entry(year, profit_account)
        val_profit = 0
        if xfer.getparam('with_profit', True):
            val_profit = self._get_profit(year)
        if abs(val_profit) > 0.0001:
            from lucterios.framework.tools import WrapAction, CLOSE_YES, FORMTYPE_MODAL
            custom = xfer.create_custom()
            self._create_custom_for_profit(year, custom, val_profit)
            custom.add_action(xfer.return_action(TITLE_OK, short_icon='mdi:mdi-check'), modal=FORMTYPE_MODAL, close=CLOSE_YES)
            custom.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
            return False
        else:
            text = _("Do you want to begin '%s'? {[br/]}{[br/]}{[i]}{[u]}Warning:{[/u]} Your retained earnings must be completed.{[/i]}") % str(year)
            return xfer.confirme(text)

    def _add_total_income_entrylines(self, year, new_entry):
        for chart_account in year.chartsaccount_set.filter(type_of_account__in=(3, 4, 5)).order_by('code'):
            if abs(chart_account.current_validated) > 1e-4:
                new_entry.add_entry_line(-1 * chart_account.get_current_validated(False), chart_account.code)

    def _create_result_entry(self, year):
        revenue = year.total_revenue
        expense = year.total_expense
        if abs(expense - revenue) > 0.0001:
            from diacamma.accounting.models import EntryAccount
            new_entry = EntryAccount.objects.create(year=year, journal_id=5, designation=self.CLOSE_TITLE_RESULT, date_value=year.end)
            self._add_total_income_entrylines(year, new_entry)
            if expense > revenue:
                chart_negatif = year.chartsaccount_set.filter(code__startswith=self.NEGATIF_ACCOUNT).first()
                new_entry.add_entry_line(revenue - expense, chart_negatif.code if chart_negatif is not None else self.NEGATIF_ACCOUNT)
            elif abs(expense - revenue) > 1e-4:
                chart_positive = year.chartsaccount_set.filter(code__startswith=self.POSITIF_ACCOUNT).first()
                new_entry.add_entry_line(revenue - expense, chart_positive.code if chart_positive is not None else self.POSITIF_ACCOUNT)
            new_entry.closed(check_needcost=False)

    def _add_sumline_in_account(self, last_account_id, sum_account, new_entry):
        from diacamma.accounting.models import EntryLineAccount
        if abs(sum_account) > 0.0001:
            new_line = EntryLineAccount()
            new_line.entry = new_entry
            new_line.account_id = last_account_id
            new_line.amount = sum_account
            new_line.third = None
            new_line.save()
            return True
        return False

    def _create_thirds_ending_entry(self, year):
        from diacamma.accounting.models import ChartsAccount, AccountLink, EntryAccount, EntryLineAccount
        from lucterios.CORE.parameters import Params

        new_entry = EntryAccount.objects.create(year=year, journal_id=5, designation=self.CLOSE_TITLE_THIRD, date_value=year.end)
        nolettering_account = ChartsAccount.objects.filter(year=year, code__in=Params.getvalue("accounting-lettering-check")).order_by('code').distinct()
        for account_item in nolettering_account:
            amounts_by_third = EntryLineAccount.objects.filter(Q(account=account_item)).order_by('third').values('third').annotate(amount=Sum('amount'))
            sum_account = reduce(lambda item1, item2: item1 + item2, [float(item['amount']) for item in amounts_by_third], 0.0)
            self._add_sumline_in_account(account_item.id, sum_account, new_entry)
            for amount_and_third in amounts_by_third:
                new_line = EntryLineAccount()
                new_line.entry = new_entry
                new_line.amount = -1 * float(amount_and_third['amount'])
                new_line.account = account_item
                new_line.third_id = amount_and_third['third']
                new_line.save()

        last_account_id = None
        sum_account = 0.0
        for entry_line in EntryLineAccount.objects.filter(account__code__regex=self.get_third_mask(), account__year=year, link__isnull=True, third__isnull=False).exclude(account__in=nolettering_account).order_by('account'):
            if last_account_id != entry_line.account_id:
                if self._add_sumline_in_account(last_account_id, sum_account, new_entry):
                    sum_account = 0
            last_account_id = entry_line.account_id
            new_line = EntryLineAccount()
            new_line.entry = new_entry
            new_line.amount = -1 * entry_line.amount
            new_line.account_id = entry_line.account_id
            new_line.third_id = entry_line.third_id
            if (entry_line.reference is not None) and (entry_line.reference != ''):
                new_line.reference = entry_line.reference
            else:
                new_line.reference = entry_line.entry.designation
            new_line.save()
            AccountLink.create_link([new_line, entry_line])
            sum_account += float(entry_line.amount)
        if last_account_id == 0:
            new_entry.delete()
        else:
            self._add_sumline_in_account(last_account_id, sum_account, new_entry)
            new_entry.closed()

    def finalize_year(self, year):
        self._create_result_entry(year)
        self._create_thirds_ending_entry(year)
        return

    def _create_report_lastyearresult(self, year, import_result):
        from diacamma.accounting.models import EntryAccount
        end_desig = _("Retained earnings - Balance sheet")
        new_entry = EntryAccount.objects.create(year=year, journal_id=1, designation=end_desig, date_value=year.begin)
        for charts_account in year.last_fiscalyear.chartsaccount_set.filter(type_of_account__in=(0, 1, 2)):
            code = charts_account.code
            name = charts_account.name
            rubric = charts_account.rubric
            new_entry.add_entry_line(charts_account.get_current_validated(with_correction=True), code, name, with_correction=True, rubric=rubric)
        new_entry.closed()
        return ''

    def _create_report_third(self, year):
        from diacamma.accounting.models import Journal, EntryAccount, EntryLineAccount, AccountLink
        last_entry_account = year.last_fiscalyear.entryaccount_set.filter(journal__id=Journal.DEFAULT_OTHER).order_by('num').last()
        _no_change, debit_rest, credit_rest = last_entry_account.serial_control(last_entry_account.get_serial())
        bad_link_third = []
        multilinks_to_transfere = {}
        if (abs(debit_rest - credit_rest) < 0.0001) and (len(last_entry_account.get_thirds()) > 0):
            end_desig = _("Retained earnings - Third party debt")
            new_entry = EntryAccount.objects.create(year=year, journal_id=1, designation=end_desig, date_value=year.begin)
            for entry_line in last_entry_account.entrylineaccount_set.all():
                if re.match(self.get_general_mask(), entry_line.account.code):
                    new_entry_line = new_entry.add_entry_line(-1 * entry_line.amount, entry_line.account.code, entry_line.account.name, entry_line.third, entry_line.reference, rubric=entry_line.account.rubric)
                    lines_multilink = EntryLineAccount.objects.filter(entry__year=year.last_fiscalyear, link__entrylineaccount=entry_line, multilink__isnull=False)
                    if lines_multilink.count() > 0:
                        multilink = lines_multilink.first().multilink
                        if multilink not in multilinks_to_transfere:
                            multilinks_to_transfere[multilink] = []
                        multilinks_to_transfere[multilink].append(new_entry_line)
                        multilinks_to_transfere[multilink].extend(EntryLineAccount.objects.filter(entry__year=year, multilink=multilink).distinct())
            new_entry.closed()
            for multilink, entrylines_to_link in multilinks_to_transfere.items():
                if len(entrylines_to_link) > 1:
                    try:
                        AccountLink.create_link(entrylines_to_link)
                        multilink.delete()
                    except LucteriosException:
                        bad_link_third.append(str(entrylines_to_link[0].third))
                        getLogger("diacamma.accounting").warning("Bad balanced entry lines : %s" % entrylines_to_link)
                else:
                    bad_link_third.append(str(entrylines_to_link[0].third))
                    getLogger("diacamma.accounting").warning("Bad entry lines : %s" % entrylines_to_link)
        if len(bad_link_third) > 0:
            return _('Link problem for: {[br]} - %s{[br]}') % '{[br]} - '.join(bad_link_third)
        else:
            return ''

    def import_lastyear(self, year, import_result):
        warning_text = ''
        warning_text += self._create_report_lastyearresult(year, import_result)
        warning_text += self._create_report_third(year)
        return warning_text

    def fill_fiscalyear_balancesheet(self, grid, currentfilter, lastfilter):
        from diacamma.accounting.tools_reports import convert_query_to_account, add_cell_in_grid, add_item_in_grid, fill_grid, get_spaces
        cash_filter = Q(account__code__regex=self.get_cash_mask())
        third_filter = Q(account__code__regex=self.get_third_mask())

        left_line_idx = 0
        actif1 = Q(account__type_of_account=0) & ~cash_filter & ~third_filter
        data_line_left, total1_lefta, total2_lefta, _b_left, _account_codes = convert_query_to_account(currentfilter & actif1, lastfilter & actif1 if lastfilter is not None else None, None)
        if len(data_line_left) > 0:
            add_cell_in_grid(grid, left_line_idx, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % _('immobilizations & stock'))
            left_line_idx += 1
            left_line_idx = fill_grid(grid, left_line_idx, 'left', data_line_left)
            add_item_in_grid(grid, left_line_idx, 'left', (get_spaces(10) + "%s" % _('Sub-total'), total1_lefta, total2_lefta, None), "{[i]}%s{[/i]}")
            left_line_idx += 1
            add_cell_in_grid(grid, left_line_idx, 'left', '')
            left_line_idx += 1

        actif2 = third_filter
        data_line_left, total1_leftb, total2_leftb, _b_left, _account_codes = convert_query_to_account(currentfilter & actif2, lastfilter & actif2 if lastfilter is not None else None, None, sign_value=-1)
        if len(data_line_left) > 0:
            add_cell_in_grid(grid, left_line_idx, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % _('receivables'))
            left_line_idx += 1
            left_line_idx = fill_grid(grid, left_line_idx, 'left', data_line_left)
            add_item_in_grid(grid, left_line_idx, 'left', (get_spaces(10) + "%s" % _('Sub-total'), total1_leftb, total2_leftb, None), "{[i]}%s{[/i]}")
            left_line_idx += 1
            add_cell_in_grid(grid, left_line_idx, 'left', '')
            left_line_idx += 1

        actif3 = Q(account__type_of_account=0) & cash_filter
        data_line_left, total1_leftc, total2_leftc, _b_left, _account_codes = convert_query_to_account(currentfilter & actif3, lastfilter & actif3 if lastfilter is not None else None, None)
        if len(data_line_left) > 0:
            add_cell_in_grid(grid, left_line_idx, 'left', get_spaces(5) + "{[i]}%s{[/i]}" % _('values & availabilities'))
            left_line_idx += 1
            left_line_idx = fill_grid(grid, left_line_idx, 'left', data_line_left)
            add_item_in_grid(grid, left_line_idx, 'left', (get_spaces(10) + "%s" % _('Sub-total'), total1_leftc, total2_leftc, None), "{[i]}%s{[/i]}")
            left_line_idx += 1
            add_cell_in_grid(grid, left_line_idx, 'left', '')
            left_line_idx += 1

        right_line_idx = 0
        passif1 = Q(account__type_of_account=2)
        data_line_right, total1_righta, total2_righta, _b_right, _account_codes = convert_query_to_account(currentfilter & passif1, lastfilter & passif1 if lastfilter is not None else None, None)
        if len(data_line_right) > 0:
            add_cell_in_grid(grid, right_line_idx, 'right', get_spaces(5) + "{[i]}%s{[/i]}" % _('capital'))
            right_line_idx += 1
            right_line_idx = fill_grid(grid, right_line_idx, 'right', data_line_right)
            add_item_in_grid(grid, right_line_idx, 'right', (get_spaces(10) + "%s" % _('Sub-total'), total1_righta, total2_righta, None), "{[i]}%s{[/i]}")
            right_line_idx += 1
            add_cell_in_grid(grid, right_line_idx, 'right', '')
            right_line_idx += 1

        passif2 = third_filter
        data_line_right, total1_rightb, total2_rightb, _b_right, _account_codes = convert_query_to_account(currentfilter & passif2, lastfilter & passif2 if lastfilter is not None else None, None, sign_value=1)
        if len(data_line_right) > 0:
            add_cell_in_grid(grid, right_line_idx, 'right', get_spaces(5) + "{[i]}%s{[/i]}" % _('liabilities'))
            right_line_idx += 1
            right_line_idx = fill_grid(grid, right_line_idx, 'right', data_line_right)
            add_item_in_grid(grid, right_line_idx, 'right', (get_spaces(10) + "%s" % _('Sub-total'), total1_rightb, total2_rightb, None), "{[i]}%s{[/i]}")
            right_line_idx += 1
            add_cell_in_grid(grid, right_line_idx, 'right', '')
            right_line_idx += 1

        total1left = total1_lefta + total1_leftb + total1_leftc
        total1right = total1_righta + total1_rightb
        total2left = total2_lefta + total2_leftb + total2_leftc
        total2right = total2_righta + total2_rightb

        line_idx = max(right_line_idx, left_line_idx)
        add_item_in_grid(grid, line_idx + 1, 'left', (_('Total'), total1left, total2left, None), "{[u]}{[b]}%s{[/b]}{[/u]}")
        add_item_in_grid(grid, line_idx + 1, 'right', (_('Total'), total1right, total2right, None), "{[u]}{[b]}%s{[/b]}{[/u]}")

        show_left = False
        show_right = False
        if (total1left - total1right) < -1e-4:
            add_cell_in_grid(grid, line_idx, 'left_n', total1right - total1left, "{[i]}{[b]}%s{[/b]}{[/i]}")
            show_left = True
        elif abs(total1left - total1right) > 1e-4:
            add_cell_in_grid(grid, line_idx, 'right_n', total1left - total1right, "{[i]}{[b]}%s{[/b]}{[/i]}")
            show_right = True
        if (total2left - total2right) < -1e-4:
            add_cell_in_grid(grid, line_idx, 'left_n_1', total2right - total2left, "{[i]}{[b]}%s{[/b]}{[/i]}")
            show_left = True
        elif abs(total2left - total2right) > 1e-4:
            add_cell_in_grid(grid, line_idx, 'right_n_1', total2left - total2right, "{[i]}{[b]}%s{[/b]}{[/i]}")
            show_right = True
        if show_left:
            add_cell_in_grid(grid, line_idx, 'left', get_spaces(5) + "{[i]}{[b]}%s{[/b]}{[/i]}" % _('result (deficit)'))
        if show_right:
            add_cell_in_grid(grid, line_idx, 'right', get_spaces(5) + "{[i]}{[b]}%s{[/b]}{[/i]}" % _('result (profit)'))

    def get_export_xmlfiles(self):
        return None
