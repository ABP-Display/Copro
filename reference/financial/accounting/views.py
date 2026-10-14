# -*- coding: utf-8 -*-
'''
Describe view for Django

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
from datetime import timedelta, date
import re

from django.utils.translation import gettext_lazy as _
from django.db.models.functions import Concat
from django.db.models import Q, Value
from django.utils import formats

from lucterios.framework import signal_and_lock
from lucterios.framework.xferadvance import XferListEditor, XferAddEditor, XferShowEditor, XferDelete, \
    TITLE_ADD, TITLE_EDIT, TITLE_DELETE, TITLE_OK, TITLE_CANCEL, XferTransition, \
    TITLE_CREATE, TITLE_SEARCH, TITLE_MODIFY
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit, XferCompButton, XferCompSelect, XferCompImage, XferCompDate, XferCompGrid
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, FORMTYPE_REFRESH, CLOSE_NO, WrapAction, FORMTYPE_MODAL, SELECT_SINGLE, SELECT_MULTI, SELECT_NONE, CLOSE_YES
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework.models import LucteriosQuerySet
from lucterios.CORE.xferprint import XferPrintListing
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor
from lucterios.CORE.parameters import Params
from lucterios.contacts.tools import ContactSelection
from lucterios.contacts.models import AbstractContact

from diacamma.accounting.models import Third, AccountThird, FiscalYear, EntryLineAccount, ModelLineEntry, ChartsAccount, ModelEntry,\
    is_with_VAT
from diacamma.accounting.views_admin import Configuration, add_year_info
from diacamma.accounting.tools import correct_accounting_code, current_system_account
from django.db.models.aggregates import Count
from diacamma.accounting.views_entries import add_fiscalyear_result

MenuManage.add_sub("financial", None, short_icon='mdi:mdi-bank-outline', caption=_("Financial"), desc=_("Financial tools"), pos=50)


@MenuManage.describ('accounting.change_third', FORMTYPE_NOMODAL, 'financial', _('Management of third account'))
class ThirdList(XferListEditor):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'
    caption = _("Thirds")

    def get_items_from_filter(self):
        items = self.model.objects.select_related('contact', 'contact__individual', 'contact__legalentity').annotate(completename=Concat('contact__individual__lastname', Value(' '), 'contact__individual__firstname')).annotate(num_entryline=Count('entrylineaccount')).filter(self.filter).distinct()
        sort_third = self.getparam('GRID_ORDER%third', '')
        sort_thirdbis = self.getparam('GRID_ORDER%third+', '')
        self.params['GRID_ORDER%third'] = ""
        if sort_third != '':
            if sort_thirdbis.startswith('-'):
                sort_thirdbis = "+"
            else:
                sort_thirdbis = "-"
            self.params['GRID_ORDER%third+'] = sort_thirdbis
        items = sorted(items, key=lambda t: str(t).lower(), reverse=sort_thirdbis.startswith('-'))
        if self.getparam('show_filter', 0) == 2:
            items = [item for item in items if abs(item.get_total()) > 0.0001]
        return LucteriosQuerySet(model=Third, initial=items)

    def fillresponse_header(self):
        contact_filter = self.getparam('filter', '')
        show_filter = self.getparam('show_filter', 0)
        thirdtype = self.getparam('thirdtype', 0)
        comp = XferCompEdit('filter')
        comp.set_value(contact_filter)
        comp.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        comp.set_location(0, 2, 2)
        comp.description = _('Filtrer by contact')
        comp.is_default = True
        self.add_component(comp)

        edt = XferCompSelect("thirdtype")
        edt.set_select([(0, '---'), (1, _('Customer')), (2, _('Provider')), (3, _('Shareholder')), (4, _('Employee'))])
        edt.set_value(thirdtype)
        edt.set_location(0, 3, 2)
        edt.description = _('Third type')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        edt = XferCompSelect("show_filter")
        edt.set_select([(0, _('Hide the account total of thirds')), (1, _('Show the account total of thirds')),
                        (2, _('Filter any thirds unbalanced')), (3, _('Filter any thirds with entries without link'))])
        edt.set_value(show_filter)
        edt.description = _('Accounts displayed')
        edt.set_location(0, 4, 2)
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)
        if show_filter != 0:
            self.fieldnames = Third.get_other_fields()

        self.filter = Q(status=0)
        if contact_filter != "":
            q_legalentity = Q(contact__legalentity__name__icontains=contact_filter)
            q_individual = Q(completename__icontains=contact_filter)
            self.filter &= (q_legalentity | q_individual)
        if thirdtype == 1:
            self.filter &= Q(accountthird__code__regex=current_system_account().get_customer_mask())
        elif thirdtype == 2:
            self.filter &= Q(accountthird__code__regex=current_system_account().get_provider_mask())
        elif thirdtype == 3:
            self.filter &= Q(accountthird__code__regex=current_system_account().get_societary_mask())
        elif thirdtype == 4:
            self.filter &= Q(accountthird__code__regex=current_system_account().get_employed_mask())
        if show_filter == 3:
            self.filter &= Q(entrylineaccount__link__isnull=True) & Q(num_entryline__gt=0)


@ActionsManage.affect_list(TITLE_SEARCH, short_icon='mdi:mdi-account-search', condition=lambda xfer: xfer.get_components('thirdtype'))
@MenuManage.describ('accounting.change_third')
class ThirdSearch(XferSavedCriteriaSearchEditor):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'
    caption = _("Search third")


@MenuManage.describ('accounting.add_third')
class ThirdSave(XferContainerAcknowledge):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = ''

    def fillresponse(self, pkname='', new_account=[]):
        contact_id = self.getparam(pkname, 0)
        if contact_id == 1:
            raise LucteriosException(IMPORTANT, _("Current structure can't be third !"))
        last_thirds = Third.objects.filter(contact__pk=contact_id)
        if len(last_thirds) > 0:
            self.item = last_thirds[0]
        else:
            self.item.contact = AbstractContact.objects.get(id=contact_id)
            self.item.status = Third.STATUS_ENABLE
            self.item.save()
        for item_account in new_account:
            old_account = self.item.accountthird_set.filter(code=correct_accounting_code(item_account))
            if len(old_account) == 0:
                AccountThird.objects.create(third=self.item, code=correct_accounting_code(item_account))
        redirect_after_save = self.getparam('REDIRECT_AFTER_SAVE')
        if redirect_after_save is None:
            self.redirect_action(ThirdShow.get_action(), params={'third': self.item.id})
        else:
            if 'URL_TO_REDIRECT' in self.params:
                del self.params['URL_TO_REDIRECT']
            self.redirect_action(WrapAction('', self.short_icon, url_text=redirect_after_save), params={'third': self.item.id})


@ActionsManage.affect_list(_('Disabled'), short_icon='mdi:mdi-account-off')
@MenuManage.describ('accounting.add_third')
class ThirdDisable(XferContainerAcknowledge):
    model = Third
    short_icon = "mdi:mdi-account-cash-outline"
    caption = _("Disable third")

    def fillresponse(self, limit_date=''):
        if limit_date == '':
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 6)
            dlg.add_component(img)
            limite_date = XferCompDate('limit_date')
            limite_date.set_needed(True)
            limite_date.set_value((date.today() - timedelta(weeks=25)))
            limite_date.set_location(1, 2, 1)
            limite_date.description = _('limit date')
            dlg.add_component(limite_date)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), params={"SAVE": "YES"})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            third_ids = [val_third['third'] for val_third in EntryLineAccount.objects.filter(entry__date_value__gt=limit_date, third__gt=0).values('third')]
            for third in Third.objects.filter(status=Third.STATUS_ENABLE):
                if third.id not in third_ids:
                    third.status = Third.STATUS_DISABLE
                    third.save()


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus', unique=SELECT_NONE)
@MenuManage.describ('accounting.add_third')
class ThirdAdd(ContactSelection):
    short_icon = "mdi:mdi-account-cash-outline"
    caption = _("Add third")
    select_class = ThirdSave
    model = Third
    readonly = False
    methods_allowed = ('POST', 'PUT')

    def fillresponse(self):
        third_filter = self.getparam('filter', '')
        if (third_filter != '') and (self.getparam('CRITERIA') is None):
            self.params['CRITERIA'] = '[["name",5,"%s"],["lastname",5,"%s"]]' % (third_filter, third_filter)
        ContactSelection.fillresponse(self)
        grid = self.get_components(self.field_id)
        for action_idx in range(0, len(grid.actions)):
            if grid.actions[action_idx][0].short_icon.endswith('pencil-plus-outline'):
                params = grid.actions[action_idx][4]
                if params is None:
                    params = {}
                params['URL_TO_REDIRECT'] = self.select_class.url_text
                params['pkname'] = self.field_id
                for criteria_item in self.criteria_list:
                    if len(criteria_item) > 2:
                        params[criteria_item[0]] = criteria_item[2]
                grid.actions[action_idx] = (grid.actions[action_idx][0], grid.actions[action_idx][1], CLOSE_YES, grid.actions[action_idx][3], params)


@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', condition=lambda xfer: len(Third.get_fields_to_show()) > 0)
@MenuManage.describ('accounting.add_third')
class ThirdEdit(XferAddEditor):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'
    caption_modify = _("Modify third")
    redirect_to_show = False


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.change_third')
class ThirdShow(XferShowEditor):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'
    caption = _("Show third")


@ActionsManage.affect_transition("status")
@MenuManage.describ('accounting.add_third')
class ThirdTransition(XferTransition):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.delete_third')
class ThirdDel(XferDelete):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'
    caption = _("Delete third")


@ActionsManage.affect_list(_("Listing"), short_icon='mdi:mdi-printer-pos-edit-outline')
@MenuManage.describ('accounting.change_third')
class ThirdListing(XferPrintListing):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Third
    field_id = 'third'
    caption = _("Listing third")

    def filter_callback(self, items):
        items = sorted(items, key=lambda t: str(t))
        if (self.getparam('CRITERIA') is None) and (self.getparam('show_filter', 0) == 2):
            items = [item for item in items if abs(item.get_total()) > 0.0001]
        return LucteriosQuerySet(model=Third, initial=items)

    def get_filter(self):
        if self.getparam('CRITERIA') is None:
            contact_filter = self.getparam('filter', '')
            thirdtype = self.getparam('thirdtype', 0)
            show_filter = self.getparam('show_filter', 0)
            new_filter = Q(status=0)
            if contact_filter != "":
                q_legalentity = Q(contact__legalentity__name__icontains=contact_filter)
                q_individual = (Q(contact__individual__firstname__icontains=contact_filter) | Q(
                    contact__individual__lastname__icontains=contact_filter))
                new_filter &= (q_legalentity | q_individual)
            if thirdtype == 1:
                new_filter &= Q(accountthird__code__regex=current_system_account().get_customer_mask())
            elif thirdtype == 2:
                new_filter &= Q(accountthird__code__regex=current_system_account().get_provider_mask())
            elif thirdtype == 3:
                new_filter &= Q(accountthird__code__regex=current_system_account().get_societary_mask())
            elif thirdtype == 4:
                new_filter &= Q(accountthird__code__regex=current_system_account().get_employed_mask())
            if show_filter == 3:
                new_filter &= Q(entrylineaccount__link__isnull=True)
        else:
            new_filter = XferPrintListing.get_filter(self)
        return new_filter

    def fillresponse(self):
        self.caption = _("Listing third") + " - " + formats.date_format(date.today(), "DATE_FORMAT")
        if self.getparam('CRITERIA') is None:
            info_list = []
            contact_filter = self.getparam('filter', '')
            thirdtype = self.getparam('thirdtype', 0)
            if contact_filter != "":
                info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('Filtrer by contact'), contact_filter))
            thirdtype_list = {1: _('Customer'), 2: _('Provider'), 3: _('Shareholder'), 4: _('Employee')}
            if thirdtype != 0:
                info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('Third type'), thirdtype_list[thirdtype]))
            if (self.getparam('show_filter', 0) == 2):
                info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('Accounts displayed'), _('Filter any thirds unbalanced')))
            elif (self.getparam('show_filter', 0) == 3):
                info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('Accounts displayed'), _('Filter any thirds with entries without link')))
            self.info = '{[br]}'.join(info_list)
        XferPrintListing.fillresponse(self)


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', unique=SELECT_NONE)
@MenuManage.describ('accounting.add_third')
class AccountThirdAddModify(XferAddEditor):
    short_icon = "mdi:mdi-bank-transfer"
    model = AccountThird
    field_id = 'accountthird'
    caption_add = _("Add account")
    caption_modify = _("Modify account")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.add_third')
class AccountThirdDel(XferDelete):
    short_icon = "mdi:mdi-bank-transfer"
    model = AccountThird
    field_id = 'accountthird'
    caption = _("Delete account")


@signal_and_lock.Signal.decorate('summary')
def summary_accounting(xfer):
    if not hasattr(xfer, 'add_component'):
        return WrapAction.is_permission(xfer, 'accounting.change_chartsaccount')
    elif WrapAction.is_permission(xfer.request, 'accounting.change_chartsaccount'):
        row = xfer.get_max_row() + 1
        lab = XferCompLabelForm('accountingtitle')
        lab.set_value_as_infocenter(_("Bookkeeping"))
        lab.set_location(0, row, 4)
        xfer.add_component(lab)
        try:
            year = FiscalYear.get_current()
            lbl = XferCompLabelForm("accounting_year")
            lbl.set_value_center(str(year))
            lbl.set_location(0, row + 1, 4)
            xfer.add_component(lbl)
            add_fiscalyear_result(xfer, 0, row + 2, 4, year, "accounting_result")
            if len(ChartsAccount.objects.filter(year=year)) == 0:
                add_year_info(xfer, True)
        except LucteriosException as lerr:
            lbl = XferCompLabelForm("accounting_error")
            lbl.set_value_center(str(lerr))
            lbl.set_location(0, row + 1, 4)
            xfer.add_component(lbl)
            btn = XferCompButton("accounting_conf")
            btn.set_action(xfer.request, Configuration.get_action(_("conf."), ""), close=CLOSE_NO)
            btn.set_location(0, row + 2, 4)
            xfer.add_component(btn)
        row = xfer.get_max_row() + 1
        lab = XferCompLabelForm('accountingend')
        lab.set_value_center('{[hr/]}')
        lab.set_location(0, row, 4)
        xfer.add_component(lab)
        return True
    else:
        return False


def account_exist(code_list, account_mask):
    account_compile = re.compile(account_mask)
    if (account_compile is None) or (account_mask == ''):
        return True
    for code_item in code_list:
        if account_compile.match(code_item):
            return True
    return False


@signal_and_lock.Signal.decorate('compte_no_found')
def comptenofound_accounting(known_codes, accompt_returned, cost_returned):
    third_unknown = AccountThird.objects.filter(third__status=0).exclude(code__in=known_codes).values_list('code', flat=True)
    model_unknown = ModelLineEntry.objects.exclude(code__in=known_codes).values_list('code', flat=True)
    comptenofound = ""
    if (len(third_unknown) > 0):
        comptenofound = _("thirds") + ":" + ",".join(set(third_unknown)) + " "
    if (len(model_unknown) > 0):
        comptenofound += _("models") + ":" + ",".join(set(model_unknown))
    if comptenofound != "":
        accompt_returned.append("- {[i]}{[u]}%s{[/u]}: %s{[/i]}" % (_('Accounting'), comptenofound))
    model_badcost = ModelEntry.objects.filter(costaccounting__isnull=False, costaccounting__year__isnull=False, costaccounting__year__is_actif=False)
    if (len(model_badcost) > 0):
        cost_returned.append("- {[i]}{[u]}%s{[/u]}: %s{[/i]}" % (_('Model of entry'), ",".join(set([str(model) for model in model_badcost]))))
    if is_with_VAT():
        vat_no_found = []
        if not account_exist(known_codes, current_system_account().get_vat_collected_mask()):
            vat_no_found.append(str(_('collected VAT')))
        if not account_exist(known_codes, current_system_account().get_vat_deductible_mask()):
            vat_no_found.append(str(_('deductible VAT')))
        if not account_exist(known_codes, current_system_account().get_vat_intracommunity_mask()):
            vat_no_found.append(str(_('intracommunity VAT liability')))
        if len(vat_no_found) > 0:
            accompt_returned.append("- {[i]}{[u]}%s{[/u]}: %s{[/i]}" % (_('VAT'), ",".join(vat_no_found)))
    return True


def get_main_third(contact):
    main_third = None
    thirds = Third.objects.filter(contact_id=contact.get_ref_contact().id)
    if len(thirds) > 1:
        main_third = thirds[0]
        alias_third = []
        for third in thirds:
            if third.id != main_third.id:
                alias_third.append(third)

        main_third.merge_objects(alias_third)
    elif len(thirds) == 1:
        main_third = thirds[0]
    return main_third


@signal_and_lock.Signal.decorate('show_contact')
def show_contact_accounting(contact, xfer):
    if WrapAction.is_permission(xfer.request, 'accounting.change_entryaccount'):
        main_third = get_main_third(contact)
        if main_third is not None:
            xfer.new_tab(_("Financial"))
            xfer.item = main_third
            xfer.filltab_from_model(0, 0, True, ["status", 'total'])
            xfer.account_row_offset = 5
            thirdaddon_accounting(main_third, xfer)
            btn = XferCompButton('show_third')
            btn.set_location(1, 50)
            btn.set_action(xfer.request, ActionsManage.get_action_url('accounting.Third', 'Show', xfer),
                           modal=FORMTYPE_MODAL, close=CLOSE_NO, params={"third": str(main_third.id)})
            xfer.add_component(btn)
            xfer.item = contact


@signal_and_lock.Signal.decorate('third_addon')
def thirdaddon_accounting(item, xfer):
    if WrapAction.is_permission(xfer.request, 'accounting.change_entryaccount'):
        try:
            entry_lines_filter = Q(third=item)
            lines_filter = xfer.getparam('lines_filter', 0)
            if lines_filter == 0:
                entry_lines_filter &= Q(entry__year=FiscalYear.get_current())
            elif lines_filter == 1:
                entry_lines_filter &= Q(entry__year=FiscalYear.get_current()) & Q(entry__close=False)
            elif lines_filter == 3:
                entry_lines_filter &= Q(link__isnull=True)
            if not hasattr(xfer, 'account_row_offset'):
                xfer.new_tab(_('Entry of account'))
                account_row_offset = 0
            else:
                account_row_offset = xfer.account_row_offset
            edt = XferCompSelect("lines_filter")
            edt.set_select([(0, _('All entries of current fiscal year')), (1, _('Only no-closed entries of current fiscal year')),
                            (2, _('All entries for all fiscal year')), (3, _('Only entries without link'))])
            edt.set_value(lines_filter)
            edt.set_location(0, account_row_offset + 1)
            edt.description = _('Accounts filter')
            edt.set_action(xfer.request, xfer.return_action(),
                           modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            xfer.add_component(edt)
            entrulines = EntryLineAccount.objects.filter(entry_lines_filter).distinct()
            link_grid_lines = XferCompGrid('entryline')
            link_grid_lines.set_model(entrulines, EntryLineAccount.get_default_fields(), xfer)
            link_grid_lines.set_location(0, account_row_offset + 2, 2)
            link_grid_lines.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'OpenFromLine', xfer),
                                       modal=FORMTYPE_MODAL, unique=SELECT_SINGLE, close=CLOSE_NO)
            link_grid_lines.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'Close', xfer),
                                       modal=FORMTYPE_MODAL, unique=SELECT_MULTI, close=CLOSE_NO)
            link_grid_lines.add_action(xfer.request, ActionsManage.get_action_url('accounting.EntryAccount', 'Link', xfer),
                                       modal=FORMTYPE_MODAL, unique=SELECT_MULTI, close=CLOSE_NO)
            xfer.add_component(link_grid_lines)
        except LucteriosException:
            pass


@signal_and_lock.Signal.decorate('pre_merge')
def pre_merge_accounting(item, alias_objects):
    if isinstance(item, AbstractContact):
        main_third = Third.objects.filter(contact=item).first()
        third_list = list(Third.objects.filter(contact__in=alias_objects).order_by('status', 'id'))
        if (main_third is None) and (len(third_list) > 0):
            main_third = third_list[0]
            third_list = third_list[1:]
        if len(third_list) > 0:
            main_third.merge_objects(third_list)


@signal_and_lock.Signal.decorate('post_merge')
def post_merge_accounting(item):
    if isinstance(item, AbstractContact):
        third_list = Third.objects.filter(contact=item).order_by('status', 'id')
        main_third = third_list.first()
        if main_third is not None:
            main_third.merge_objects(list(third_list)[1:])
