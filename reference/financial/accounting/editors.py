# -*- coding: utf-8 -*-

'''
Describe database model for Django

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
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
from re import match
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework.editors import LucteriosEditor
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompSelect, XferCompButton, XferCompGrid, XferCompEdit, XferCompFloat, \
    XferCompCheck
from lucterios.framework.tools import FORMTYPE_REFRESH, CLOSE_NO, ActionsManage, SELECT_SINGLE, SELECT_MULTI, CLOSE_YES, \
    FORMTYPE_MODAL
from lucterios.framework.xferadvance import TITLE_MODIFY
from lucterios.CORE.parameters import Params

from diacamma.accounting.models import current_system_account, FiscalYear, EntryLineAccount, EntryAccount, Third, CostAccounting, \
    ChartsAccount
from lucterios.framework import signal_and_lock
from lucterios.contacts.models import CustomField


class ThirdEditor(LucteriosEditor):

    def edit(self, xfer):
        xfer.filltab_from_model(1, 1, True, ['contact'])
        lbl_contact = xfer.get_components('contact')
        lbl_contact.colspan = 2
        CustomField.edit_fields(xfer, 1)

    def saving(self, xfer):
        LucteriosEditor.saving(self, xfer)
        self.item.set_custom_values(xfer.params)

    def show(self, xfer):
        xfer.tab = 0
        old_item = xfer.item
        xfer.item = self.item.contact.get_final_child()
        xfer.filltab_from_model(1, 1, True, ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email'])
        btn = XferCompButton('show')
        btn.set_location(3, 4, 3, 2)
        modal_name = xfer.item.__class__.get_long_name()
        field_id = xfer.item.__class__.__name__.lower()
        if field_id == 'legalentity':
            field_id = 'legal_entity'
        btn.set_action(xfer.request, ActionsManage.get_action_url(modal_name, 'Show', xfer), close=CLOSE_NO,
                       params={field_id: str(xfer.item.id)})
        xfer.add_component(btn)
        xfer.item = old_item
        Signal.call_signal("third_addon", self.item, xfer)


class AccountThirdEditor(LucteriosEditor):

    def edit(self, xfer):
        old_account = xfer.get_components("code")
        try:
            chart_accouts = FiscalYear.get_current().chartsaccount_set.all().filter(code__regex=current_system_account().get_third_mask())
            xfer.remove_component("code")
            sel_code = XferCompSelect("code")
            sel_code.set_location(old_account.col, old_account.row, old_account.colspan + 1, old_account.rowspan)
            existed_codes = []
            for acc_third in xfer.item.third.accountthird_set.all():
                existed_codes.append(acc_third.code)
            for item in chart_accouts.exclude(code__in=existed_codes).order_by('code'):
                sel_code.select_list.append((item.code, str(item)))
            sel_code.set_value(self.item.code)
            xfer.add_component(sel_code)
        except LucteriosException:
            old_account.mask = current_system_account().get_third_mask()
        return


class FiscalYearEditor(LucteriosEditor):

    def edit(self, xfer):
        fiscal_years = FiscalYear.objects.order_by('end')
        xfer.change_to_readonly('status')
        # modification case
        if self.item.id is not None:
            folder = xfer.get_components('folder')
            folder.set_needed(True)
            if (len(fiscal_years) != 0) and (fiscal_years[len(fiscal_years) - 1].id != self.item.id):
                raise LucteriosException(IMPORTANT, _('This fiscal year is not the last!'))
            # modifcation and not the first in building
            if (len(fiscal_years) != 1) or (self.item.status != 0):
                xfer.change_to_readonly('begin')
        else:  # creation
            prefix = xfer.get_components('prefix')
            prefix.set_value(xfer.item.get_letter())
            xfer.remove_component('folder')
            if len(fiscal_years) > 0:
                # not the first
                xfer.params['last_fiscalyear'] = fiscal_years[len(fiscal_years) - 1].id
                xfer.params['begin'] = self.item.begin.isoformat()
                xfer.change_to_readonly('begin')
        if self.item.status == FiscalYear.STATUS_FINISHED:
            xfer.change_to_readonly('end')
        if self.item.id is None:
            init_select = [(0, _('Blank')), (1, _("Initial"))]
            if len(fiscal_years) > 0:
                init_select.append((2, _("Import")))
            sel = XferCompSelect('init_account')
            sel.description = _("Charts of account")
            sel.set_select(init_select)
            sel.set_value(len(init_select) - 1)
            sel.set_location(1, xfer.get_max_row() + 1)
            xfer.add_component(sel)

    def before_save(self, xfer):
        if isinstance(self.item.end, str):
            self.item.end = datetime.strptime(self.item.end, "%Y-%m-%d").date()
        if isinstance(self.item.begin, str):
            self.item.begin = datetime.strptime(
                self.item.begin, "%Y-%m-%d").date()
        if self.item.end < self.item.begin:
            raise LucteriosException(IMPORTANT, _("end of fiscal year must be after begin!"))
        if self.item.id is None and (len(FiscalYear.objects.all()) == 0):
            self.item.is_actif = True
        return

    def run_begin(self, xfer):
        if self.item.status == FiscalYear.STATUS_BUILDING:
            EntryAccount.clear_ghost()
            nb_entry_noclose = EntryLineAccount.objects.filter(entry__journal__id=1, entry__close=False, account__year=self.item).count()
            if nb_entry_noclose > 0:
                raise LucteriosException(IMPORTANT, _("Some enties for last year report are not closed!"))
            signal_and_lock.Signal.call_signal("begin_year", xfer)
            if current_system_account().check_begin(self.item, xfer):
                self.item.status = FiscalYear.STATUS_RUNNING
                self.item.save()


class CostAccountingEditor(LucteriosEditor):

    def edit(self, xfer):
        if self.item.status == CostAccounting.STATUS_CLOSED:
            xfer.change_to_readonly('name')
            xfer.change_to_readonly('description')
            xfer.change_to_readonly('last_costaccounting')
            xfer.change_to_readonly('year')
        else:
            sel_year = xfer.get_components('year')
            sel_year.set_select_query(FiscalYear.objects.exclude(status=FiscalYear.STATUS_FINISHED))
            if self.item.id is not None:
                sel = xfer.get_components('last_costaccounting')
                sel.set_select_query(CostAccounting.objects.all().exclude(id=self.item.id))

    def before_save(self, xfer):
        if self.item.id is None and (len(CostAccounting.objects.all()) == 0):
            self.item.is_default = True
        return


class ChartsAccountEditor(LucteriosEditor):

    def before_save(self, xfer):
        if xfer.item.id is not None:
            old_item = ChartsAccount.objects.get(id=xfer.item.id)
            xfer.item.type_of_account = old_item.type_of_account
            if xfer.item.has_validated:
                xfer.item.code = old_item.code
        return

    def edit(self, xfer):
        xfer.change_to_readonly('type_of_account')
        if xfer.item.has_validated:
            xfer.change_to_readonly('code')
            code_ed = xfer.get_components('code')
        else:
            code_ed = xfer.get_components('code')
            code_ed.mask = current_system_account().get_general_mask()
            code_ed.set_action(xfer.request, xfer.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        descript, typeaccount = current_system_account().new_charts_account(self.item.code)
        error_msg = ''
        if typeaccount < 0:
            if typeaccount == -2:
                error_msg = _("Invalid code")
            if self.item.code != '':
                code_ed.set_value(self.item.code + '!')
            if self.item.id is None:
                xfer.get_components('type_of_account').set_value(None)
        elif self.item.id is None:
            xfer.get_components('type_of_account').set_value(typeaccount)
            xfer.get_components('name').set_value(descript)
            xfer.params['type_of_account'] = typeaccount
        elif typeaccount != self.item.type_of_account:
            error_msg = _("Changment not allowed!")
            code_ed.set_value(self.item.code + '!')
        if typeaccount in (ChartsAccount.TYPE_REVENUE, ChartsAccount.TYPE_EXPENSE):
            rubric_list = self.item.year.get_rubric_list()
            rubric_comp = XferCompEdit('rubric')
            rubric_comp.set_value(xfer.item.rubric)
            rubric_comp.set_location(1, xfer.get_max_row() + 1)
            rubric_comp.description = _('rubric')
            xfer.add_component(rubric_comp)
            if len(rubric_list) > 0:
                rubric_list.insert(0, '')
                sel = XferCompSelect('rubric_select')
                sel.set_select([(rubric, rubric) for rubric in rubric_list])
                sel.set_value(rubric_comp.value)
                sel.set_location(rubric_comp.col, rubric_comp.row + 1, rubric_comp.colspan, rubric_comp.rowspan)
                sel.description = rubric_comp.description
                sel.java_script = """
var rubric=current.getValue();
parent.get('rubric').setValue({'value':rubric});
"""
                xfer.add_component(sel)
                check = XferCompCheck('rubric_add')
                check.set_value(xfer.getparam('rubric_add', False))
                check.set_location(rubric_comp.col, rubric_comp.row + 2, rubric_comp.colspan, rubric_comp.rowspan)
                check.description = _('new rubric')
                check.java_script = """
var new_rubric=current.getValue();
parent.get('rubric').setVisible(new_rubric);
parent.get('rubric_select').setVisible(!new_rubric);
"""
                xfer.add_component(check)

        lbl = XferCompLabelForm('error_code')
        lbl.set_location(1, xfer.get_max_row() + 1, 2)
        lbl.set_color('red')
        lbl.set_value_center(error_msg)
        xfer.add_component(lbl)
        return

    def show(self, xfer):
        row = xfer.get_max_row() + 1
        if xfer.item.type_of_account in (ChartsAccount.TYPE_REVENUE, ChartsAccount.TYPE_EXPENSE):
            rubric_comp = XferCompLabelForm('rubric')
            rubric_comp.set_value(xfer.item.rubric)
            rubric_comp.set_location(1, row)
            rubric_comp.description = _('rubric')
            xfer.add_component(rubric_comp)
            row += 1
        comp = XferCompGrid('entryaccount')
        comp.set_model(EntryAccount.objects.filter(entrylineaccount__account=self.item).distinct(), None, xfer)
        comp.description = EntryLineAccount._meta.verbose_name
        comp.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'OpenFromLine', xfer), unique=SELECT_SINGLE, close=CLOSE_NO)
        comp.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'Close', xfer), unique=SELECT_MULTI, close=CLOSE_NO)
        if self.item.is_third:
            comp.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'Link', xfer), unique=SELECT_MULTI, close=CLOSE_NO)
        comp.set_location(1, row)
        xfer.add_component(comp)


class EntryAccountEditor(LucteriosEditor):

    def __init__(self, model):
        LucteriosEditor.__init__(self, model)
        self.added = False

    def before_save(self, xfer):
        self.item.check_date()
        return

    def _add_cost_savebtn(self, xfer):
        name_comp = xfer.get_components('designation')
        self.added = isinstance(name_comp, XferCompEdit)

    def show(self, xfer):
        self._add_cost_savebtn(xfer)
        last_row = xfer.get_max_row() + 10
        lbl = XferCompLabelForm('sep3')
        lbl.set_location(0, last_row + 1, 6)
        lbl.set_value_center("{[hr/]}")
        xfer.add_component(lbl)
        grid_lines = XferCompGrid('entrylineaccount')
        grid_lines.set_location(0, last_row + 2, 6)
        grid_lines.set_model(xfer.item.entrylineaccount_set.all(), EntryLineAccount.get_other_fields(), xfer)
        grid_lines.description = _('entry line of account')
        if len(xfer.item.entrylineaccount_set.filter(Q(account__type_of_account__in=(3, 4, 5)) & (Q(costaccounting__isnull=True) | Q(costaccounting__status=0)))) > 0:
            grid_lines.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'CostAccounting', xfer), close=CLOSE_NO, unique=SELECT_MULTI)
        xfer.add_component(grid_lines)
        if self.item.has_third:
            if self.item.is_asset:
                lbl = XferCompLabelForm('asset_warning')
                lbl.set_location(0, last_row + 3, 6)
                lbl.set_value_as_header(_("entry of accounting for an asset"))
                xfer.add_component(lbl)
        links = []
        for entryline in xfer.item.entrylineaccount_set.all():
            if entryline.link is not None:
                links.append(entryline.link)
        if len(links) > 0:
            linkentries = EntryAccount.objects.filter(entrylineaccount__link__in=links).exclude(id=self.item.id).distinct()
            if len(linkentries) == 0:
                for entryline in xfer.item.entrylineaccount_set.all():
                    entryline.unlink()
            else:
                lbl = XferCompLabelForm('sep4')
                lbl.set_location(0, last_row + 4, 6)
                lbl.set_value_center("{[hr/]}")
                xfer.add_component(lbl)
                link_grid_lines = XferCompGrid('entryaccount_link')
                link_grid_lines.description = _("Linked entries")
                link_grid_lines.set_model(linkentries, fieldnames=None, xfer_custom=xfer)
                link_grid_lines.set_location(0, last_row + 5, 6)
                link_grid_lines.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'OpenFromLine', xfer), unique=SELECT_SINGLE, close=CLOSE_YES, params={'field_id': 'entryaccount_link', 'journal': ''})
                xfer.add_component(link_grid_lines)
        if self.added:
            xfer.add_action(xfer.return_action(TITLE_MODIFY, short_icon='mdi:mdi-check'), params={"SAVE": "YES"})

    def _entryline_editor(self, xfer, serial_vals, debit_rest, credit_rest):
        last_row = xfer.get_max_row() + 5
        lbl = XferCompLabelForm('sep1')
        lbl.set_location(0, last_row, 6)
        lbl.set_value("{[center]}{[hr/]}{[/center]}")
        xfer.add_component(lbl)
        lbl = XferCompLabelForm('sep2')
        lbl.set_location(1, last_row + 1, 5)
        lbl.set_value_center(_("Add a entry line"))
        xfer.add_component(lbl)
        entry_line = EntryLineAccount()
        entry_line.editor.edit_line(xfer, 0, last_row + 2, debit_rest, credit_rest)
        if entry_line.has_account:
            btn = XferCompButton('entrybtn')
            btn.is_default = True
            btn.set_location(3, last_row + 5, 2)
            btn.set_action(xfer.request, ActionsManage.get_action_url(
                'accounting.EntryLineAccount', 'Add', xfer), close=CLOSE_YES)
            xfer.add_component(btn)
        self.item.editor.show(xfer)
        grid_lines = xfer.get_components('entrylineaccount')
        xfer.remove_component('entrylineaccount')
        new_grid_lines = XferCompGrid('entrylineaccount_serial')
        new_grid_lines.description = grid_lines.description
        new_grid_lines.set_model(self.item.get_entrylineaccounts(serial_vals), EntryLineAccount.get_other_fields(), xfer)
        new_grid_lines.set_location(grid_lines.col, grid_lines.row, grid_lines.colspan, grid_lines.rowspan)
        new_grid_lines.add_action_notified(xfer, EntryLineAccount)
        xfer.add_component(new_grid_lines)
        nb_lines = len(new_grid_lines.record_ids)
        return nb_lines

    def _remove_lastyear_notbuilding(self, xfer):
        if self.item.year.status != FiscalYear.STATUS_BUILDING:
            cmp_journal = xfer.get_components('journal')
            select_list = cmp_journal.select_list
            for item_idx in range(len(select_list)):
                if select_list[item_idx][0] == 1:
                    del select_list[item_idx]
                    break
            cmp_journal.select_list = select_list

    def edit(self, xfer):
        self._remove_lastyear_notbuilding(xfer)
        if (self.item.id is None) and not Params.getvalue('accounting-datecurrent'):
            date_cmp = xfer.get_components('date_value')
            date_cmp.value = None
        serial_vals = xfer.getparam('serial_entry')
        if serial_vals is None:
            xfer.params['serial_entry'] = self.item.get_serial()
            serial_vals = xfer.getparam('serial_entry')
        xfer.no_change, xfer.debit_rest, xfer.credit_rest = self.item.serial_control(serial_vals)
        if self.item.id:
            xfer.nb_lines = self._entryline_editor(xfer, serial_vals, xfer.debit_rest, xfer.credit_rest)
            self.added = True
        else:
            self._add_cost_savebtn(xfer)
            xfer.nb_lines = 0
        xfer.added = self.added


def edit_third_for_line(xfer, column, row, account_code, current_third, vertical=True):
    sel_thirds = []
    for third in Third.objects.filter(accountthird__code=account_code).distinct():
        sel_thirds.append((third.id, str(third)))
    sel_thirds = sorted(sel_thirds, key=lambda third_item: third_item[1])
    if len(sel_thirds) > 0:
        sel_thirds.insert(0, (0, '---'))
        cb_third = XferCompSelect('third')
        cb_third.set_select(sel_thirds)
        if current_third is None:
            cb_third.set_value(xfer.getparam('third', 0))
        else:
            cb_third.set_value(xfer.getparam('third', current_third.id))
        if vertical:
            lbl = XferCompLabelForm('thirdlbl')
            lbl.set_value_as_name(_('third'))
            lbl.set_location(column, row, 2)
            xfer.add_component(lbl)
            cb_third.set_location(column, row + 1, 2)
        else:
            cb_third.set_location(column, row)
            cb_third.description = _('third')
        xfer.add_component(cb_third)
        btn_new = XferCompButton('new-third')
        btn_new.set_is_mini(True)
        btn_new.set_location(cb_third.col + cb_third.colspan, cb_third.row)
        btn_new.set_action(xfer.request, ActionsManage.get_action_url('accounting.Third', 'Add', xfer),
                           modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'new_account': account_code})
        xfer.add_component(btn_new)


class EntryLineAccountEditor(LucteriosEditor):

    def edit_account_for_line(self, xfer, column, row, debit_rest, credit_rest):
        num_cpt_txt = xfer.getparam('num_cpt_txt', '')
        num_cpt = xfer.getparam('num_cpt', 0)

        lbl = XferCompLabelForm('numCptlbl')
        lbl.set_location(column, row, 2)
        lbl.set_value_as_headername(_('account'))
        xfer.add_component(lbl)
        edt = XferCompEdit('num_cpt_txt')
        edt.set_location(column, row + 1)
        edt.set_value(num_cpt_txt)
        edt.set_action(xfer.request, xfer.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        xfer.add_component(edt)
        sel_val = []
        current_account = None
        if num_cpt_txt != '':
            year = FiscalYear.get_current(xfer.getparam('year'))
            sel_val, current_account = year.get_account_list(num_cpt_txt, num_cpt)
        sel = XferCompSelect('num_cpt')
        sel.set_location(column + 1, row + 1, 1)
        sel.set_select(sel_val)
        sel.set_action(xfer.request, xfer.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        if current_account is not None:
            sel.set_value(current_account.id)
            self.item.account = current_account
            self.item.set_montant(float(xfer.getparam('debit_val', 0.0)), float(xfer.getparam('credit_val', 0.0)))
            if abs(self.item.amount) < 0.0001:
                self.item.set_montant(debit_rest, credit_rest)
        xfer.add_component(sel)
        if (num_cpt_txt != '') and (len(sel.select_list) == 0) and (current_system_account().new_charts_account(num_cpt_txt)[1] >= 0):
            btn_new = XferCompButton('new-cpt')
            btn_new.set_is_mini(True)
            btn_new.set_location(column + 2, row + 1, 1)
            btn_new.set_action(xfer.request, ActionsManage.get_action_url('accounting.ChartsAccount', 'AddModify', xfer), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'code': num_cpt_txt})
            xfer.add_component(btn_new)
        return lbl, edt

    def edit_extra_for_line(self, xfer, column, row, vertical=True):
        try:
            if self.item.has_account and self.item.account.is_third:
                edit_third_for_line(xfer, column, row, self.item.account.code, self.item.third, vertical)
            elif self.item.account.type_of_account in (3, 4, 5):
                sel = XferCompSelect('costaccounting')
                if hasattr(xfer.item, 'year'):
                    current_year = xfer.item.year
                    current_costaccounting = None
                else:
                    current_year = xfer.item.entry.year
                    current_costaccounting = self.item.costaccounting
                sel.set_select_query(CostAccounting.objects.filter(Q(status=0) & (Q(year=None) | Q(year=current_year))).distinct())
                sel.set_needed(Params.getvalue('accounting-needcost'))
                if current_costaccounting is not None:
                    sel.set_value(current_costaccounting.id)
                elif Params.getvalue('accounting-needcost'):
                    default_costaccointing = CostAccounting.objects.filter(Q(status=0) & (Q(year=None) | Q(year=current_year)) & Q(is_default=True)).first()
                    if default_costaccointing is not None:
                        sel.set_value(default_costaccointing.id)
                if vertical:
                    sel.set_location(column, row + 1, 2)
                    lbl = XferCompLabelForm('costaccountinglbl')
                    lbl.set_value_as_name(_('cost accounting'))
                    lbl.set_location(column, row)
                    xfer.add_component(lbl)
                else:
                    sel.set_location(column, row)
                    sel.description = _('cost accounting')
                xfer.add_component(sel)
            else:
                edt = XferCompEdit('reference')
                reference = xfer.getparam('reference', self.item.reference)
                if reference is not None:
                    edt.set_value(reference)
                if vertical:
                    edt.set_location(column, row + 1, 2)
                    lbl = XferCompLabelForm('referencelbl')
                    lbl.set_value_as_name(_('reference'))
                    lbl.set_location(column, row)
                    xfer.add_component(lbl)
                else:
                    edt.set_location(column, row)
                    edt.description = _('reference')
                xfer.add_component(edt)
        except ObjectDoesNotExist:
            pass

    def edit_creditdebit_for_line(self, xfer, column, row):
        currency_decimal = Params.getvalue("accounting-devise-prec")
        edt = XferCompFloat('debit_val', -10000000, 10000000, currency_decimal)
        edt.set_location(column, row, 2)
        edt.set_value(self.item.get_debit(with_correction=False))
        edt.description = _('debit')
        xfer.add_component(edt)
        edt = XferCompFloat('credit_val', -10000000, 10000000, currency_decimal)
        edt.set_location(column, row + 1, 2)
        edt.set_value(self.item.get_credit())
        edt.description = _('credit')
        xfer.add_component(edt)

    def edit_line(self, xfer, init_col, init_row, debit_rest, credit_rest):
        self.edit_account_for_line(xfer, init_col, init_row, debit_rest, credit_rest)
        self.edit_creditdebit_for_line(xfer, init_col + 1, init_row + 2)
        self.edit_extra_for_line(xfer, init_col + 3, init_row)


class ModelEntryEditor(EntryLineAccountEditor):

    def edit(self, xfer):
        comp_journal = xfer.get_components('journal')
        select_jrn = comp_journal.select_list
        for item_idx in range(len(select_jrn)):
            if select_jrn[item_idx][0] == 1:
                del select_jrn[item_idx]
                break
        comp_journal.select_list = select_jrn
        sel = xfer.get_components('costaccounting')
        sel.set_select_query(CostAccounting.objects.filter(Q(status=0) & (Q(year=None) | Q(year=FiscalYear.get_current()))).distinct())


class ModelLineEntryEditor(EntryLineAccountEditor):

    def edit(self, xfer):
        xfer.params['model'] = xfer.getparam('modelentry', 0)
        code = xfer.get_components('code')
        xfer.remove_component('code')

        codetxt = xfer.getparam('code_txt', xfer.item.code)
        code_txt = XferCompEdit('code_txt')
        code_txt.set_location(code.col, code.row)
        code_txt.set_value(codetxt)
        code_txt.set_needed(True)
        code_txt.set_action(xfer.request, xfer.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        code_txt.description = _('search code')
        xfer.add_component(code_txt)
        sel_val = []
        if codetxt != '':
            year = FiscalYear.get_current()
            for account in year.chartsaccount_set.all().filter(code__startswith=codetxt).order_by('code'):
                sel_val.append((account.code, str(account)))
        sel = XferCompSelect('code')
        sel.set_location(code.col, code.row + 1)
        sel.set_select(sel_val)
        sel.set_value(xfer.item.code)
        sel.description = code.description
        xfer.add_component(sel)
        if match(current_system_account().get_third_mask(), sel.value) is not None:
            edit_third_for_line(xfer, 1, xfer.get_max_row() + 1, sel.value, None, False)
        self.edit_creditdebit_for_line(xfer, 1, xfer.get_max_row() + 1)

    def before_save(self, xfer):
        self.item.set_montant(xfer.getparam('debit_val', 0.0), xfer.getparam('credit_val', 0.0))


class BudgetEditor(EntryLineAccountEditor):

    def edit(self, xfer):
        self.edit_creditdebit_for_line(xfer, 1, xfer.get_max_row() + 1)
        if xfer.field_id == 'budget_revenue':
            code_mask = current_system_account().get_revenue_mask() + "|" + current_system_account().get_annexe_mask()
        elif xfer.field_id == 'budget_expense':
            code_mask = current_system_account().get_expence_mask() + "|" + current_system_account().get_annexe_mask()
        else:
            code_mask = current_system_account().get_revenue_mask() + "|" + current_system_account().get_expence_mask() + "|" + current_system_account().get_annexe_mask()
        old_account = xfer.get_components("code")
        xfer.remove_component("code")
        sel_code = XferCompSelect("code")
        sel_code.set_location(old_account.col, old_account.row, old_account.colspan + 1, old_account.rowspan)
        for item in FiscalYear.get_current().chartsaccount_set.all().filter(code__regex=code_mask).order_by('code'):
            sel_code.select_list.append((item.code, str(item)))
        sel_code.set_value(self.item.code)
        xfer.add_component(sel_code)

    def before_save(self, xfer):
        self.item.set_montant(xfer.getparam('debit_val', 0.0), xfer.getparam('credit_val', 0.0))
