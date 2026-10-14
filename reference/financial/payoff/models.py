# -*- coding: utf-8 -*-
'''
diacamma.payoff models package

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
from datetime import date, datetime
from _io import BytesIO
from logging import getLogger
from json import loads, dumps, JSONDecodeError

from django.db import models
from django.db.models import Q
from django.db.models.aggregates import Sum, Max
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils.module_loading import import_module

from lucterios.framework.models import LucteriosModel, correct_db_field
from lucterios.framework.model_fields import FSMIntegerField, transition
from lucterios.framework.model_fields import get_value_if_choices, LucteriosVirtualField, LucteriosDecimalField
from lucterios.framework.tools import get_date_formating, get_url_from_request
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework.printgenerators import ReportingGenerator
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.xferbasic import NULL_VALUE
from lucterios.framework.filetools import remove_accent
from lucterios.framework.auditlog import auditlog
from lucterios.CORE.models import PrintModel, Parameter, LucteriosUser, Preference
from lucterios.CORE.parameters import Params
from lucterios.contacts.models import LegalEntity, Individual
from lucterios.documents.models import DocumentContainer

from diacamma.accounting.models import EntryAccount, FiscalYear, Third, Journal, ChartsAccount, EntryLineAccount, AccountLink, \
    CostAccounting, is_with_VAT
from diacamma.accounting.tools import currency_round, correct_accounting_code, format_with_devise, \
    get_amount_from_format_devise, current_system_account
from diacamma.payoff.payment_type import PAYMENTTYPE_LIST, PaymentType, PaymentTypeTransfer


class Supporting(LucteriosModel):
    third = models.ForeignKey(Third, verbose_name=_('third'), null=True, default=None, db_index=True, on_delete=models.PROTECT)
    is_revenu = models.BooleanField(verbose_name=_('is revenu'), default=True)
    internal_info = models.TextField(_('internal info'), blank=True, default="{}")

    total_payed = LucteriosVirtualField(verbose_name=_('total payed'), compute_from='get_total_payed', format_string=lambda: format_with_devise(5))
    total_rest_topay = LucteriosVirtualField(verbose_name=_('rest to pay'), compute_from='get_total_rest_topay', format_string=lambda: format_with_devise(5))

    @property
    def reference(self):
        return str(self)

    @classmethod
    def get_payoff_fields(cls):
        return ['payoff_set', ('total_payed', 'total_rest_topay')]

    @classmethod
    def get_print_fields(cls):
        return ['payoff_set', 'total_payed', 'total_rest_topay']

    class Meta(object):
        verbose_name = _('supporting')
        verbose_name_plural = _('supporting')
        default_permissions = []

    def get_total(self):
        raise Exception('no implemented!')

    def get_third_mask(self):
        raise Exception('no implemented!')

    def get_third_masks_by_amount(self, amount):
        return [(self.get_third_mask(), amount)]

    def get_min_payoff(self, ignore_payoff=-1):
        return 0

    def get_max_payoff(self, ignore_payoff=-1):
        return self.get_total_rest_topay(ignore_payoff)

    def payoff_is_revenu(self):
        raise Exception('no implemented!')

    def default_date(self):
        return date.today()

    def entry_links(self):
        return None

    def get_default_costaccounting(self):
        return None

    def get_email(self, only_main=None):
        return self.third.contact.get_email(only_main)

    @property
    def contact(self):
        return self.third.contact

    @property
    def payoff_query(self):
        return Q()

    def get_total_payed(self, ignore_payoff=-1):
        if self.id is None:
            return 0
        val = 0
        for payoff in self.payoff_set.filter(self.payoff_query):
            if payoff.id != ignore_payoff:
                val += currency_round(payoff.amount)
        return val

    def get_warning_state(self):
        warning = []
        return warning

    def get_info_state(self, third_mask=None):
        info = []
        if third_mask is None:
            third_mask = self.get_third_mask()
        if getattr(self, 'status', -1) == 0:
            if self.third is None:
                info.append(str(_("no third selected")))
            else:
                accounts = self.third.accountthird_set.filter(code__regex=third_mask)
                try:
                    if (len(accounts) == 0) or (ChartsAccount.get_account(accounts[0].code, FiscalYear.get_current()) is None):
                        info.append(str(_("third has not correct account")))
                except LucteriosException as err:
                    info.append(str(err))
        return info

    def check_date_current_year(self, date):
        info = []
        fiscal_year = FiscalYear.get_current()
        if (fiscal_year.begin.isoformat() > date) or (fiscal_year.end.isoformat() < date):
            info.append(str(_("date not include in current fiscal year")))
        return info

    def check_date_year_valid(self, date):
        info = []
        fiscal_year = FiscalYear.get_current(date)
        if (fiscal_year is None) or (fiscal_year.status == FiscalYear.STATUS_FINISHED):
            info.append(str(_("date not include in a valid fiscal year")))
        return info

    def get_third_account(self, third_mask, fiscalyear, third=None):
        if third is None:
            third = self.third
        return third.get_account(fiscalyear, third_mask)

    def get_total_rest_topay(self, ignore_payoff=-1):
        if self.id is None:
            return 0
        return self.get_total() - self.get_total_payed(ignore_payoff)

    def get_tax_sum(self):
        return 0.0

    def get_send_email_objects(self):
        return [self]

    def can_add_pay(self):
        return abs(self.get_total_rest_topay()) > 0.001

    def can_send_email(self):
        if self.third.contact.email != '':
            return True
        else:
            cclist = self.get_cclist()
            return isinstance(cclist, list) and (len(self.get_cclist()) > 0)

    def get_cclist(self):
        cclist = []
        contact = self.third.contact.get_final_child()
        if isinstance(contact, LegalEntity):
            for indiv in Individual.objects.filter(responsability__legal_entity=self.third.contact).distinct():
                if indiv.email != '':
                    cclist.append(indiv.email)
        if len(cclist) == 0:
            cclist = None
        return cclist

    def get_bcclist(self):
        return None

    def set_context(self, xfer):
        if (xfer.request.user is not None) and (xfer.request.user.id is not None):
            self.last_user = xfer.request.user

    def get_saved_pdfreport(self, recreate):
        metadata = '%s-%d' % (self.__class__.__name__, self.id)
        doc = DocumentContainer.objects.filter(metadata=metadata).first()
        if recreate and (doc is not None):
            doc.delete()
            doc = None
        if doc is None:
            doc = self.generate_pdfreport()
        return doc

    def get_saved_renew(self):
        return False

    def add_pdf_document(self, title, user, metadata, pdf_content):
        self.fiscal_year.create_folder()
        return self.fiscal_year.folder.add_pdf_document(title, user, metadata, pdf_content) if self.fiscal_year.folder is not None else None

    def generate_pdfreport(self):
        model_id = self.get_default_print_model()
        if model_id is None:
            model_value = PrintModel.objects.filter(kind=PrintModel.KIND_REPORT, modelname=self.get_long_name()).order_by('-is_default', 'id').first()
        else:
            model_value = PrintModel.objects.get(id=model_id)
        if model_value is not None:
            try:
                last_user = getattr(self, 'last_user', None)
                if (last_user is not None) and (last_user.id is not None) and last_user.is_authenticated:
                    user_modifier = LucteriosUser.objects.get(pk=last_user.id)
                else:
                    user_modifier = None
                return self.add_pdf_document(self.get_document_filename(), user_modifier, '%s-%d' % (self.__class__.__name__, self.id),
                                             ReportingGenerator.createpdf_from_model(self.get_send_email_objects(), model_value.value, model_value.mode))
            except Exception:
                getLogger("diacamma.payoff").exception("Failure to create '%s' report" % self.get_document_filename())
        return None

    def renew_generate_pdfreport(self):
        metadata = '%s-%d' % (self.__class__.__name__, self.id)
        doc = DocumentContainer.objects.filter(metadata=metadata).first()
        if doc is not None:
            doc.delete()
        self.generate_pdfreport()

    def get_pdfreport(self, printmodel):
        doc = self.get_saved_pdfreport(False)
        if printmodel == 0:
            if doc is None:
                raise LucteriosException(IMPORTANT, _('saved PDF report not found !'))
            return (doc.name, doc.content)
        else:
            from lucterios.framework.xferprinting import XferContainerPrint
            pdf_name = "%s.pdf" % self.get_document_filename()
            model_value = PrintModel.objects.get(id=printmodel)
            pdf_file = BytesIO(ReportingGenerator.createpdf_from_model(self.get_send_email_objects(), model_value.value, model_value.mode, XferContainerPrint.PRINT_DUPLICATA if doc is not None else ''))
            return (pdf_name, pdf_file)

    def send_email(self, subject, message, model, withcopy=True):
        fct_mailing_mod = import_module('lucterios.mailing.email_functions')
        if fct_mailing_mod.will_mail_send():
            fct_mailing_mod.send_email(self.third.contact.email, subject, message, [self.get_pdfreport(model)],
                                       cclist=self.get_cclist(), bcclist=self.get_bcclist(), withcopy=withcopy)
            self.email_sended()

    def email_sended(self):
        self.set_internal_value("email", datetime.utcnow().isoformat())
        last_user = getattr(self, 'last_user', None)
        if (last_user is not None) and (last_user.id is not None) and last_user.is_authenticated:
            self.set_internal_value("username", last_user.username)

    def get_document_filename(self):
        return remove_accent(self.get_payment_name(), True)

    @classmethod
    def get_payment_fields(cls):
        raise Exception('no implemented!')

    def support_validated(self, validate_date, with_valid=True):
        raise Exception('no implemented!')

    def get_tax(self):
        raise Exception('no implemented!')

    def get_payable_without_tax(self):
        raise Exception('no implemented!')

    def payoff_have_payment(self):
        raise Exception('no implemented!')

    def get_payment_name(self):
        return str(self).strip()

    def get_docname(self):
        return str(self)

    def get_current_date(self):
        raise Exception('no implemented!')

    def delete_accountlink(self):
        entry_links = self.entry_links()
        if entry_links is not None:
            for entry in entry_links:
                for entryline in entry.entrylineaccount_set.all():
                    if entryline.link is not None:
                        entryline.link.delete()

    def generate_accountlink(self):
        def _add_entryline_by_third(entry):
            added = False
            if entry is not None:
                for entryline_third in entry.get_thirds():
                    third_id = (entryline_third.account.code, entryline_third.third_id)
                    if third_id in entryline_by_third.keys():
                        entryline_by_third[third_id].append(entryline_third)
                        added = True
            return added

        nb_link_created = 0
        if (abs(self.get_total_rest_topay()) < 0.0001) and (self.entry_links() is not None) and (len(self.entry_links()) > 0):
            entryline_by_third = {}
            for entry in self.entry_links():
                for entryline_third in entry.get_thirds():
                    third_id = (entryline_third.account.code, entryline_third.third_id)
                    if third_id not in entryline_by_third.keys():
                        entryline_by_third[third_id] = []

            for all_payoff in self.payoff_set.filter(self.payoff_query & Q(entry__isnull=False)):
                for payoff_item in all_payoff.entry.payoff_set.all():
                    supporting_payed = payoff_item.supporting.get_final_child()
                    added = False
                    supporting_entry_links = supporting_payed.entry_links()
                    if supporting_entry_links is not None:
                        for supporting_payed_entry in supporting_entry_links:
                            added = added or _add_entryline_by_third(supporting_payed_entry)
                    if added:
                        for payoff_item in supporting_payed.payoff_set.filter(supporting_payed.payoff_query):
                            _add_entryline_by_third(payoff_item.entry)
            for entrylines in entryline_by_third.values():
                try:
                    AccountLink.create_link(set(entrylines))
                    nb_link_created += 1
                except LucteriosException:
                    pass
        return nb_link_created

    def get_linked_supportings(self):
        return []

    def accounting_of_linked_supportings(self, source_payoff, target_payoff):
        return

    def delete_linked_supporting(self, payoff):
        return

    def get_email_subject(self):
        return Params.getvalue('payoff-email-subject')

    def get_email_message(self):
        message = Params.getvalue('payoff-email-message')
        message = message.replace('%(name)s', '#name')
        message = message.replace('%(doc)s', '#doc')
        return message

    def get_default_print_model(self):
        model = PrintModel.objects.filter(kind=PrintModel.KIND_REPORT, modelname=self.get_long_name()).order_by('-is_default').first()
        if model is None:
            return None
        else:
            return model.id

    def get_payment_method(self):
        return list(PaymentMethod.objects.all())

    def get_email_footer(self, request=None):
        message = ""
        if self.payoff_have_payment() and (len(self.get_payment_method()) > 0):
            message += get_html_payment(get_url_from_request(request), None, self)
        return message

    def adding_payoff(self, payoff):
        return

    def get_internal_value(self, name):
        value = ""
        try:
            value = loads(self.internal_info)[name]
        except (JSONDecodeError, KeyError):
            pass
        return value

    def set_internal_value(self, name, value):
        try:
            internal_json = loads(self.internal_info)
        except JSONDecodeError:
            internal_json = {}
        internal_json[name] = value
        self.internal_info = dumps(internal_json)
        self.save()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.is_revenu = self.get_final_child().payoff_is_revenu()
        if not force_insert:
            self.generate_accountlink()
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class BankAccount(LucteriosModel):
    NO_BANK = 0

    designation = models.TextField(_('designation'), null=False)
    reference = models.CharField(_('reference'), max_length=200, null=False)
    account_code = models.CharField(_('bank account'), max_length=50, null=False)
    order_key = models.IntegerField(verbose_name=_('order key'), null=True, default=None)
    is_disabled = models.BooleanField(verbose_name=_('is disabled'), default=False)

    bank_journal = models.ForeignKey(Journal, verbose_name=_('bank journal'), null=False, default=Journal.DEFAULT_PAYMENT, on_delete=models.PROTECT, related_name='bank_journal')
    temporary_account_code = models.CharField(_('temporary account'), max_length=50, null=False, default='')
    temporary_journal = models.ForeignKey(Journal, verbose_name=_('temporary journal'), null=False, default=Journal.DEFAULT_PAYMENT, on_delete=models.PROTECT, related_name='temporary_journal')

    fee_account_code = models.CharField(_('fee account'), max_length=50, null=False, default='')
    vat_rate = models.DecimalField(_('vat rate'), max_digits=6, decimal_places=2,
                                   default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(99.9)])

    @classmethod
    def get_default_fields(cls):
        return ["order_key", "designation", "reference", "account_code", "temporary_account_code", "fee_account_code"]

    @classmethod
    def get_edit_fields(cls):
        fields = ["designation", "reference", ("account_code", "bank_journal"), ("temporary_account_code", "temporary_journal")]
        if is_with_VAT():
            fields.append(("fee_account_code", "vat_rate"))
        else:
            fields.append("fee_account_code")
        fields.append("is_disabled")
        return fields

    def __str__(self):
        return self.designation

    def up_order(self):
        prec_banks = BankAccount.objects.filter(order_key__lt=self.order_key).order_by('-order_key')
        if len(prec_banks) > 0:
            prec_bank = prec_banks[0]
            order_key = prec_bank.order_key
            prec_bank.order_key = self.order_key
            self.order_key = order_key
            prec_bank.save()
            self.save()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.account_code = correct_accounting_code(self.account_code)
        if self.order_key is None:
            val = BankAccount.objects.all().aggregate(Max('order_key'))
            if val['order_key__max'] is None:
                self.order_key = 1
            else:
                self.order_key = val['order_key__max'] + 1
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('bank code')
        verbose_name_plural = _('bank codes')
        ordering = ['order_key']


class Payoff(LucteriosModel):
    MODE_CASH = 0
    MODE_CHEQUE = 1
    MODE_TRANSFER = 2
    MODE_CREDITCARD = 3
    MODE_OTHER = 4
    MODE_LEVY = 5
    MODE_INTERNAL = 6
    LIST_MODES = ((MODE_CASH, _('cash')), (MODE_CHEQUE, _('cheque')), (MODE_TRANSFER, _('transfer')),
                  (MODE_CREDITCARD, _('credit card')), (MODE_OTHER, _('other')), (MODE_LEVY, _('levy')), (MODE_INTERNAL, _('internal')))

    REPARTITION_BYRATIO = 0
    REPARTITION_BYDATE = 1
    LIST_REPARTITIONS = [(REPARTITION_BYRATIO, _('by ratio')), (REPARTITION_BYDATE, _('by date'))]

    supporting = models.ForeignKey(Supporting, verbose_name=_('supporting'), null=False, db_index=True, on_delete=models.CASCADE)
    date = models.DateField(verbose_name=_('date'), null=False)
    amount = LucteriosDecimalField(verbose_name=_('amount'), max_digits=10, decimal_places=3, default=0.0,
                                   validators=[MinValueValidator(0.0), MaxValueValidator(9999999.999)], format_string=lambda: format_with_devise(5))
    mode = models.IntegerField(verbose_name=_('mode'), choices=LIST_MODES, null=False, default=MODE_CASH, db_index=True)
    payer = models.CharField(_('payer'), max_length=150, null=True, default='')
    reference = models.CharField(_('reference'), max_length=100, null=True, default='')
    entry = models.ForeignKey(EntryAccount, verbose_name=_('entry'), null=True, default=None, db_index=True, on_delete=models.CASCADE)
    bank_account = models.ForeignKey(BankAccount, verbose_name=_('bank account'), null=True, default=None, db_index=True, on_delete=models.PROTECT)
    bank_fee = models.DecimalField(verbose_name=_('bank fee'), max_digits=10, decimal_places=3, default=0.0,
                                   validators=[MinValueValidator(0.0), MaxValueValidator(9999999.999)])
    linked_payoff = models.ForeignKey("payoff.Payoff", verbose_name=_('linked payoff'), null=True, default=None, db_index=True, on_delete=models.CASCADE)

    value = LucteriosVirtualField(verbose_name=_('amount'), compute_from='amount', format_string=lambda: format_with_devise(5))
    bank_account_ex = LucteriosVirtualField(verbose_name=_('bank account'), compute_from='get_bank_account_ex')

    def __str__(self):
        return "%s - %s - %s" % (self.payer, get_date_formating(self.date), self.reference)

    @classmethod
    def get_default_fields(cls):
        return ["date", "amount", "mode", "reference", "payer", "bank_account_ex"]

    @classmethod
    def get_edit_fields(cls):
        return ["amount", "mode", "bank_account", "date", "reference", "payer", "bank_fee"]

    @classmethod
    def get_search_fields(cls):
        search_fields = ["date", "amount", "mode", "reference", "payer", "bank_account"]
        return search_fields

    @property
    def bank_account_query(self):
        return BankAccount.objects.filter(is_disabled=False)

    def get_bank_account_ex(self):
        if (self.bank_account is not None) and (self.bank_account.fee_account_code != ''):
            return _("%(bank)s (fee = %(fee)s)") % {'bank': self.bank_account, 'fee': get_amount_from_format_devise(self.bank_fee, 7)}
        return self.bank_account

    def delete_accounting(self):
        if self.entry is not None:
            if self.mode != self.MODE_INTERNAL:
                payoff_entry = self.entry
                if payoff_entry.close:
                    raise LucteriosException(IMPORTANT, _("an entry associated to this payoff is closed!"))
                self.entry = None
                self.save(do_generate=False)
                payoff_entry.delete()
            else:
                self.supporting.get_final_child().delete_accountlink()

    def generate_accountlink(self):
        supporting = self.supporting.get_final_child()
        if self.entry is not None:
            supporting.generate_accountlink()

    def _create_entry(self, designation=None):
        supporting = self.supporting.get_final_child()
        years = FiscalYear.objects.filter(begin__lte=self.date, end__gte=self.date)
        if len(years) == 1:
            fiscal_year = years[0]
        else:
            fiscal_year = FiscalYear.get_current()
        if designation is None:
            designation = _("payoff for %s") % supporting.reference
        return EntryAccount.objects.create(year=fiscal_year, date_value=self.date, designation=designation, journal=Journal.objects.get(id=Journal.DEFAULT_PAYMENT))

    def _fill_entrylines(self, entry):
        supporting = self.supporting.get_final_child()
        if self.supporting.is_revenu:
            is_revenu = -1
        else:
            is_revenu = 1
        amount_to_bank = 0
        for sub_mask, sub_amount in supporting.get_third_masks_by_amount(float(self.amount)):
            third_account = supporting.third.get_account(entry.year, sub_mask)
            if third_account.type_of_account == ChartsAccount.TYPE_ASSET:
                is_liability = 1
            else:
                is_liability = -1
            EntryLineAccount.objects.create(account=third_account, amount=is_liability * is_revenu * sub_amount, third=supporting.third, entry=entry)
            amount_to_bank += float(sub_amount)
        fee_code = self.bank_account.fee_account_code if self.bank_account is not None else ''
        if (fee_code != '') and (float(self.bank_fee) > 0.001):
            fee_account = ChartsAccount.get_account(fee_code, entry.year)
            if fee_account is not None:
                cost_accounting = CostAccounting.objects.filter(status=CostAccounting.STATUS_OPENED, is_default=True).first()
                if cost_accounting is None:
                    cost_accounting = supporting.get_default_costaccounting()
                EntryLineAccount.objects.create(account=fee_account, amount=-1 * is_revenu * float(self.bank_fee), entry=entry, costaccounting=cost_accounting)
                amount_to_bank -= float(self.bank_fee)
                if (is_with_VAT()) and (self.bank_account.vat_rate > 0.001):
                    vat_account = ChartsAccount.objects.filter(year=entry.year, code__regex=current_system_account().get_vat_collected_mask()).last()
                    if vat_account is None:
                        raise LucteriosException(IMPORTANT, _('collected VAT account not found !'))
                    vat_amount = float(self.bank_fee) * float(self.bank_account.vat_rate) / 100
                    EntryLineAccount.objects.create(account=vat_account, amount=is_revenu * vat_amount, entry=entry, costaccounting=cost_accounting)
                    amount_to_bank -= float(vat_amount)

        return amount_to_bank, is_revenu

    def _get_bankinfo(self, new_entry):
        info = ""
        if self.reference != '':
            info = "%s : %s" % (get_value_if_choices(self.mode, self._meta.get_field('mode')), self.reference)
        if self.bank_account is None:
            bank_code = Params.getvalue("payoff-cash-account")
            bank_journal = None
        elif self.bank_account.temporary_account_code != '':
            bank_code = self.bank_account.temporary_account_code
            bank_journal = self.bank_account.temporary_journal
        else:
            bank_code = self.bank_account.account_code
            bank_journal = self.bank_account.bank_journal
        bank_account = ChartsAccount.get_account(bank_code, new_entry.year)
        if bank_account is None:
            raise LucteriosException(IMPORTANT, _("account is not defined!"))
        if (bank_journal is not None) and (new_entry.journal_id != bank_journal.id) and not new_entry.close:
            new_entry.journal = bank_journal
            new_entry.save()
        return bank_account, info

    def can_delete(self):
        if (self.entry is not None) and self.entry.close and (self.mode != self.MODE_INTERNAL):
            return _("an entry associated to this payoff is closed!")
        return ''

    def generate_accounting(self, designation=None):
        if (self.mode != self.MODE_INTERNAL):
            new_entry = self._create_entry(designation)
            amount_to_bank, is_revenu = self._fill_entrylines(new_entry)
            bank_account, info = self._get_bankinfo(new_entry)
            EntryLineAccount.objects.create(account=bank_account, amount=-1 * is_revenu * amount_to_bank, entry=new_entry, reference=info)
            return new_entry
        else:
            return self.entry

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, do_generate=True, do_linking=True, do_internal=True):
        self.mode = int(self.mode)
        if not force_insert and do_generate:
            self.delete_accounting()
            self.entry = self.generate_accounting()
        res = LucteriosModel.save(self, force_insert, force_update, using, update_fields)
        if do_internal and (self.mode == self.MODE_INTERNAL) and (self.linked_payoff is not None):
            if (self.linked_payoff.linked_payoff is None):
                self.linked_payoff.linked_payoff = self
                self.linked_payoff.save(do_internal=False)
            if (self.linked_payoff.mode == Payoff.MODE_INTERNAL) and (self.linked_payoff.linked_payoff == self):
                self.supporting.get_final_child().accounting_of_linked_supportings(self, self.linked_payoff)
        if not force_insert and do_linking:
            self.generate_accountlink()
        return res

    @classmethod
    def _get_supportings_amountsum(cls, supportings, amount):
        amount_sum = 0
        amount_max = 0
        supporting_list = []
        for supporting in Supporting.objects.filter(id__in=supportings).distinct():
            supporting = supporting.get_final_child()
            amount_sum += supporting.get_final_child().get_total_rest_topay()
            amount_max += supporting.get_final_child().get_max_payoff()
            supporting_list.append(supporting)
        supporting_list.sort(key=lambda item: item.get_current_date())
        if abs(amount_max) < 0.0001:
            raise LucteriosException(IMPORTANT, _('No-valid selection!'))
        if (amount > amount_sum) and (amount_sum < amount_max):
            amount_sum = amount
        return supporting_list, amount_sum

    @classmethod
    def _create_payoff(cls, amount, mode, payer, reference, bank_account, date, bank_fee, repartition, supporting_list, amount_sum):
        amount_rest = float(amount)
        new_paypoff = None
        paypoff_list = []
        for supporting in supporting_list:
            new_paypoff = Payoff(supporting=supporting, date=date, payer=payer, mode=mode, reference=reference, bank_fee=bank_fee)
            bank_fee = 0
            if (bank_account != BankAccount.NO_BANK) and (mode != cls.MODE_CASH):
                new_paypoff.bank_account = BankAccount.objects.get(id=bank_account)
            if repartition == cls.REPARTITION_BYRATIO:
                new_paypoff.amount = currency_round(supporting.get_total_rest_topay() * amount / amount_sum)
            else:
                total_rest_topay = supporting.get_total_rest_topay()
                new_paypoff.amount = min(max(0, total_rest_topay), amount_rest)
            if abs(new_paypoff.amount) > 0.0001:
                amount_rest -= float(new_paypoff.amount)
                new_paypoff.save(do_generate=False)
                paypoff_list.append(new_paypoff)
            else:
                new_paypoff.amount = 0.0
        if (abs(amount_rest) > 0.001) and (new_paypoff is not None):
            new_paypoff.amount += amount_rest
            new_paypoff.save(do_generate=False)
            if new_paypoff not in paypoff_list:
                paypoff_list.append(new_paypoff)
        return paypoff_list

    @classmethod
    def _create_entry_from_multi(cls, paypoff_list, entry=None):
        if entry is None:
            designation_items = []
            for paypoff_item in paypoff_list:
                designation_items.append(str(paypoff_item.supporting.get_final_child().reference))
            designation = _("payoff for %s") % ",".join(designation_items)
            if len(designation) > 190:
                designation = _("payoff for %d multi-pay") % len(designation_items)
            entry = paypoff_list[0]._create_entry(designation)
        else:
            entry.unlink()
            for entryline in entry.entrylineaccount_set.all():
                entryline.delete()
        bank_account, info = paypoff_list[0]._get_bankinfo(entry)
        amount_to_bank = 0.0
        for paypoff_item in paypoff_list:
            amount, is_revenu = paypoff_item._fill_entrylines(entry)
            amount_to_bank += amount
            paypoff_item.entry = entry
            paypoff_item.save(do_generate=False)
        EntryLineAccount.objects.create(account=bank_account, amount=-1 * is_revenu * amount_to_bank, entry=entry, reference=info)
        return entry

    @classmethod
    def _get_subsupporting_from_entry(cls, supporting_list, entry):
        old_is_revenu = None
        new_supporting_list = []
        for supporting in supporting_list:
            for account, _subamount in supporting.get_third_masks_by_amount(0.0):
                third_account = supporting.third.get_account(entry.year, account)
                entryline_filter = Q(account=third_account)
                entryline_filter &= Q(third=supporting.third)
                is_revenu = 1 if not supporting.is_revenu else -1
                if old_is_revenu is None:
                    old_is_revenu = is_revenu
                elif old_is_revenu != is_revenu:
                    raise LucteriosException(IMPORTANT, _('bill type different !'))
                is_liability = 1 if third_account.type_of_account == 0 else -1
                if is_revenu * is_liability > 0:
                    entryline_filter &= Q(amount__gt=0)
                else:
                    entryline_filter &= Q(amount__lt=0)
                if entry.entrylineaccount_set.filter(entryline_filter).count() > 0:
                    new_supporting_list.append(supporting)
                    break
        return new_supporting_list

    @classmethod
    def multi_save(cls, supportings, amount, mode, payer, reference, bank_account, date, bank_fee, repartition, entry=None):
        supporting_list, amount_sum = cls._get_supportings_amountsum(supportings, amount)
        if (entry is not None) and entry.close:
            new_supporting_list = cls._get_subsupporting_from_entry(supporting_list, entry)
            paypoff_list = cls._create_payoff(amount, mode, payer, reference, bank_account, date, bank_fee, repartition, new_supporting_list, amount_sum)
            if len(paypoff_list) > 0:
                for payoff in paypoff_list:
                    payoff.entry = entry
                    payoff.save(do_generate=False)
                return True
            else:
                return False
        else:
            paypoff_list = cls._create_payoff(amount, mode, payer, reference, bank_account, date, bank_fee, repartition, supporting_list, amount_sum)
            cls._create_entry_from_multi(paypoff_list, entry)
            for supporting in supporting_list:
                supporting.generate_accountlink()
            return True

    def delete(self, using=None):
        if self.mode == self.MODE_INTERNAL:
            self.supporting.get_final_child().delete_linked_supporting(self)
        self.delete_accounting()
        LucteriosModel.delete(self, using)

    def get_auditlog_object(self):
        return self.supporting.get_final_child()

    class Meta(object):
        verbose_name = _('payoff')
        verbose_name_plural = _('payoffs')


class DepositSlip(LucteriosModel):
    STATUS_BUILDING = 0
    STATUS_CLOSED = 1
    STATUS_VALID = 2
    LIST_STATUS = ((STATUS_BUILDING, _('building deposit')), (STATUS_CLOSED, _('closed deposit')), (STATUS_VALID, _('valid deposit')))

    status = FSMIntegerField(verbose_name=_('status'), choices=LIST_STATUS, null=False, default=STATUS_BUILDING, db_index=True)
    bank_account = models.ForeignKey(BankAccount, verbose_name=_('bank account'), null=False, db_index=True, on_delete=models.PROTECT)
    date = models.DateField(verbose_name=_('date'), null=False)
    reference = models.CharField(_('reference'), max_length=100, null=False, default='')

    total = LucteriosVirtualField(verbose_name=_('total'), compute_from='get_total', format_string=lambda: format_with_devise(5))
    nb = LucteriosVirtualField(verbose_name=_('number'), compute_from='get_nb', format_string="N0")

    def __str__(self):
        return "%s %s" % (self.reference, get_date_formating(self.date))

    @classmethod
    def get_default_fields(cls):
        return ['status', 'bank_account', 'date', 'reference', 'total']

    @classmethod
    def get_edit_fields(cls):
        return ['bank_account', 'reference', 'date']

    @classmethod
    def get_show_fields(cls):
        return ['bank_account', 'bank_account.reference', ("date", "reference"), ("nb", 'total'), "depositdetail_set"]

    def get_total(self):
        value = 0
        if self.id is not None:
            for detail in self.depositdetail_set.all():
                value += detail.get_amount()
        return value

    def get_nb(self):
        return len(self.depositdetail_set.all()) if self.id is not None else 0

    def can_delete(self):
        if self.status != 0:
            return _('Remove of %s impossible!') % str(self)
        return ''

    transitionname__close_deposit = _("To Close")

    @transition(field=status, source=STATUS_BUILDING, target=STATUS_CLOSED, conditions=[lambda item:len(item.depositdetail_set.all()) > 0])
    def close_deposit(self):
        pass

    transitionname__validate_deposit = _("Validate")

    @transition(field=status, source=STATUS_CLOSED, target=STATUS_VALID)
    def validate_deposit(self):
        if self.bank_account.temporary_account_code != '':
            fiscal_year = FiscalYear.get_current()
            new_entry = EntryAccount.objects.create(year=fiscal_year, date_value=self.date, designation=_("Deposit slip '%s' validate") % self.reference, journal=self.bank_account.bank_journal)
            bank_account = ChartsAccount.get_account(self.bank_account.account_code, fiscal_year)
            temporary_bank_account = ChartsAccount.get_account(self.bank_account.temporary_account_code, fiscal_year)
            if (bank_account is None) or (temporary_bank_account is None):
                raise LucteriosException(IMPORTANT, _("account is not defined!"))
            EntryLineAccount.objects.create(account=bank_account, amount=self.get_total(), entry=new_entry)
            EntryLineAccount.objects.create(account=temporary_bank_account, amount=-1 * self.get_total(), entry=new_entry)

    def add_payoff(self, entries):
        if self.status == self.STATUS_BUILDING:
            for entry in entries:
                payoff_list = Payoff.objects.filter(entry_id=entry)
                if len(payoff_list) > 0:
                    DepositDetail.objects.create(
                        deposit=self, payoff=payoff_list[0])

    def get_payoff_not_deposit(self, payer, reference, order_list, date_begin, date_end):
        payoff_nodeposit = []
        if self.bank_account_id == 0:
            payoff_query = Q(supporting__is_revenu=True) & Q(mode=Payoff.MODE_CHEQUE)
            entity_known = []
        elif self.bank_account_id is not None:
            payoff_query = Q(supporting__is_revenu=True) & Q(bank_account=self.bank_account) & Q(mode=Payoff.MODE_CHEQUE)
            entity_known = DepositDetail.objects.values_list('payoff__entry_id', flat=True).distinct()
        else:
            payoff_query = Q()
            entity_known = []
        entity_unknown = Payoff.objects.filter(payoff_query).exclude(entry_id__in=entity_known).values('entry_id', 'date', 'reference', 'payer', 'supporting__is_revenu').annotate(amount=Sum('amount'))
        if payer != '':
            entity_unknown = entity_unknown.filter(payer__icontains=payer)
        if reference != '':
            entity_unknown = entity_unknown.filter(reference__icontains=reference)
        if date_begin != NULL_VALUE:
            entity_unknown = entity_unknown.filter(date__gte=date_begin)
        if date_end != NULL_VALUE:
            entity_unknown = entity_unknown.filter(date__lte=date_end)
        if order_list is not None:
            entity_unknown = entity_unknown.order_by(*order_list)
        for values in entity_unknown:
            payoff = {}
            payoff['id'] = values['entry_id']
            bills = []
            for supporting in Supporting.objects.filter(payoff__entry=values['entry_id']).distinct():
                bills.append(str(supporting.get_final_child()))
            deposits = []
            if self.bank_account_id == 0:
                for depodetail in DepositDetail.objects.filter(payoff__entry=values['entry_id']).distinct():
                    deposits.append(str(depodetail.deposit))
            payoff['bill'] = '{[br/]}'.join(bills)
            payoff['payer'] = values['payer']
            payoff['amount'] = values['amount']
            payoff['date'] = values['date']
            payoff['reference'] = values['reference']
            payoff['is_revenu'] = values['supporting__is_revenu']
            payoff['deposit'] = deposits
            payoff_nodeposit.append(payoff)
        return payoff_nodeposit

    class Meta(object):
        verbose_name = _('deposit slip')
        verbose_name_plural = _('deposit slips')


class DepositDetail(LucteriosModel):
    deposit = models.ForeignKey(DepositSlip, verbose_name=_('deposit'), null=True, default=None, db_index=True, on_delete=models.CASCADE)
    payoff = models.ForeignKey(Payoff, verbose_name=_('payoff'), null=True, default=None, db_index=True, on_delete=models.CASCADE)

    amount = LucteriosVirtualField(verbose_name=_('amount'), compute_from='get_amount', format_string=lambda: format_with_devise(5))
    supports = LucteriosVirtualField(verbose_name=_('link document'), compute_from='get_supports')

    @classmethod
    def get_default_fields(cls):
        return ['payoff.payer', 'payoff.date', 'payoff.reference', 'amount']

    @classmethod
    def get_edit_fields(cls):
        return []

    @property
    def customer(self):
        return self.payoff.payer

    @property
    def date(self):
        return self.payoff.date

    @property
    def reference(self):
        return self.payoff.reference

    def get_amount(self):
        values = Payoff.objects.filter(entry=self.payoff.entry, reference=self.payoff.reference).aggregate(Sum('amount'))
        if 'amount__sum' in values.keys():
            return values['amount__sum']
        else:
            return 0

    def get_supports(self):
        return [str(payoff.supporting.get_final_child()) for payoff in Payoff.objects.filter(entry=self.payoff.entry, reference=self.payoff.reference)]

    def get_auditlog_object(self):
        return self.deposit

    class Meta(object):
        verbose_name = _('deposit detail')
        verbose_name_plural = _('deposit details')
        default_permissions = []
        ordering = ['payoff__payer']


class PaymentMethod(LucteriosModel):

    paytype = models.IntegerField(verbose_name=_('type'), choices=[(payitem.num, payitem.name) for payitem in PAYMENTTYPE_LIST],
                                  null=False, default=PaymentTypeTransfer.num, db_index=True)
    bank_account = models.ForeignKey(BankAccount, verbose_name=_('bank account'), null=False, default=None, db_index=True, on_delete=models.PROTECT)
    extra_data = models.TextField(_('data'), null=False)

    info = LucteriosVirtualField(verbose_name=_('parameters'), compute_from='get_info')

    def __str__(self):
        return str(self.paymentType.name)

    @property
    def paymentType(self):
        if not hasattr(self, "_paymentType"):
            self.paytype = int(self.paytype)
            self._paymentType = PaymentType(self.extra_data, self.id)
            for payitem in PAYMENTTYPE_LIST:
                if self.paytype == payitem.num:
                    self._paymentType = payitem(self.extra_data, self.id)
        return self._paymentType

    @classmethod
    def get_default_fields(cls):
        return ['paytype', 'bank_account', 'info']

    @classmethod
    def get_edit_fields(cls):
        return ['paytype', 'bank_account']

    @property
    def bank_account_query(self):
        return BankAccount.objects.filter(Q(is_disabled=False))

    def get_extra_fields(self):
        return self.paymentType.get_extra_fields()

    def set_items(self, items):
        self.paymentType.set_items(items)
        self.extra_data = self.paymentType.extra_data

    def get_items(self):
        return self.paymentType.get_items()

    def get_info(self):
        return self.paymentType.get_info()

    @property
    def paytypetext(self):
        return get_value_if_choices(self.paytype, self.get_field_by_name('paytype'))

    def show_pay(self, absolute_uri, lang, supporting):
        return self.paymentType.show_pay(absolute_uri, lang, supporting)

    class Meta(object):
        verbose_name = _('payment method')
        verbose_name_plural = _('payment methods')
        default_permissions = []
        ordering = ['id']


class BankTransaction(LucteriosModel):
    STATUS_FAILURE = 0
    STATUS_SUCCESS = 1
    LIST_STATUS = ((STATUS_FAILURE, _('failure')), (STATUS_SUCCESS, _('success')))

    date = models.DateTimeField(verbose_name=_('date'), null=False)
    status = models.IntegerField(verbose_name=_('status'), choices=LIST_STATUS, null=False, default=STATUS_FAILURE, db_index=True)
    payer = models.CharField(_('payer'), max_length=200, null=False)
    amount = models.DecimalField(verbose_name=_('amount'), max_digits=10, decimal_places=3, default=0.0,
                                 validators=[MinValueValidator(0.0), MaxValueValidator(9999999.999)], null=True)
    contains = models.TextField(_('contains'), null=True)

    @classmethod
    def get_default_fields(cls):
        return ['date', 'status', 'payer', 'amount']

    @classmethod
    def get_show_fields(cls):
        return [('date', 'status'), ('payer', 'amount'), 'contains']

    class Meta(object):
        verbose_name = _('bank transaction')
        verbose_name_plural = _('bank transactions')
        default_permissions = ['change']
        ordering = ['-date']


def check_payoff_accounting():
    for entry in EntryAccount.objects.filter(close=False, journal_id=Journal.DEFAULT_PAYMENT):
        _no_change, debit_rest, credit_rest = entry.serial_control(entry.get_serial())
        payoff_list = entry.payoff_set.all()
        if abs(debit_rest - credit_rest) > 0.0001:
            if len(payoff_list) > 0:
                third_amounts = []
                designation_items = []
                for paypoff_item in payoff_list:
                    third_amounts.append((paypoff_item.supporting.third, float(paypoff_item.amount)))
                    designation_items.append(str(paypoff_item.supporting.get_final_child().reference))
                designation = _("payoff for %s") % ",".join(designation_items)
                if len(designation) > 190:
                    designation = _("payoff for %d multi-pay") % len(designation_items)
                entry.unlink()
                new_entry = Payoff._create_entry_from_multi(payoff_list)
                new_entry.unlink()
                entry.delete()
                try:
                    entrylines = []
                    for paypoff_item in payoff_list:
                        supporting = paypoff_item.supporting.get_final_child()
                        if (abs(supporting.get_total_rest_topay()) < 0.0001) and (supporting.entry_links() is not None) and (len(supporting.payoff_set.filter(supporting.payoff_query)) == 1):
                            entrylines.extend(supporting.entry_links())
                    if len(entrylines) == len(payoff_list):
                        entrylines.append(new_entry)
                        AccountLink.create_link(entrylines)
                except LucteriosException:
                    pass


def check_bank_account():
    for bank in BankAccount.objects.filter(order_key__isnull=True).order_by('id'):
        bank.save()


def remove_bankaccount_param():
    old_param_bankcharges_account = Parameter.objects.filter(name='payoff-bankcharges-account').first()
    if old_param_bankcharges_account is not None:
        if old_param_bankcharges_account.value != '':
            for bank in BankAccount.objects.all():
                bank.fee_account_code = old_param_bankcharges_account.value
                bank.save()
        old_param_bankcharges_account.delete()


def check_accountlink_from_supporting():
    nb_link_created = 0
    for supporting in Supporting.objects.filter(Q(payoff__entry__entrylineaccount__third__isnull=False) & Q(payoff__entry__entrylineaccount__link__isnull=True)).distinct():
        supporting = supporting.get_final_child()
        link_created = supporting.generate_accountlink()
        nb_link_created += link_created
        if link_created > 0:
            getLogger("diacamma.payoff").info(' + Add entry link from %s', supporting)
    return nb_link_created


@Signal.decorate('checkparam')
def payoff_checkparam():
    Parameter.check_and_create(name='payoff-cash-account', typeparam=Parameter.TYPE_STRING, title=_("payoff-cash-account"),
                               args="{'Multi':False}", value='', meta='("accounting","ChartsAccount","import diacamma.accounting.tools;django.db.models.Q(code__regex=diacamma.accounting.tools.current_system_account().get_cash_mask()) & django.db.models.Q(year__is_actif=True)", "code", True)')
    Parameter.check_and_create(name='payoff-email-message', typeparam=Parameter.TYPE_STRING, title=_("payoff-email-message"),
                               args="{'Multi':True, 'HyperText': True}", value=_('#name{[br/]}{[br/]}Joint in this email #doc.{[br/]}{[br/]}Regards'))
    Parameter.check_and_create(name='payoff-email-subject', typeparam=Parameter.TYPE_STRING, title=_("payoff-email-subject"),
                               args="{'Multi':False, 'HyperText': False}", value=_('#reference'))

    Preference.check_and_create(name="payoff-mode", typeparam=Preference.TYPE_INTEGER, title=_("payoff-mode"),
                                args="{'Multi':False}", value=Payoff.MODE_CASH, meta='("","","%s","",False)' % (Payoff.LIST_MODES,))
    Preference.check_and_create(name="payoff-bank_account", typeparam=Preference.TYPE_INTEGER, title=_("payoff-bank_account"),
                                args="{'Multi':False}", value=0, meta='("payoff","BankAccount","django.db.models.Q()", "id", False)')


@Signal.decorate('convertdata')
def payoff_convertdata():
    check_payoff_accounting()
    check_bank_account()
    correct_db_field({'payoff_payoff': 'amount', })
    remove_bankaccount_param()


@Signal.decorate('auditlog_register')
def payoff_auditlog_register():
    auditlog.register(BankAccount, exclude_fields=['ID'])
    auditlog.register(PaymentMethod, include_fields=['paytype', 'bank_account', 'info'])
    auditlog.register(DepositSlip, include_fields=['status', 'bank_account', 'date', 'reference', 'total'])
    auditlog.register(DepositDetail, include_fields=['payoff', 'amount'])
    auditlog.register(Payoff, include_fields=["date", "amount", "mode", "reference", "payer", "bank_account", "bank_fee"])


def get_html_payment(root_uri, lang=None, supporting=None):
    from django.conf import settings
    html_message = "<hr/>"
    html_message += "<center><i><u>%s</u></i></center>" % _("Payement methods")
    html_message += "<table width='90%'>"
    for paymeth in supporting.get_payment_method():
        html_message += "<tr>"
        html_message += "<td><b>%s</b></td>" % paymeth.paytypetext
        html_message += "<td>%s</td>" % paymeth.show_pay(root_uri, settings.LANGUAGE_CODE if lang is None else lang, supporting).replace('{[', '<').replace(']}', '>')
        html_message += "</tr>"
        html_message += "<tr></tr>"
    html_message += "</table>"
    return html_message
