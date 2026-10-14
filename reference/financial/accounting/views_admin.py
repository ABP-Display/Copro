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
from json import dumps

from django.utils.translation import gettext_lazy as _

from lucterios.framework.xferadvance import XferListEditor, XferDelete, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, \
    TITLE_CREATE
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.tools import FORMTYPE_MODAL, ActionsManage, MenuManage, SELECT_SINGLE, CLOSE_NO, SELECT_MULTI,\
    FORMTYPE_REFRESH
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XferContainerCustom
from lucterios.framework.xfercomponents import XferCompButton, XferCompLabelForm, XferCompSelect, XferCompImage, XferCompDownLoad,\
    XferCompEdit, XferCompPassword
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework import signal_and_lock
from lucterios.CORE.parameters import Params
from lucterios.CORE.views import ParamEdit
from lucterios.CORE.models import Parameter

from diacamma.accounting.models import FiscalYear, Journal, AccountThird, ChartsAccount, ModelLineEntry, Third
from diacamma.accounting.system import accounting_system_list, accounting_system_name
from diacamma.accounting.tools import clear_system_account, correct_accounting_code, \
    current_system_account
from diacamma.accounting.einvoicing_flow import DEFAULT_CONFIG, extract_config, get_einvoice_config, get_einvoicing_flow, get_einvoicing_directory
from lucterios.contacts.models import CustomField
from diacamma.accounting.views_accounts import ChartsAccountInitial, \
    ChartsAccountImportFiscalYear

MenuManage.add_sub("financial.conf", "core.extensions", short_icon='mdi:mdi-bank', caption=_("Financial"), pos=2)


def select_account_system(xfer):
    current_account_system = Params.getvalue("accounting-system")
    if current_account_system == '':
        edt = XferCompSelect("account_system")
        account_systems = list(accounting_system_list().items())
        account_systems.insert(0, ('', '---'))
        edt.set_select(account_systems)
        edt.set_action(xfer.request, ConfigurationAccountingSystem.get_action(), modal=FORMTYPE_MODAL, close=CLOSE_NO)
    else:
        edt = XferCompLabelForm("account_system")
    edt.set_value(accounting_system_name(current_account_system))
    edt.set_location(1, xfer.get_max_row() + 1)
    edt.description = _('accounting system')
    xfer.add_component(edt)
    return edt


def fill_params(xfer, is_mini=False):
    xfer.params['params'] = ['accounting-devise-iso', 'accounting-devise-prec']
    if current_system_account().has_minium_code_size():
        xfer.params['params'].append('accounting-sizecode')
    xfer.params['params'].append('accounting-VAT-arrangements')
    xfer.params['params'].append('accounting-needcost')
    xfer.params['params'].append('accounting-code-report-filter')
    xfer.params['params'].append('accounting-datecurrent')
    Params.fill(xfer, xfer.params['params'], 1, xfer.get_max_row() + 1)
    btn = XferCompButton('editparam')
    btn.set_is_mini(is_mini)
    btn.set_location(1, xfer.get_max_row() + 1, 2, 1)
    btn.set_action(xfer.request, ParamEdit.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO)
    xfer.add_component(btn)


def add_year_info(xfer, is_mini=False):
    try:
        row = xfer.get_max_row() + 1
        current_year = FiscalYear.get_current()
        nb_account = len(ChartsAccount.objects.filter(year=current_year))
        lbl = XferCompLabelForm('nb_account')
        if is_mini and (nb_account == 0):
            lbl.set_value(_("No charts of accounts in current fiscal year"))
        else:
            lbl.set_value(_("Total of charts of accounts in current fiscal year: %d") % nb_account)
        lbl.set_location(0, row, 4)
        xfer.add_component(lbl)
        if nb_account == 0:
            lbl.set_color('red')
            xfer.item = ChartsAccount()
            xfer.item.year = current_year
            btn2 = XferCompButton('accountfiscalyear')
            btn2.set_location(0, row + 1)
            btn2.set_action(xfer.request, ActionsManage.get_action_url(ChartsAccount.get_long_name(), 'AccountList', xfer), close=CLOSE_NO)
            xfer.add_component(btn2)
            if not is_mini:
                btn1 = XferCompButton('initialfiscalyear')
                btn1.set_location(1, row + 1, 3)
                btn1.set_action(xfer.request, ActionsManage.get_action_url(ChartsAccount.get_long_name(), 'AccountInitial', xfer), close=CLOSE_NO)
                xfer.add_component(btn1)
    except LucteriosException as lerr:
        lbl = XferCompLabelForm('nb_account')
        lbl.set_value(str(lerr))
        lbl.set_location(0, row, 4)
        xfer.add_component(lbl)


@ActionsManage.affect_other(_("Accounting configuration"), short_icon="mdi:mdi-calendar-star-four-points")
@MenuManage.describ('accounting.change_fiscalyear', FORMTYPE_MODAL, 'financial.conf', _('Management of fiscal year and financial parameters'))
class Configuration(XferListEditor):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = FiscalYear
    field_id = 'fiscalyear'
    caption = _("Accounting configuration")

    def fillresponse_header(self):
        self.params['basic_model'] = 'accounting.Third'
        self.new_tab(_('Fiscal year list'))
        select_account_system(self)

    def get_items_from_filter(self):
        items = XferListEditor.get_items_from_filter(self)
        return items.order_by('-begin', '-end')

    def fill_invoicing(self):
        einvoice_config, einvoice_type_changed = get_einvoice_config(self)
        if einvoice_type_changed:
            einvoice_config.update(extract_config(einvoice_config['einvoice_type']))
        if self.getparam("SAVE", "") == "OK":
            Params.setvalue('accounting-einvoicing-conf', dumps(einvoice_config))

        einvoice_type = XferCompSelect('einvoice_type')
        einvoice_type.set_location(0, 0, 2)
        einvoice_type.set_select([(default_item['id'], default_item['name']) for default_item in DEFAULT_CONFIG])
        einvoice_type.set_value(einvoice_config['einvoice_type'])
        einvoice_type.description = _('einvoice provider')
        einvoice_type.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(einvoice_type)

        if einvoice_config['einvoice_type'] != 0:
            auth_url = XferCompEdit("auth_url")
            auth_url.set_location(0, 1, 2)
            auth_url.set_value(einvoice_config['auth_url'])
            auth_url.mask = r"(?:http[s]?:\/\/.)?(?:www\.)?[-a-zA-Z0-9@%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&\/\/=]*)"
            auth_url.description = _('auth url')
            self.add_component(auth_url)

            directory_url = XferCompEdit("directory_url")
            directory_url.set_location(0, 2)
            directory_url.set_value(einvoice_config['directory_url'])
            directory_url.mask = r"(?:http[s]?:\/\/.)?(?:www\.)?[-a-zA-Z0-9@%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&\/\/=]*)"
            directory_url.description = _('directory url')
            self.add_component(directory_url)
            flow_url = XferCompEdit("flow_url")
            flow_url.set_location(1, 2)
            flow_url.set_value(einvoice_config['flow_url'])
            flow_url.mask = r"(?:http[s]?:\/\/.)?(?:www\.)?[-a-zA-Z0-9@%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&\/\/=]*)"
            flow_url.description = _('flow url')
            self.add_component(flow_url)
            client_id = XferCompEdit("client_id")
            client_id.set_location(0, 3)
            client_id.set_value(einvoice_config['client_id'])
            client_id.description = _('client id')
            self.add_component(client_id)
            secret_id = XferCompPassword("secret_id")
            secret_id.set_location(1, 3)
            secret_id.set_value(einvoice_config['secret_id'])
            secret_id.description = _('secret id')
            self.add_component(secret_id)

            if (einvoice_config['flow_url'] != '') and (einvoice_config['auth_url'] != '') and (einvoice_config['client_id'] != '') and (einvoice_config['secret_id'] != ''):
                btn = XferCompButton('check-einvoice')
                btn.set_is_mini(False)
                btn.set_location(1, 4)
                btn.set_action(self.request, self.return_action(_('Check'), "mdi:mdi-refresh"), close=CLOSE_NO, modal=FORMTYPE_REFRESH, params={'CHECK': 'OK'})
                self.add_component(btn)

            lbl = XferCompLabelForm('resutl-check')
            lbl.set_location(0, 5, 2)
            lbl.set_value("")
            lbl.set_centered()
            if self.getparam("CHECK", "") == "OK":
                try:
                    get_einvoicing_flow(self).healthcheck()
                    get_einvoicing_directory(self).healthcheck()
                    lbl.set_value(_("Connexion successfull"))
                    lbl.set_color('BLUE')
                except Exception as err:
                    lbl.set_value(_("Error of Connexion : %s") % err)
                    lbl.set_color('RED')
            self.add_component(lbl)

        btn = XferCompButton('save-einvoice')
        btn.set_is_mini(False)
        btn.set_location(0, 4)
        btn.set_action(self.request, self.return_action(_('Save'), "mdi:mdi-content-save-outline"), close=CLOSE_NO, modal=FORMTYPE_REFRESH, params={'SAVE': 'OK'})
        self.add_component(btn)

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        add_year_info(self)
        self.get_components('fiscalyear').move_action(FiscalYearActive.get_action().url_text, 0)
        self.new_tab(_('Journals'))
        self.fill_grid(self.get_max_row() + 1, Journal, 'journal', Journal.objects.all())
        self.new_tab(_('Parameters'))
        fill_params(self)
        self.new_tab(_("Third Custom field"))
        self.fill_grid(0, CustomField, "custom_field", CustomField.get_filter(Third))
        grid_custom = self.get_components('custom_field')
        grid_custom.delete_header('model_title')
        self.new_tab(_("e-invoicing"))
        self.fill_invoicing()


@MenuManage.describ('accounting.add_fiscalyear')
class ConfigurationAccountingSystem(XferContainerAcknowledge):
    short_icon = "mdi:mdi-calendar-star-four-points"

    def fillresponse(self, account_system=''):
        if account_system != '':
            if self.confirme(_('Do you confirm to select "%s" like accounting system?{[br/]}{[br/]}{[i]}{[u]}Warning{[/u]}: This choose is definitive.{[/i]}') %
                             accounting_system_name(account_system)):
                Parameter.change_value('accounting-system', account_system)
                Params.clear()
                clear_system_account()
                signal_and_lock.Signal.call_signal("param_change", ('accounting-system'))


@ActionsManage.affect_grid(_("Activate"), short_icon="mdi:mdi-check", unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearActive(XferContainerAcknowledge):
    short_icon = "mdi:mdi-check"
    model = FiscalYear
    field_id = 'fiscalyear'
    caption = _("Activate")

    def fillresponse(self):
        self.item.set_has_actif()


@ActionsManage.affect_grid(_("Export"), short_icon="mdi:mdi-checkbook", unique=SELECT_SINGLE)
@MenuManage.describ('accounting.change_fiscalyear')
class FiscalYearExport(XferContainerCustom):
    short_icon = "mdi:mdi-checkbook"
    model = FiscalYear
    field_id = 'fiscalyear'
    caption = _("Export")
    readonly = True
    methods_allowed = ('GET', )

    def fillresponse(self):
        if self.item.id is None:
            self.item = FiscalYear.get_current()
        destination_file = self.item.get_xml_export()
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(_('Export fiscal year'))
        lbl.set_location(1, 0)
        self.add_component(lbl)
        down = XferCompDownLoad('filename')
        down.compress = False
        down.http_file = True
        down.maxsize = 0
        down.set_value('export_year_%s_%s.xml' %
                       (self.item.begin.isoformat(), self.item.end.isoformat()))
        down.set_download(destination_file)
        down.set_location(1, 1)
        self.add_component(down)


@ActionsManage.affect_grid(_("Check"), short_icon='mdi:mdi-finance', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearCheckReport(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-finance'
    model = FiscalYear
    field_id = 'fiscalyear'
    caption = _("Check saved reports")

    def fillresponse(self):
        if self.confirme(_('Do you want to check saving reports for this year?')):
            self.item.check_report()
            self.message(_('All registration reports will be verified within minutes'))


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus')
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearAddModify(XferAddEditor):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = FiscalYear
    field_id = 'fiscalyear'
    caption_add = _("Add fiscal year")
    caption_modify = _("Modify fiscal year")
    redirect_to_show = 'InitAccount'

    def fillresponse(self):
        if self.item.id is None:
            if Params.getvalue("accounting-system") == '':
                raise LucteriosException(IMPORTANT, _('Account system not defined!'))
            self.item.init_dates()
        XferAddEditor.fillresponse(self)


@ActionsManage.affect_other(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus')
@MenuManage.describ('accounting.add_fiscalyear')
class FiscalYearInitAccount(XferContainerAcknowledge):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = FiscalYear
    field_id = 'fiscalyear'
    caption = _("Add fiscal year")

    def fillresponse(self, init_account=0):
        if init_account == 1:
            self.redirect_action(ChartsAccountInitial.get_action(), params={'year': self.item.id, 'CONFIRME': 'YES'})
        elif init_account == 2:
            self.redirect_action(ChartsAccountImportFiscalYear.get_action(), params={'year': self.item.id, 'CONFIRME': 'YES'})


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.delete_fiscalyear')
class FiscalYearDel(XferDelete):
    short_icon = "mdi:mdi-calendar-star-four-points"
    model = FiscalYear
    field_id = 'fiscalyear'
    caption = _("Delete fiscal year")

    def fillresponse(self):
        self.check_can_delete()
        if self.confirme(_("Do you want delete this fiscal year ?{[br]}Warning: all accounting entries and financial vouchers for this year will also be destroyed.")):
            self.delete_list()
            if (FiscalYear.objects.filter(is_actif=True).count() == 0) and (FiscalYear.objects.all().count() > 0):
                FiscalYear.objects.all().last().set_has_actif()


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline')
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_fiscalyear')
class JournalAddModify(XferAddEditor):
    short_icon = "mdi:mdi-checkbook"
    model = Journal
    field_id = 'journal'
    caption_add = _("Add accounting journal")
    caption_modify = _("Modify accounting journal")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.delete_fiscalyear')
class JournalDel(XferDelete):
    short_icon = "mdi:mdi-checkbook"
    model = Journal
    field_id = 'journal'
    caption = _("Delete accounting journal")


@ActionsManage.affect_grid(_("Default"), short_icon='mdi:mdi-star-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_fiscalyear')
class JournalDefault(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-star-outline'
    model = Journal
    field_id = 'journal'
    caption = _("Default")
    readonly = True

    def fillresponse(self):
        self.item.change_has_default()


@signal_and_lock.Signal.decorate('param_change')
def paramchange_accounting(params):
    if 'accounting-sizecode' in params:
        for account in AccountThird.objects.all():
            if account.code != correct_accounting_code(account.code):
                account.code = correct_accounting_code(account.code)
                account.save()
        for charts_account in ChartsAccount.objects.filter(year__status__in=(FiscalYear.STATUS_BUILDING, FiscalYear.STATUS_RUNNING)).distinct():
            if charts_account.code != correct_accounting_code(charts_account.code):
                charts_account.code = correct_accounting_code(charts_account.code)
                charts_account.save()
        for model_line in ModelLineEntry.objects.all():
            if model_line.code != correct_accounting_code(model_line.code):
                model_line.code = correct_accounting_code(model_line.code)
                model_line.save()


@signal_and_lock.Signal.decorate('conf_wizard')
def conf_wizard_accounting(wizard_ident, xfer):
    if isinstance(wizard_ident, list) and (xfer is None):
        wizard_ident.append(("accounting_params", 9))
        wizard_ident.append(("accounting_fiscalyear", 9))
        wizard_ident.append(("accounting_journal", 23))
    elif (xfer is not None) and (wizard_ident == "accounting_params"):
        xfer.add_title(_("Diacamma accounting"), _('Parameters'), _('Configuration of accounting parameters'))
        select_account_system(xfer)
        fill_params(xfer, True)
    elif (xfer is not None) and (wizard_ident == "accounting_fiscalyear"):
        xfer.add_title(_("Diacamma accounting"), _('Fiscal year list'), _('Configuration of fiscal years'))
        xfer.fill_grid(5, FiscalYear, 'fiscalyear', FiscalYear.objects.all())
        add_year_info(xfer)
    elif (xfer is not None) and (wizard_ident == "accounting_journal"):
        xfer.add_title(_("Diacamma accounting"), _('Journals'), _('Configuration of journals'))
        xfer.fill_grid(5, Journal, 'journal', Journal.objects.all())
