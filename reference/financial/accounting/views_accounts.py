# -*- coding: utf-8 -*-
'''
Describe entries account viewer for Django

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
from os.path import basename
from datetime import date

from django.utils.translation import gettext_lazy as _
from django.utils import formats
from django.db.models import Q

from lucterios.framework.xferadvance import XferListEditor, TITLE_ADD, TITLE_MODIFY, TITLE_EDIT, TITLE_DELETE, TITLE_LISTING, TITLE_OK, TITLE_CANCEL
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, SELECT_SINGLE, WrapAction, SELECT_MULTI, SELECT_NONE, \
    FORMTYPE_MODAL, CLOSE_YES
from lucterios.framework.tools import ActionsManage, MenuManage
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompImage, \
    XferCompButton, XferCompSelect
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XFER_DBOX_WARNING
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework import signal_and_lock
from lucterios.framework.model_fields import get_value_if_choices
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.CORE.xferprint import XferPrintListing
from lucterios.CORE.views import ObjectMerge

from diacamma.accounting.models import ChartsAccount, FiscalYear, EntryAccount
from diacamma.accounting.views_entries import add_fiscalyear_result

MenuManage.add_sub("bookkeeping", "financial", short_icon='mdi:mdi-bank', caption=_("Bookkeeping"), desc=_("Manage of Bookkeeping"), pos=30)


@ActionsManage.affect_other(_("Charts of account"), short_icon="mdi:mdi-bank-transfer")
@MenuManage.describ('accounting.change_chartsaccount', FORMTYPE_NOMODAL, 'bookkeeping', _('Editing and modifying of Charts of accounts for current fiscal year'))
class ChartsAccountList(XferListEditor):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Charts of account")
    multi_page = False

    def fillresponse_header(self):
        select_year = self.getparam('year')
        select_type = self.getparam('type_of_account', ChartsAccount.TYPE_ASSET)
        self.item.year = FiscalYear.get_current(select_year)
        self.fill_from_model(0, 1, False, ['year', 'type_of_account'])
        comp_year = self.get_components('year')
        comp_year.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        comp_year.colspan = 2
        btn = XferCompButton('confyear')
        btn.set_location(comp_year.col + comp_year.colspan, comp_year.row)
        btn.set_action(self.request, ActionsManage.get_action_url(FiscalYear.get_long_name(), 'configuration', self), close=CLOSE_NO)
        btn.set_is_mini(True)
        self.add_component(btn)
        type_of_account = self.get_components('type_of_account')
        type_of_account.colspan = 2
        type_of_account.select_list.append((-1, '---'))
        type_of_account.set_value(select_type)
        type_of_account.set_action(self.request, ChartsAccountList.get_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.filter = Q(year=self.item.year)
        if select_type != -1:
            self.filter &= Q(type_of_account=select_type)
        if select_type in (ChartsAccount.TYPE_REVENUE, ChartsAccount.TYPE_EXPENSE):
            self.fieldnames = ChartsAccount.get_default_fields()
            self.fieldnames.insert(2, 'rubric')

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        chartsaccount = self.get_components('chartsaccount')
        chartsaccount.colspan = 3
        add_fiscalyear_result(self, 0, 10, 2, self.item.year, "result")
        if self.item.year == FiscalYear.get_current():
            accompt_returned = []
            cost_returned = []
            all_codes = list(self.item.year.chartsaccount_set.all().values_list('code', flat=True))
            all_codes.append('')
            Signal.call_signal("compte_no_found", all_codes, accompt_returned, cost_returned)
            if len(accompt_returned) > 0:
                lbl = XferCompLabelForm("CompteNoFound")
                lbl.set_value("{[u]}{[b]}%s{[/b]}{[/u]}{[br]}%s" % (_("Using codes unknows in this account chart:"), "{[br/]}".join(accompt_returned)))
                lbl.set_location(0, 11, 2)
                self.add_component(lbl)
            if len(cost_returned) > 0:
                lbl = XferCompLabelForm("CostNoFound")
                lbl.set_value("{[u]}{[b]}%s{[/b]}{[/u]}{[br]}%s" % (_("Using bad cost accounting in this fiscal year:"), "{[br/]}".join(cost_returned)))
                lbl.set_location(0, 12, 2)
                self.add_component(lbl)


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', condition=lambda xfer, gridname='': xfer.item.year.status != 2)
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', condition=lambda xfer: xfer.item.year.status != 2)
@MenuManage.describ('accounting.add_chartsaccount')
class ChartsAccountAddModify(XferAddEditor):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption_add = _("Add an account")
    caption_modify = _("Modify an account")
    redirect_to_show = None

    def fill_simple_fields(self):
        keys_to_remove = ['type_of_account']
        if self.item.has_validated:
            keys_to_remove.append("code")
        for old_key in keys_to_remove:
            if old_key in self.params.keys():
                del self.params[old_key]
        return XferAddEditor.fill_simple_fields(self)


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.change_chartsaccount')
class ChartsAccountShow(XferShowEditor):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Show an account")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.item.year.status != 2)
@MenuManage.describ('accounting.delete_chartsaccount')
class ChartsAccountDel(XferDelete):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Delete an account")


@ActionsManage.affect_grid(_("Import"), short_icon="mdi:mdi-upload-box-outline", unique=SELECT_NONE, condition=lambda xfer, gridname: (xfer.item.year.status != 2) and (xfer.item.year.last_fiscalyear is not None))
@MenuManage.describ('accounting.add_chartsaccount')
class ChartsAccountImportFiscalYear(XferContainerAcknowledge):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Import charts accounts from last fiscal year")

    def fillresponse(self, year=0):
        year = FiscalYear.objects.get(id=year)
        if self.confirme(_("Do you want to import last year charts accounts?")):
            year.import_charts_accounts()


@ActionsManage.affect_grid(_("Merge"), short_icon='mdi:mdi-set-merge', close=CLOSE_NO, unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.item.year.status != 2)
@MenuManage.describ('accounting.add_chartsaccount')
class ChartsAccountMerge(ObjectMerge):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'

    def __init__(self, **kwargs):
        ObjectMerge.__init__(self, **kwargs)
        self.params['modelname'] = ChartsAccount.get_long_name()

    def fillresponse(self):
        type_of_account = None
        for item in self.items:
            if item.has_validated:
                raise LucteriosException(IMPORTANT, _('Merge not possible !'))
            if type_of_account is None:
                type_of_account = item.type_of_account
            elif type_of_account != item.type_of_account:
                raise LucteriosException(IMPORTANT, _('Merge not possible !'))
        ObjectMerge.fillresponse(self, 'chartsaccount')


@ActionsManage.affect_grid(_("Initial"), short_icon='mdi:mdi-pencil-plus-outline', close=CLOSE_NO, unique=SELECT_NONE, condition=lambda xfer, gridname='': (xfer.item.year.status != 2) and (signal_and_lock.Signal.call_signal("initial_account", None) > 0))
@MenuManage.describ('accounting.add_chartsaccount')
class ChartsAccountInitial(XferContainerAcknowledge):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Add initial charts of account")

    def fillresponse(self, account_item=""):
        account_list = []
        signal_and_lock.Signal.call_signal("initial_account", account_list)
        if len(account_list) == 1:
            if self.confirme(_('Do you want to import initial accounts?')):
                ChartsAccount.import_initial(FiscalYear.get_current(self.getparam('year')), account_list[0])
        elif len(account_list) > 1:
            if account_item not in account_list:
                select_list = {}
                for account_item in account_list:
                    filename = basename(account_item).split('-')[-1].split('.')[0]
                    select_list[account_item] = filename.replace('_', ' ')
                dlg = self.create_custom()
                img = XferCompImage('img')
                img.set_value(self.short_icon, '#')
                img.set_location(0, 0, 1, 3)
                dlg.add_component(img)
                lbl = XferCompLabelForm('title')
                lbl.set_value_as_title(self.caption)
                lbl.set_location(1, 0)
                dlg.add_component(lbl)
                sel = XferCompSelect('account_item')
                sel.set_select(select_list)
                sel.set_location(1, 1)
                dlg.add_component(sel)
                dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), close=CLOSE_YES)
                dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
            else:
                ChartsAccount.import_initial(FiscalYear.get_current(self.getparam('year')), account_item)


@ActionsManage.affect_list(TITLE_LISTING, short_icon='mdi:mdi-printer-pos-edit-outline')
@MenuManage.describ('accounting.change_chartsaccount')
class ChartsAccountListing(XferPrintListing):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Listing charts of account")

    def get_filter(self):
        if self.getparam('CRITERIA') is None:
            select_year = self.getparam('year')
            select_type = self.getparam('type_of_account', 0)
            new_filter = Q(year=FiscalYear.get_current(select_year))
            if select_type != -1:
                new_filter &= Q(type_of_account=select_type)
        else:
            new_filter = XferPrintListing.get_filter(self)
        return new_filter

    def fillresponse(self):
        self.caption = _("Listing charts of account") + " - " + formats.date_format(date.today(), "DATE_FORMAT")
        if self.getparam('CRITERIA') is None:
            info_list = []
            select_year = self.getparam('year')
            info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('fiscal year'), str(FiscalYear.get_current(select_year))))
            select_type = self.getparam('type_of_account', 0)
            if select_type >= 0:
                dep_field = self.item.get_field_by_name("type_of_account")
                info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (dep_field.verbose_name, get_value_if_choices(select_type, dep_field)))
            self.info = '{[br]}'.join(info_list)
        XferPrintListing.fillresponse(self)


@ActionsManage.affect_list(_('Last fiscal year'), short_icon='mdi:mdi-calendar-arrow-right',
                           condition=lambda xfer: (xfer.item.year.status == FiscalYear.STATUS_BUILDING) and (xfer.item.year.last_fiscalyear is not None) and xfer.item.year.has_no_lastyear_entry and (xfer.item.year.last_fiscalyear.status == FiscalYear.STATUS_FINISHED))
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearReportLastYear(XferContainerAcknowledge):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Last fiscal year import")

    def fillresponse(self, year=0):
        current_year = FiscalYear.objects.get(id=year)
        if self.confirme(_('Do you want to import last year result?')):
            signal_and_lock.Signal.call_signal("reportlastyear", self)
            warning_text = current_year.run_report_lastyear(self.getparam("import_result", True))
            signal_and_lock.Signal.call_signal("reportlastyear_after", self)
            if warning_text != '':
                self.message(warning_text, XFER_DBOX_WARNING)


@ActionsManage.affect_list(_('Begin'), short_icon='mdi:mdi-check', condition=lambda xfer: xfer.item.year.status == FiscalYear.STATUS_BUILDING, intop=True)
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearBegin(XferContainerAcknowledge):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption_add = _("Begin fiscal year")

    def fillresponse(self, year=0):
        current_year = FiscalYear.objects.get(id=year)
        current_year.editor.run_begin(self)


@ActionsManage.affect_list(_('Closing'), short_icon='mdi:mdi-check', condition=lambda xfer: xfer.item.year.status == FiscalYear.STATUS_RUNNING, intop=True)
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearClose(XferContainerAcknowledge):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Close fiscal year")

    def fillresponse(self, year=0):
        current_year = FiscalYear.objects.get(id=year)
        if self.getparam("CONFIRME") is None:
            nb_entry_noclose = current_year.check_to_close()
            text_confirm = str(_('close-fiscal-year-confirme'))
            if nb_entry_noclose > 0:
                if nb_entry_noclose == 1:
                    text_confirm += str(_('warning, entry no validated'))
                else:
                    text_confirm += str(_('warning, %d entries no validated') % nb_entry_noclose)
            dlg = self.create_custom(self.model)
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0)
            dlg.add_component(img)
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_title(self.caption)
            lbl.set_location(1, 0)
            dlg.add_component(lbl)
            lab = XferCompLabelForm('info')
            lab.set_value(text_confirm)
            lab.set_location(0, 1, 4)
            dlg.add_component(lab)
            signal_and_lock.Signal.call_signal("finalize_year", dlg)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), modal=FORMTYPE_MODAL, close=CLOSE_YES, params={'CONFIRME': 'YES'})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            EntryAccount.clear_ghost()
            signal_and_lock.Signal.call_signal("finalize_year", self)
            current_year.set_context(self)
            current_year.closed()
            signal_and_lock.Signal.call_signal("finalize_year_after", self)
