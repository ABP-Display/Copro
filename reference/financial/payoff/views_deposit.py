# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from lucterios.framework.xferadvance import XferListEditor, TITLE_DELETE, TITLE_ADD, TITLE_MODIFY, TITLE_EDIT, TITLE_PRINT, \
    TITLE_CANCEL, XferTransition, TITLE_CREATE, TITLE_CLOSE
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.xferbasic import NULL_VALUE
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompImage, XferCompSelect, XferCompDate, XferCompCheck
from lucterios.framework.xfercomponents import XferCompEdit, XferCompGrid
from lucterios.framework.tools import FORMTYPE_NOMODAL, CLOSE_YES, CLOSE_NO, FORMTYPE_REFRESH, SELECT_MULTI, SELECT_SINGLE
from lucterios.framework.tools import ActionsManage, MenuManage, WrapAction
from lucterios.CORE.xferprint import XferPrintAction

from diacamma.payoff.models import DepositSlip, DepositDetail, BankTransaction, PaymentMethod
from diacamma.accounting.models import FiscalYear
from diacamma.accounting.tools import format_with_devise
from diacamma.payoff.payment_type import PaymentTypePayPal, \
    PaymentTypeMoneticoPaiement, PaymentTypeHelloAsso


@MenuManage.describ('payoff.change_depositslip', FORMTYPE_NOMODAL, 'financial', _('Manage deposit of cheque'))
class DepositSlipList(XferListEditor):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption = _("Deposit slips")

    def fillresponse_header(self):
        status_filter = self.getparam('status_filter', -1)
        year_filter = self.getparam('year_filter', FiscalYear.get_current().id)
        dep_field = DepositSlip.get_field_by_name('status')
        sel_list = list(dep_field.choices)
        sel_list.insert(0, (-1, '---'))
        edt = XferCompSelect("status_filter")
        edt.set_select(sel_list)
        edt.set_value(status_filter)
        edt.set_needed(False)
        edt.set_location(0, 1, 2)
        edt.description = _('Filter by status')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        edt = XferCompSelect("year_filter")
        edt.set_needed(False)
        edt.set_select_query(FiscalYear.objects.all())
        edt.set_value(year_filter)
        edt.set_location(0, 2, 2)
        edt.description = _('Filter by year')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        self.filter = Q()
        if status_filter >= 0:
            self.filter &= Q(status=status_filter)
        if year_filter > 0:
            year = FiscalYear.objects.get(id=year_filter)
            self.filter &= Q(date__gte=year.begin)
            self.filter &= Q(date__lte=year.end)


@ActionsManage.affect_list(_('payoffs'), short_icon="mdi:mdi-checkbook")
@MenuManage.describ('payoff.add_depositslip')
class DepositShowPayoff(XferContainerCustom):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption = _("payoff by cheque")

    def fillresponse_header(self):
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(self.caption)
        lbl.set_location(1, 0)
        self.add_component(lbl)

        year_filter = self.getparam('year_filter', FiscalYear.get_current().id)
        year = FiscalYear.objects.get(id=year_filter)
        self.payer = self.getparam('payer', '')
        self.reference = self.getparam('reference', '')
        self.date_begin = self.getparam('date_begin', str(year.begin))
        self.date_end = self.getparam('date_end', str(year.end))
        self.without_deposit = self.getparam("without_deposit", False)
        if (self.date_begin > str(year.end)) or (self.date_begin < str(year.begin)):
            self.date_begin = str(year.begin)
        if (self.date_end < str(year.begin)) or (self.date_end > str(year.end)):
            self.date_end = str(year.end)

        edt = XferCompSelect("year_filter")
        edt.set_needed(True)
        edt.set_select_query(FiscalYear.objects.all())
        edt.set_value(year_filter)
        edt.set_location(0, 2, 2)
        edt.description = _('Filter by year')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        edt = XferCompEdit('payer')
        edt.set_value(self.payer)
        edt.set_location(0, 3)
        edt.description = _("payer contains")
        edt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)
        edt = XferCompEdit('reference')
        edt.set_value(self.reference)
        edt.set_location(1, 3)
        edt.description = _("reference contains")
        edt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)
        dt = XferCompDate('date_begin')
        dt.set_value(self.date_begin)
        dt.set_location(0, 4)
        dt.set_needed(True)
        dt.description = _("date superior to")
        dt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(dt)
        dt = XferCompDate('date_end')
        dt.set_value(self.date_end)
        dt.set_location(1, 4)
        dt.set_needed(True)
        dt.description = _("date inferior to")
        dt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(dt)
        without_deposit = XferCompCheck('without_deposit')
        without_deposit.set_value(self.without_deposit)
        without_deposit.set_location(0, 5, 2)
        without_deposit.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        without_deposit.description = _('without deposit')
        self.add_component(without_deposit)

    def fillresponse(self):
        self.fillresponse_header()
        grid = XferCompGrid('entry')
        grid.define_page(self)
        self.item.bank_account_id = 0
        payoff_nodeposit = self.item.get_payoff_not_deposit(self.payer, self.reference, grid.order_list, self.date_begin, self.date_end)
        if self.without_deposit is True:
            payoff_nodeposit = [payoffdep for payoffdep in payoff_nodeposit if len(payoffdep['deposit']) == 0]
        grid.nb_lines = len(payoff_nodeposit)
        record_min, record_max = grid.define_page(self)
        grid.add_header('date', _('date'), horderable=1, htype='D')
        grid.add_header('payer', _('payer'), horderable=1)
        grid.add_header('amount', _('amount'), horderable=1, htype=format_with_devise(7))
        grid.add_header('reference', _('reference'), horderable=1)
        grid.add_header('bill', _('link document'))
        grid.add_header('deposit', _('deposit'))
        for payoff in payoff_nodeposit[record_min:record_max]:
            payoffid = payoff['id']
            grid.set_value(payoffid, 'date', payoff['date'])
            grid.set_value(payoffid, 'payer', payoff['payer'])
            grid.set_value(payoffid, 'amount', payoff['amount'])
            grid.set_value(payoffid, 'reference', payoff['reference'])
            grid.set_value(payoffid, 'bill', payoff['bill'])
            grid.set_value(payoffid, 'deposit', payoff['deposit'])
        grid.set_location(0, 6, 2)
        self.add_component(grid)
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus')
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', condition=lambda xfer: xfer.item.status == DepositSlip.STATUS_BUILDING, close=CLOSE_YES)
@MenuManage.describ('payoff.add_depositslip')
class DepositSlipAddModify(XferAddEditor):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption_add = _("Add deposit slip")
    caption_modify = _("Modify deposit slip")


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('payoff.change_depositslip')
class DepositSlipShow(XferShowEditor):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption = _("Show deposit slip")

    def fillresponse(self):
        XferShowEditor.fillresponse(self)
        if self.getparam("PRINTING", False) is True:
            self.remove_component("img")

    def fill_from_model(self, col, row, readonly, desc_fields=None, prefix=''):
        self.fieldnames_depositdetail = DepositDetail.get_default_fields()
        if (self.getparam("show_support", False) is True) and (self.getparam("PRINTING", False) is False):
            self.fieldnames_depositdetail.append('supports')
        XferShowEditor.fill_from_model(self, col, row, readonly, desc_fields, prefix)
        if self.getparam("PRINTING", False) is not True:
            show_support = XferCompCheck('show_support')
            show_support.set_value(self.getparam("show_support", False))
            show_support.set_location(1, self.get_max_row() + 1, 4)
            show_support.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            show_support.description = _('show link document')
            self.add_component(show_support)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('payoff.delete_depositslip')
class DepositSlipDel(XferDelete):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption = _("Delete deposit slip")


@ActionsManage.affect_transition("status")
@MenuManage.describ('payoff.add_depositslip')
class DepositSlipTransition(XferTransition):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'


@ActionsManage.affect_show(TITLE_PRINT, short_icon='mdi:mdi-printer-outline', condition=lambda xfer: (xfer.item.status != 0) or (len(xfer.item.depositdetail_set.all()) > 0))
@MenuManage.describ('payoff.change_depositslip')
class DepositSlipPrint(XferPrintAction):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption = _("Deposit slip")
    action_class = DepositSlipShow

    def get_report_generator(self):
        self.params['PRINTING'] = True
        report_generator = XferPrintAction.get_report_generator(self)
        if self.item.status == DepositSlip.STATUS_BUILDING:
            report_generator.watermark = _('*** NO VALIDATED ***')
        return report_generator


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', condition=lambda xfer, gridname='': xfer.item.status == DepositSlip.STATUS_BUILDING)
@MenuManage.describ('payoff.add_depositslip')
class DepositDetailAddModify(XferContainerCustom):
    short_icon = "mdi:mdi-checkbook"
    model = DepositDetail
    field_id = 'depositdetail'
    caption = _("Add deposit detail")

    def fill_header(self, payer, reference, date_begin, date_end):
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(_("select cheque to deposit"))
        lbl.set_location(1, 0, 3)
        self.add_component(lbl)
        edt = XferCompEdit('payer')
        edt.set_value(payer)
        edt.set_location(1, 1)
        edt.description = _("payer contains")
        edt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)
        edt = XferCompEdit('reference')
        edt.set_value(reference)
        edt.set_location(2, 1)
        edt.description = _("reference contains")
        edt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(edt)
        dt = XferCompDate('date_begin')
        dt.set_value(date_begin)
        dt.set_location(1, 2)
        dt.set_needed(False)
        dt.description = _("date superior to")
        dt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(dt)
        dt = XferCompDate('date_end')
        dt.set_value(date_end)
        dt.set_location(2, 2)
        dt.set_needed(False)
        dt.description = _("date inferior to")
        dt.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(dt)

    def fillresponse(self, depositslip=0, payer="", reference="", date_begin=NULL_VALUE, date_end=NULL_VALUE):
        deposit_item = DepositSlip.objects.get(id=depositslip)
        self.fill_header(payer, reference, date_begin, date_end)

        grid = XferCompGrid('entry')
        grid.define_page(self)
        payoff_nodeposit = deposit_item.get_payoff_not_deposit(payer, reference, grid.order_list, date_begin, date_end)
        grid.nb_lines = len(payoff_nodeposit)
        record_min, record_max = grid.define_page(self)
        grid.add_header('bill', _('link document'))
        grid.add_header('payer', _('payer'), horderable=1)
        grid.add_header('amount', _('amount'), horderable=1, htype=format_with_devise(7))
        grid.add_header('date', _('date'), horderable=1, htype='D')
        grid.add_header('reference', _('reference'), horderable=1)
        for payoff in payoff_nodeposit[record_min:record_max]:
            payoffid = payoff['id']
            grid.set_value(payoffid, 'bill', payoff['bill'])
            grid.set_value(payoffid, 'payer', payoff['payer'])
            grid.set_value(payoffid, 'amount', payoff['amount'])
            grid.set_value(payoffid, 'date', payoff['date'])
            grid.set_value(payoffid, 'reference', payoff['reference'])
        grid.set_location(0, 3, 4)

        grid.add_action(self.request, DepositDetailSave.get_action(_("select"), short_icon='mdi:mdi-check'), close=CLOSE_YES, unique=SELECT_MULTI)
        self.add_component(grid)

        self.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))


@MenuManage.describ('payoff.add_depositslip')
class DepositDetailSave(XferContainerAcknowledge):
    short_icon = "mdi:mdi-checkbook"
    model = DepositSlip
    field_id = 'depositslip'
    caption = _("Save deposit detail")

    def fillresponse(self, entry=()):
        self.item.add_payoff(entry)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.item.status == DepositSlip.STATUS_BUILDING)
@MenuManage.describ('payoff.add_depositslip')
class DepositDetailDel(XferDelete):
    short_icon = "mdi:mdi-checkbook"
    model = DepositDetail
    field_id = 'depositdetail'
    caption = _("Delete deposit detail")


def right_banktransaction(request):
    if BankTransactionShow.get_action().check_permission(request):
        return len(PaymentMethod.objects.filter(paytype__in=(PaymentTypePayPal.num, PaymentTypeMoneticoPaiement.num, PaymentTypeHelloAsso.num))) > 0
    else:
        return False


@MenuManage.describ(right_banktransaction, FORMTYPE_NOMODAL, 'financial', _('show bank transactions'))
class BankTransactionList(XferListEditor):
    short_icon = "mdi:mdi-bank-transfer-in"
    model = BankTransaction
    field_id = 'banktransaction'
    caption = _("Bank transactions")


@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('payoff.change_banktransaction')
class BankTransactionShow(XferShowEditor):
    short_icon = "mdi:mdi-bank-transfer-in"
    model = BankTransaction
    field_id = 'banktransaction'
    caption = _("Show bank transaction")
