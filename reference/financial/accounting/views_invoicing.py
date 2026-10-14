# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from json import dumps, loads
from time import sleep
from io import BytesIO
from digitalInvoice.reader import ReaderInvoice

from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q

from lucterios.framework.xferadvance import TITLE_MODIFY, TITLE_CANCEL, TITLE_OK, TITLE_CLOSE
from lucterios.framework.tools import FORMTYPE_NOMODAL, SELECT_SINGLE, FORMTYPE_REFRESH, CLOSE_NO, CLOSE_YES, FORMTYPE_MODAL
from lucterios.framework.tools import MenuManage, WrapAction
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm,\
    XferCompStep, XferCompUpLoad, XferCompCheck, XferCompSelect, XferCompButton,\
    XferCompGrid, GRID_SIZE, GRID_PAGE
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XferContainerCustom
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.CORE.parameters import Params
from lucterios.contacts.models import LegalEntity

from diacamma.accounting.models import FiscalYear, ChartsAccount, EntryAccount, Journal, Third, AccountThird, EntryLineAccount, get_meta_currency_iso_list
from diacamma.accounting.views_entries import EntryAccountValidate
from diacamma.accounting.tools import get_amount_from_format_devise, currency_round, current_system_account
from diacamma.accounting.einvoicing_flow import get_einvoicing_flow, get_einvoicing_directory, CdarHandler


def right_importEinvoice(request):
    if EntryAccountValidate.get_action().check_permission(request):
        current_contact = LegalEntity.objects.get(id=1)
        return (current_contact.legal_identification != '') and (current_system_account().get_einvoice_format() != '')
    else:
        return False


@MenuManage.describ(right_importEinvoice, FORMTYPE_NOMODAL, 'financial', _('Manage e-invoicing from platform connecting'))
class EInvoicingManage(XferContainerCustom):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("E-invoicing")

    def fillresponse(self):
        try:
            flow = get_einvoicing_flow()
            flow.healthcheck()
            Signal.call_signal("EInvoicing", self, flow)
        except Exception:
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_infocenter(_('No e-invoicing platform is avalable !'))
            lbl.set_location(0, 0)
            self.add_component(lbl)

            act = XferCompButton('btn')
            act.set_location(0, 1)
            act.set_action(self.request, ImportEInvoice.get_action(_("Manual import")), modal=FORMTYPE_MODAL, close=CLOSE_YES)
            self.add_component(act)
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


def get_contact_from_json(contact_json):
    new_contact = LegalEntity()
    new_contact.name = contact_json['name']
    new_contact.legal_identification = contact_json['legal_ident']
    new_contact.vat_identification = contact_json['vat_ident']
    new_contact.address = '\n'.join(contact_json['address']).strip().replace('\n', '{[br/]}')
    new_contact.postal_code = contact_json['postalcode']
    new_contact.city = contact_json['city']
    new_contact.country_id = contact_json['country_id']
    new_contact.tel1 = contact_json['phone']
    new_contact.email = contact_json['email']
    return new_contact


@MenuManage.describ('contacts.add_abstractcontact')
class EInvoiceAddSeller(XferContainerAcknowledge):
    short_icon = "mdi:mdi-pencil-plus-outline"
    caption = _("add this seller")
    model = LegalEntity
    field_id = 'legal_entity'

    def fillresponse(self, legal_entity=None):
        einvoice_content = loads(self.getparam('einvoice', 'null'))
        if 'seller' in einvoice_content:
            new_contact = get_contact_from_json(einvoice_content['seller'])
            new_contact.id = legal_entity
            for fieldname in ['address', 'postal_code', 'city', 'tel1', 'email']:
                if getattr(new_contact, fieldname).replace('{[br/]}', '\n').strip() == "":
                    setattr(new_contact, fieldname, getattr(self.item, fieldname))
            new_contact.save()


@MenuManage.describ(right_importEinvoice)
class UpdateContactEInvoice(XferContainerAcknowledge):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("E-invoicing upgrade")
    model = LegalEntity
    field_id = 'contactid'

    def fillresponse(self, search_siret=''):
        directory = get_einvoicing_directory()
        data_searching = directory.get_establishment_by_siret(search_siret)
        self.item.name = data_searching['name']
        new_address = "/n".join([data_searching['address'].get('addressLine1', ''), data_searching['address'].get('addressLine2', ''), data_searching['address'].get('addressLine3', '')])
        if new_address.strip() == '':
            self.item.address = new_address.strip().replace('/n', '{[br/]}')
        if data_searching['address']['postalCode'] != '':
            self.item.postal_code = data_searching['address']['postalCode']
        if data_searching['address']['locality'] != '':
            self.item.city = data_searching['address']['locality']
        self.item.country_id = data_searching['address']['countryCode']
        self.item.legal_identification = data_searching['siren']
        self.item.save()


@MenuManage.describ(right_importEinvoice)
class ImportEInvoice(XferContainerCustom):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("Import e-invoice")

    def _select_einvoice(self):
        upld = XferCompUpLoad('importcontent')
        upld.http_file = True
        upld.withcam = False
        upld.set_needed(True)
        upld.add_filter('*.pdf,*.xml')
        upld.set_location(0, 2, 9)
        upld.description = _('e-invoice file')
        self.add_component(upld)

    def _add_contact(self, contact_json, col, label):
        new_contact = get_contact_from_json(contact_json)
        lbl = XferCompLabelForm(f'contact-{col}')
        lbl.set_value_as_title(label)
        lbl.set_location(col, 2, 4)
        self.add_component(lbl)
        self.model = LegalEntity
        self.item = new_contact
        fields = LegalEntity.get_show_fields()
        self.fill_from_model(col, 3, True, desc_fields=list(fields.values())[0], prefix=f'{col}_')
        return new_contact

    def _assign_buyer(self, einvoice_content):
        buyer = self._add_contact(einvoice_content['buyer'], 1, _('buyer'))
        current_contact = LegalEntity.objects.get(id=1)
        if (current_contact.legal_identification != '') and (current_contact.get_legal_identification() == buyer.get_legal_identification()):
            lbl = XferCompLabelForm('buyer_ok')
            lbl.set_value(_('Our structure is well referenced as a buyer'))
            lbl.set_color('blue')
            lbl.set_location(1, 20, 4)
            self.add_component(lbl)
            buyer_valid = True
        else:
            buyer_valid = self.getparam('buyer_valid', False)
            chk = XferCompCheck('buyer_valid')
            chk.set_needed(True)
            chk.set_value(buyer_valid)
            chk.description = ('{[font color="red"]}%s{[/font]}' if not buyer_valid else '%s') % _('Our structure is not defined as a buyer:{[br/]}force this import anyway ?')
            chk.set_location(1, 20, 4)
            chk.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(chk)
        return buyer_valid

    def _assign_seller(self, einvoice_content):
        seller_select = self.getparam('seller_select', 0)
        seller = self._add_contact(einvoice_content['seller'], 5, _('seller'))
        seller_filter = Q(name__icontains=seller.name)
        if seller.legal_identification != '':
            seller_filter |= Q(legal_identification=seller.legal_identification)
        select_list = [(seller_contact.id, f"{seller_contact} (ID={seller_contact.legal_identification})") for seller_contact in LegalEntity.objects.filter(seller_filter)]
        select_list.insert(0, (0, None))
        sel = XferCompSelect("seller_select")
        sel.set_needed(False)
        sel.set_value(seller_select)
        sel.set_select(select_list)
        sel.description = ('{[font color="red"]}%s{[/font]}' if seller_select == 0 else '%s') % _('Select the seller in the contacts')
        sel.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel.set_location(5, 20, 3)
        self.add_component(sel)
        if seller_select != 0:
            btn = XferCompButton('add_seller')
            btn.set_location(8, 20, 1)
            btn.set_is_mini(True)
            btn.set_action(self.request, EInvoiceAddSeller.get_action(caption=_("update this seller"), short_icon="mdi:mdi-pencil-outline"), close=CLOSE_NO, params={'legal_entity': seller_select})
            self.add_component(btn)
        elif f"{seller} (ID={seller.legal_identification})" not in dict(select_list).values():
            btn = XferCompButton('add_seller')
            btn.set_location(8, 20, 1)
            btn.set_is_mini(True)
            btn.set_action(self.request, EInvoiceAddSeller.get_action(caption=_("add this seller"), short_icon="mdi:mdi-pencil-plus-outline"), close=CLOSE_NO)
            self.add_component(btn)
        return seller_select

    def _assign_detail(self, einvoice_content):
        row = self.get_max_row()
        lbl = XferCompLabelForm('detail')
        lbl.set_value_as_title(_('detail'))
        lbl.set_location(0, row + 1, 4)
        self.add_component(lbl)
        row += 2
        sum_total = 0.0
        query = FiscalYear.get_current().chartsaccount_set.filter(type_of_account=ChartsAccount.TYPE_EXPENSE)
        for detail_idx, detail_json in enumerate(einvoice_content['bill']['detail']):
            lbl = XferCompLabelForm(f'detail1_{detail_idx}')
            lbl.set_value("{[b]}%s{[/b]}{[br/]}{[i]}%s{[/i]}" % (detail_json['designation'], detail_json['reference']))
            lbl.set_location(1, row)
            self.add_component(lbl)
            lbl = XferCompLabelForm(f'detail2_{detail_idx}')
            detail_amount = "%s x %.2f" % (get_amount_from_format_devise(detail_json['price'], 7), detail_json['quantity'])
            if abs(detail_json['reduce']) > 1e-3:
                detail_amount += " - %s" % get_amount_from_format_devise(detail_json['reduce'], 7)
            if abs(detail_json['vat_rate']) > 1e-3:
                detail_amount += " (%s  %.2f%%)" % (_('vat'), detail_json['vat_rate'])
            lbl.set_value(detail_amount)
            lbl.set_location(2, row)
            self.add_component(lbl)
            if Params.getvalue("accounting-VAT-arrangements") == FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
                detail_total = currency_round(detail_json['total'] * (1 + detail_json['vat_rate'] / 100))
            else:
                detail_total = detail_json['total']
            sum_total += detail_total
            lbl = XferCompLabelForm(f'detail3_{detail_idx}')
            lbl.set_value(get_amount_from_format_devise(detail_total, 7))
            lbl.set_bold()
            lbl.set_location(3, row)
            self.add_component(lbl)

            sel = XferCompSelect(f'detail_{detail_idx}')
            sel.set_needed(True)
            sel.set_select_query(query)
            sel.set_location(4, row)
            self.add_component(sel)
            row += 1
        return sum_total

    def _assign_vat(self, einvoice_content):
        row = self.get_max_row()
        lbl = XferCompLabelForm('vat')
        lbl.set_value_as_title(_('VAT'))
        lbl.set_location(0, row + 1, 4)
        self.add_component(lbl)
        row += 2
        sum_tva = 0.0
        query = FiscalYear.get_current().chartsaccount_set.filter(code__regex=current_system_account().get_vat_deductible_mask())
        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            for vat_idx, vat_info in enumerate(einvoice_content["bill"]['vat_info']):
                lbl = XferCompLabelForm(f'vat1_{vat_idx}')
                lbl.set_value("%s x %.2f%%" % (get_amount_from_format_devise(vat_info['basic'], 7), vat_info['rate']))
                lbl.set_location(2, row)
                self.add_component(lbl)
                lbl = XferCompLabelForm(f'vat2_{vat_idx}')
                lbl.set_value(get_amount_from_format_devise(vat_info['calculate'], 7))
                lbl.set_bold()
                lbl.set_location(3, row)
                self.add_component(lbl)
                if abs(vat_info['calculate']) > 1e-3:
                    sel = XferCompSelect(f'vat_{vat_idx}')
                    sel.set_needed(True)
                    sel.set_select_query(query)
                    sel.set_location(4, row)
                    self.add_component(sel)
                sum_tva += vat_info['calculate']
                row += 1
        else:
            lbl = XferCompLabelForm('novat')
            lbl.set_value(_('VAT is not recoverable'))
            lbl.set_location(2, row, 4)
            self.add_component(lbl)
        return sum_tva

    def _assign_expences(self, einvoice_content):
        seller = LegalEntity.objects.get(id=self.getparam('seller_select', 0))
        lbl = XferCompLabelForm('seller')
        lbl.description = _('seller')
        lbl.set_value(str(seller))
        lbl.set_location(1, 2, 4)
        self.add_component(lbl)

        self._assign_detail(einvoice_content)
        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            lbl = XferCompLabelForm('total_excltax')
            lbl.description = _('Total excl')
            lbl.set_value(get_amount_from_format_devise(einvoice_content["bill"]['total']['excltax'], 7))
            lbl.set_italic()
            lbl.set_location(3, self.get_max_row() + 1)
            self.add_component(lbl)
        sum_tva = self._assign_vat(einvoice_content)
        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            lbl = XferCompLabelForm('total_vat')
            lbl.description = _('Total VAT')
            lbl.set_value(get_amount_from_format_devise(sum_tva, 7))
            lbl.set_italic()
            lbl.set_location(3, self.get_max_row() + 1)
            self.add_component(lbl)

        row = self.get_max_row()
        lbl = XferCompLabelForm('total')
        lbl.description = _('Total')
        lbl.set_value(get_amount_from_format_devise(einvoice_content["bill"]['total']['incltax'], 7))
        lbl.set_bold()
        lbl.set_location(3, row + 1)
        self.add_component(lbl)

    def _set_entry(self, einvoice_content):
        entry_id = self.getparam("entryaccount", 0)
        self.model = EntryAccount
        if entry_id == 0:
            self.item = EntryAccount.objects.create(year=FiscalYear.get_current(), journal=Journal.objects.get(id=self.getparam('journal', Journal.DEFAULT_BUYING)),
                                                    date_value=timezone.now().date(),
                                                    designation=_('e-invoice import ref. %s') % einvoice_content['bill']['num'])
            self.params["year"] = self.item.year.id
            self.params["entryaccount"] = self.item.id
        else:
            self.item = EntryAccount.objects.get(id=entry_id)

    def _get_third(self):
        third, _new = Third.objects.get_or_create(contact_id=self.getparam('seller_select', 0), status=Third.STATUS_ENABLE)
        accountthirds = third.accountthird_set.filter(code__regex=current_system_account().get_provider_mask())
        if accountthirds.count() == 0:
            charts_sell = FiscalYear.get_current().chartsaccount_set.filter(code__regex=current_system_account().get_provider_mask()).first()
            AccountThird.objects.create(third=third, code=charts_sell.code)
        else:
            charts_sell = FiscalYear.get_current().chartsaccount_set.filter(code__in=[accountthird.code for accountthird in accountthirds]).first()
        return third, charts_sell

    def _fill_serial_entry(self, einvoice_content):
        third, charts_sell = self._get_third()
        serial_entry = self.item.add_new_entryline("", 0, charts_sell.id, einvoice_content["bill"]['total']['incltax'], 0.0, third.id, 0, '')
        sleep(0.05)
        for detail_idx, detail_json in enumerate(einvoice_content['bill']['detail']):
            if Params.getvalue("accounting-VAT-arrangements") == FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
                detail_total = currency_round(detail_json['total'] * (1 + detail_json['vat_rate'] / 100))
            else:
                detail_total = detail_json['total']
            serial_entry = self.item.add_new_entryline(serial_entry, 0, self.getparam(f'detail_{detail_idx}', 0),
                                                       0.0, detail_total, 0, 0, detail_json['designation'])
            sleep(0.05)

        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            for vat_idx, vat_info in enumerate(einvoice_content["bill"]['vat_info']):
                if abs(vat_info['calculate']) > 1e-3:
                    serial_entry = self.item.add_new_entryline(serial_entry, 0, self.getparam(f'vat_{vat_idx}', 0),
                                                               0.0, vat_info['calculate'], 0, 0, "%.2f%%" % vat_info['rate'])
                    sleep(0.05)

        return serial_entry

    def _create_entity(self, einvoice_content):
        self._set_entry(einvoice_content)
        serial_entry = self._fill_serial_entry(einvoice_content)
        self.filltab_from_model(2, 3, False, EntryAccount.get_edit_fields())
        new_grid_lines = XferCompGrid('entrylineaccount_serial')
        new_grid_lines.set_model(self.item.get_entrylineaccounts(serial_entry), EntryLineAccount.get_other_fields(), self)
        new_grid_lines.set_location(2, 10)
        new_grid_lines.add_action_notified(self, EntryLineAccount)
        self.add_component(new_grid_lines)
        return serial_entry

    def _fill_header(self, step):
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(self.caption)
        lbl.set_location(1, 0, 9)
        self.add_component(lbl)
        stepcomp = XferCompStep('step', 4)
        stepcomp.set_value(step)
        stepcomp.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        stepcomp.set_location(2, 1, 7)
        stepcomp.description = _('import progression')
        self.add_component(stepcomp)
        return stepcomp

    def fillresponse(self, step=1, import_flow=None):
        if (import_flow is not None) and (step == 1):
            flow = get_einvoicing_flow()
            reader = ReaderInvoice()
            reader.run(BytesIO(flow.get_flow(import_flow.split('#')[0], doc_type='Original')))
            einvoice_content = reader.data
            self.params['einvoice'] = dumps(einvoice_content, default=str)
            step = 2
        elif 'importcontent' in self.request.FILES:
            reader = ReaderInvoice()
            reader.run(self.request.FILES['importcontent'])
            einvoice_content = reader.data
            self.params['einvoice'] = dumps(einvoice_content, default=str)
        else:
            einvoice_content = loads(self.getparam('einvoice', 'null'))

        if step != 1:
            if einvoice_content is None:
                raise LucteriosException(IMPORTANT, _('No e-invoice file found !'))
            if 'error' in einvoice_content:
                raise LucteriosException(IMPORTANT, einvoice_content['error'])
            if einvoice_content["currency_code"] != Params.getvalue('accounting-devise-iso'):
                currency_iso = dict(get_meta_currency_iso_list())
                raise LucteriosException(IMPORTANT, _('This e-invoice uses the currency "%s" while it is "%s" that is supported !') % (currency_iso[einvoice_content["currency_code"]], currency_iso[Params.getvalue('accounting-devise-iso')]))

        stepcomp = self._fill_header(step)
        if step == 1:
            self._select_einvoice()
        elif step == 2:
            buyer_valid = self._assign_buyer(einvoice_content)
            seller_select = self._assign_seller(einvoice_content)
            stepcomp.set_enabled((buyer_valid is True) and (seller_select != 0))
        elif step == 3:
            self._assign_expences(einvoice_content)
        elif step == 4:
            serial_entry = self._create_entity(einvoice_content)
            _nochange, debit_rest, credit_rest = self.item.serial_control(serial_entry)
            if (debit_rest < 0.0001) and (credit_rest < 0.0001):
                self.add_action(EntryAccountValidate.get_action(TITLE_OK, short_icon='mdi:mdi-check'), params={'serial_entry': serial_entry})
        if import_flow is None:
            self.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            self.add_action(EInvoiceRefuseInvoicing.get_action(_('Refused'), short_icon='mdi:mdi-cancel'),
                            params={
                                "issuer_ident": einvoice_content["seller"]['legal_ident'],
                                "bill_ref": import_flow.split('#')[0],
                                "bill_date": einvoice_content['bill']['date']}
                            )
            self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


# @MenuManage.describ(right_importEinvoice)
class EInvoiceRefuseInvoicing(XferContainerAcknowledge):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("Refuse e-invoice")

    def fillresponse(self, issuer_ident, bill_ref, bill_date):
        current_contact = LegalEntity.objects.get(id=1)
        flow = get_einvoicing_flow()
        flow.submit_cdar(current_contact.get_legal_identification(), issuer_ident, bill_ref, bill_date, CdarHandler.STATUS_REFUSED, "MONTANTTOTAL_ERR")


@Signal.decorate('EInvoicing')
def accounting_EInvoicing(xfer, flow):
    year = FiscalYear.get_current()
    xfer.new_tab(_("Receiving"))
    grid = XferCompGrid('import_flow')
    grid.size_by_page = 500
    size_by_page = xfer.getparam(GRID_SIZE + grid.name, grid.size_by_page)
    page_num = xfer.getparam(GRID_PAGE + grid.name, 0)
    data_to_import = flow.search_flows(flow_direction=['Out', 'In'],
                                       flow_type=['SupplierInvoice'],
                                       updated_after=str(year.begin) + 'T00:00:00Z',
                                       updated_before=str(year.end) + 'T23:59:59Z',
                                       ignore=page_num * size_by_page,
                                       limit=(page_num + 1) * size_by_page)
    grid.nb_lines = len(data_to_import['results'])
    grid.define_page(xfer)
    grid.description = _('Supplier invoices available on the platform')
    grid.add_header('flowId', _('ID'))
    grid.add_header('flowSyntax', _('syntax'))
    grid.add_header('submittedAt', _('submitted at'), 'H')
    grid.add_header('updatedAt', _('updated at'), 'H')
    grid.add_header('acknowledgement', _('acknowledgement'))
    for index, record in enumerate(data_to_import['results']):
        Ident = "%s#%d" % (record['flowId'], index)
        grid.set_value(Ident, 'flowId', record['flowId'])
        grid.set_value(Ident, 'flowSyntax', record['flowSyntax'])
        grid.set_value(Ident, 'submittedAt', record['submittedAt'])
        grid.set_value(Ident, 'updatedAt', record['updatedAt'])
        grid.set_value(Ident, 'acknowledgement', [f"{key}={val}" for key, val in record['acknowledgement'].items()])
    grid.set_location(0, 0)
    grid.add_action(xfer.request, ImportEInvoice.get_action(_('Download e-invoice'), 'mdi:mdi-invoice-import-outline'), close=CLOSE_NO, unique=SELECT_SINGLE)
    xfer.add_component(grid)


@MenuManage.describ(right_importEinvoice)
class SearchContactEInvoice(XferContainerCustom):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("E-invoicing search")
    model = LegalEntity
    field_id = 'contactid'

    def fillresponse(self):
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 4)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(self.caption)
        lbl.set_location(1, 0)
        self.add_component(lbl)
        self.filltab_from_model(1, 1, True, ['name', ('postal_code', 'city'), 'legal_identification'])

        check_name = XferCompCheck('check_name')
        check_name.set_value(self.getparam('check_name', False))
        check_name.set_location(0, 5)
        check_name.description = _('search by name')
        self.add_component(check_name)

        check_location = XferCompCheck('check_location')
        check_location.set_value(self.getparam('check_location', False))
        check_location.set_location(1, 5)
        check_location.description = _('search by location')
        self.add_component(check_location)

        check_identification = XferCompCheck('check_identification')
        check_identification.set_value(self.getparam('check_identification', True))
        check_identification.set_location(2, 5)
        check_identification.description = _('search by identification')
        self.add_component(check_identification)

        act = XferCompButton('btn_einvoicing_contact')
        act.set_location(3, 5)
        act.set_action(self.request, self.return_action(_('Refresh'), short_icon='mdi:mdi-refresh'), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(act)

        grid = XferCompGrid('search_siret')
        size_by_page = self.getparam(GRID_SIZE + grid.name, grid.size_by_page)
        page_num = self.getparam(GRID_PAGE + grid.name, 0)
        grid.add_header("siret", "siret")
        grid.add_header("siren", "siren")
        grid.add_header("name", _("name"))
        grid.add_header("address", _("address"))
        directory = get_einvoicing_directory()
        data_searching = directory.search_company(name=self.item.name if self.getparam('check_name', False) else None,
                                                  postalcode=self.item.postal_code if self.getparam('check_location', False) else None,
                                                  locality=self.item.city if self.getparam('check_location', False) else None,
                                                  siren_siret=self.item.get_legal_identification() if self.getparam('check_identification', True) else None,
                                                  status="A",
                                                  ignore=page_num * size_by_page,
                                                  limit=(page_num + 1) * size_by_page)
        grid.nb_lines = data_searching['totalNumberOfResults'] if 'totalNumberOfResults' in data_searching else 0
        grid.define_page(self)
        for record in data_searching['results']:
            for header, cell in record.items():
                if isinstance(cell, dict):
                    grid.set_value(record['siret'], header, [f"{name}={value}" for name, value in cell.items()])
                else:
                    grid.set_value(record['siret'], header, str(cell))
        grid.set_location(0, 6, 4)
        grid.add_action(self.request, UpdateContactEInvoice.get_action(TITLE_MODIFY, 'mdi:mdi-invoice-import-outline'), close=CLOSE_YES, unique=SELECT_SINGLE)
        self.add_component(grid)


@Signal.decorate('show_contact')
def accounting_einvoicing_contact(contact, xfer):
    if right_importEinvoice(xfer.request):
        contact = contact.get_final_child()
        if isinstance(contact, LegalEntity):
            old_tab = xfer.tab
            xfer.tab = 1
            act = XferCompButton('btn_einvoicing_contact')
            act.set_location(1, xfer.get_max_row() + 1, 2)
            act.set_action(xfer.request, SearchContactEInvoice.get_action(), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'contactid': contact.id})
            xfer.add_component(act)
            xfer.tab = old_tab
