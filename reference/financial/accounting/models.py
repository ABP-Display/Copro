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

from datetime import date, timedelta, datetime
from os.path import join, isfile, dirname
from logging import getLogger
from re import match
from csv import DictReader
from _csv import QUOTE_NONE

from django.db import models
from django.db.models.functions import Concat
from django.db.models import Q, F, Value
from django.db.models.query import QuerySet
from django.db.models.aggregates import Sum, Max, Count
from django.template import engines
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_save

from lucterios.framework.models import LucteriosModel
from lucterios.framework.model_fields import FSMIntegerField, transition
from lucterios.framework.model_fields import get_value_if_choices, LucteriosVirtualField, LucteriosScheduler
from lucterios.framework.tools import get_date_formating, convert_date
from lucterios.framework.error import LucteriosException, IMPORTANT, GRAVE
from lucterios.framework.filetools import read_file, xml_validator, save_file, get_user_path
from lucterios.framework.signal_and_lock import RecordLocker, Signal
from lucterios.framework.auditlog import auditlog
from lucterios.framework.printgenerators import ActionGenerator
from lucterios.framework import signal_and_lock
from lucterios.CORE.models import Parameter, LucteriosUser, LucteriosGroup
from lucterios.CORE.parameters import Params
from lucterios.contacts.models import AbstractContact, CustomField, CustomizeObject, LegalEntity, Individual
from lucterios.documents.models import FolderContainer, DocumentContainer

from diacamma.accounting.tools import get_amount_sum, current_system_account, currency_round, correct_accounting_code, get_currency_symbole, format_with_devise, get_amount_from_format_devise


class ThirdCustomField(LucteriosModel):
    third = models.ForeignKey('Third', verbose_name=_('third'), null=False, on_delete=models.CASCADE)
    field = models.ForeignKey(CustomField, verbose_name=_('field'), null=False, on_delete=models.CASCADE)
    value = models.TextField(_('value'), default="")

    data = LucteriosVirtualField(verbose_name=_('value'), compute_from=lambda item: item.field.convert_data(item.value))

    def get_auditlog_object(self):
        return self.third.get_final_child()

    class Meta(object):
        verbose_name = _('custom field value')
        verbose_name_plural = _('custom field values')
        default_permissions = []


class Third(LucteriosModel, CustomizeObject):
    STATUS_ENABLE = 0
    STATUS_DISABLE = 1
    LIST_STATUS = ((STATUS_ENABLE, _('Enable')), (STATUS_DISABLE, _('Disable')))
    CustomFieldClass = ThirdCustomField
    FieldName = 'third'

    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=False, on_delete=models.CASCADE)
    status = FSMIntegerField(verbose_name=_('status'), choices=LIST_STATUS)
    total = LucteriosVirtualField(verbose_name=_('total'), compute_from='get_total', format_string=lambda: format_with_devise(5))

    def __str__(self):
        return str(self.contact.get_final_child(1))

    @classmethod
    def get_field_by_name(cls, fieldname):
        dep_field = CustomizeObject.get_virtualfield(fieldname)
        if dep_field is None:
            dep_field = super(Third, cls).get_field_by_name(fieldname)
        return dep_field

    @classmethod
    def get_default_fields(cls):
        return ["contact", "accountthird_set"]

    @classmethod
    def get_other_fields(cls):
        return ["contact", "accountthird_set", 'total']

    @classmethod
    def get_edit_fields(cls):
        result = []
        return result

    @classmethod
    def get_show_fields(cls):
        fields_desc = ["status", "accountthird_set", 'total']
        fields_desc.extend(cls.get_fields_to_show())
        return {'': ['contact'], _('001@AccountThird information'): fields_desc}

    @classmethod
    def get_print_fields(cls):
        fields_desc = cls.get_other_fields()
        for custom_fields in cls.get_fields_to_show():
            for custom_field in custom_fields:
                fields_desc.append(custom_field)
        return fields_desc

    @classmethod
    def get_search_fields(cls, with_addon=True):
        fieldnames = []
        fieldnames.append(cls.convert_field_for_search('contact', ('name', LegalEntity._meta.get_field('name'), 'legalentity__name', Q())))
        fieldnames.append(cls.convert_field_for_search('contact', ('firstname', Individual._meta.get_field('firstname'), 'individual__firstname', Q())))
        fieldnames.append(cls.convert_field_for_search('contact', ('lastname', Individual._meta.get_field('lastname'), 'individual__lastname', Q())))
        for field_name in AbstractContact.get_search_fields(with_addon=False):
            fieldnames.append(cls.convert_field_for_search('contact', field_name))
        for cf_name, cf_model in CustomField.get_fields(cls):
            fieldnames.append((cf_name, cf_model.get_field(), 'thirdcustomfield__value', Q(thirdcustomfield__field__id=cf_model.id)))
        fieldnames.extend(["status", "accountthird_set.code"])
        if with_addon:
            Signal.call_signal("addon_search", cls, fieldnames)
        return fieldnames

    def get_total(self, current_date=None, strict=True, ignore_close=False):
        current_filter = Q(third=self)
        if current_date is not None:
            if strict:
                current_filter &= Q(entry__date_value__lte=current_date)
            else:
                current_filter &= Q(entry__date_value__lt=current_date)
        if ignore_close:
            current_filter &= ~Q(entry__designation=current_system_account().CLOSE_TITLE_THIRD)
        active_sum = get_amount_sum(EntryLineAccount.objects.filter(current_filter & Q(account__type_of_account=0)).aggregate(Sum('amount')))
        passive_sum = get_amount_sum(EntryLineAccount.objects.filter(current_filter & Q(account__type_of_account=1)).aggregate(Sum('amount')))
        other_sum = get_amount_sum(EntryLineAccount.objects.filter(current_filter & Q(account__type_of_account__gt=1)).aggregate(Sum('amount')))
        return passive_sum - active_sum + other_sum

    @property
    def legal_identification(self):
        final_contact = self.contact.get_final_child()
        if hasattr(final_contact, 'get_legal_identification'):
            return final_contact.get_legal_identification()
        else:
            return ""

    @property
    def vat_identification(self):
        final_contact = self.contact.get_final_child()
        if hasattr(final_contact, 'vat_identification'):
            return final_contact.vat_identification
        else:
            return ""

    def extract_form_identify_number(self, name):
        def build_item(line):
            import re
            line_splied = re.split('[:=]', line)
            return line_splied[0], re.sub('[^0-9_:]+', '', line[len(line_splied[0]) + 1:])
        final_contact = self.contact.get_final_child()
        if hasattr(final_contact, 'identify_number'):
            identify_number_list = dict([build_item(line) for line in final_contact.identify_number.split('\n')])
            return identify_number_list.get(name, '')
        else:
            return ""

    def merge_objects(self, alias_objects=[]):
        LucteriosModel.merge_objects(self, alias_objects=alias_objects)
        last_code = []
        for sub_account in self.accountthird_set.all():
            if sub_account.code in last_code:
                sub_account.delete()
            else:
                last_code.append(sub_account.code)

    transitionname__disabled = _('Disabled')

    @transition(field=status, source=STATUS_ENABLE, target=STATUS_DISABLE)
    def disabled(self):
        pass

    transitionname__enabled = _("Enabled")

    @transition(field=status, source=STATUS_DISABLE, target=STATUS_ENABLE)
    def enabled(self):
        pass

    def get_account(self, fiscal_year, mask):
        accounts = self.accountthird_set.filter(code__regex=mask).order_by('code')
        if len(accounts) == 0:
            raise LucteriosException(IMPORTANT, _("third has not correct account"))
        third_account = None
        for account in accounts:
            third_account = ChartsAccount.get_account(account.code, fiscal_year)
            if third_account is not None:
                break
        if third_account is None:
            raise LucteriosException(IMPORTANT, _("third has not correct account"))
        return third_account

    def from_einvoice(self):
        return {
            'name': str(self.contact),
            'legal_ident': self.legal_identification,
            'vat_ident': self.vat_identification,
            'postalcode': self.contact.postal_code,
            'address': self.contact.address_list,
            'city': self.contact.city,
            'country_id': self.contact.country_id,
            'electronic_address': self.extract_form_identify_number('e-address'),
            'email': self.contact.email,
            'phone': self.contact.tel1,
        }

    class Meta(object):
        verbose_name = _('third')
        verbose_name_plural = _('thirds')


class AccountThird(LucteriosModel):
    third = models.ForeignKey(Third, verbose_name=_('third'), null=False, on_delete=models.CASCADE)
    code = models.CharField(_('code'), max_length=50)

    total_txt = LucteriosVirtualField(verbose_name=_('total'), compute_from='get_total_txt', format_string=lambda: format_with_devise(2))

    def get_auditlog_object(self):
        return self.third.get_final_child()

    def __str__(self):
        return self.code

    def can_delete(self):
        if self.total > 0.0001:
            return _('This account is not nul!')
        else:
            return ''

    @classmethod
    def get_default_fields(cls):
        return ["code", 'total_txt']

    @classmethod
    def get_edit_fields(cls):
        return ["code"]

    @property
    def current_charts(self):
        try:
            return ChartsAccount.objects.get(code=self.code, year=FiscalYear.get_current())
        except (ObjectDoesNotExist, LucteriosException):
            return None

    def get_total_txt(self):
        chart = self.current_charts
        if chart is not None:
            return chart.credit_debit_way() * self.total
        else:
            return 0

    @property
    def total(self):
        return get_amount_sum(EntryLineAccount.objects.filter(third=self.third, account__code=self.code).aggregate(Sum('amount')))

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.code = correct_accounting_code(self.code)
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('account')
        verbose_name_plural = _('accounts')
        default_permissions = []


def get_total_result_text_format():
    value = {}
    value['revenue'] = '{0}'
    value['expense'] = '{1}'
    value['result'] = '{2}'
    value['cash'] = '{3}'
    value['closed'] = '{4}'
    res_text = _('{[b]}Revenue:{[/b]} %(revenue)s - {[b]}Expense:{[/b]} %(expense)s = {[b]}Result:{[/b]} %(result)s{[br/]}{[b]}Cash:{[/b]} %(cash)s - {[b]}Closed:{[/b]} %(closed)s')
    return format_with_devise(7) + ";" + res_text % value


class FiscalYear(LucteriosModel):
    VAT_ARRANGEMENTS_NOT_APPLICABLE = 0
    VAT_ARRANGEMENTS_SIMPLE = 1

    STATUS_BUILDING = 0
    STATUS_RUNNING = 1
    STATUS_FINISHED = 2
    LIST_STATUS = ((STATUS_BUILDING, _('building year')), (STATUS_RUNNING, _('running year')), (STATUS_FINISHED, _('finished year')))

    begin = models.DateField(verbose_name=_('begin'))
    end = models.DateField(verbose_name=_('end'))
    status = models.IntegerField(verbose_name=_('status'), choices=LIST_STATUS, default=STATUS_BUILDING)
    is_actif = models.BooleanField(verbose_name=_('actif'), default=False, db_index=True)
    last_fiscalyear = models.ForeignKey('FiscalYear', verbose_name=_('last fiscal year'), related_name='next_fiscalyear', null=True, on_delete=models.SET_NULL)

    folder = models.ForeignKey(FolderContainer, verbose_name=_('folder'), null=True, on_delete=models.PROTECT)
    prefix = models.CharField(verbose_name=_('prefix'), default='', null=False, max_length=10)

    total_result_text = LucteriosVirtualField(verbose_name='', compute_from='get_total_result_text', format_string=lambda: get_total_result_text_format())

    def init_dates(self):
        fiscal_years = FiscalYear.objects.order_by('end')
        if len(fiscal_years) == 0:
            self.begin = date.today()
        else:
            last_fiscal_year = fiscal_years[len(fiscal_years) - 1]
            self.begin = last_fiscal_year.end + timedelta(days=1)
        try:
            self.end = date(self.begin.year + 1, self.begin.month, self.begin.day) - timedelta(days=1)
        except ValueError:
            self.end = date(self.begin.year + 1, self.begin.month, self.begin.day - 1)

    def can_delete(self):
        fiscal_years = FiscalYear.objects.order_by('end')
        if (len(fiscal_years) != 0) and (fiscal_years.last().id != self.id):
            return _('This fiscal year is not the last!')
        else:
            return ''

    def delete(self, using=None):
        signal_and_lock.Signal.call_signal("delete_fiscalyear", self)
        for entry in self.entryaccount_set.all():
            entry.delete()
        LucteriosModel.delete(self, using=using)
        self.folder.delete()

    def create_folder(self):
        if self.folder is None:
            parent = None
            if (self.last_fiscalyear is not None) and (self.last_fiscalyear.folder is not None):
                parent = self.last_fiscalyear.folder.parent
            name = _("Accounting from %(begin)s to %(end)s") % {'begin': get_date_formating(self.begin), 'end': get_date_formating(self.end)}
            self.folder = FolderContainer.objects.create(name=name, description=name, parent=parent)
            return True
        else:
            return False

    def set_has_actif(self):
        EntryAccount.clear_ghost()
        all_year = FiscalYear.objects.all()
        for year_item in all_year:
            year_item.is_actif = False
            year_item.save()
        self.is_actif = True
        self.save()
        Signal.call_signal("fiscalyear_change")

    @classmethod
    def get_default_fields(cls):
        return ['begin', 'end', 'status', 'prefix', 'is_actif']

    @classmethod
    def get_edit_fields(cls):
        return ['status', 'begin', 'end', 'prefix', 'folder']

    def get_result_entries(self):
        if not hasattr(self, "_result_entries"):
            self._result_entries = [entry for entry in self.entryaccount_set.filter(journal_id=5, entrylineaccount__account__code__in=current_system_account().result_accounting_codes)]
        return self._result_entries

    def get_total_income(self, type_of_account):
        entrylines = EntryLineAccount.objects.filter(account__type_of_account=type_of_account, account__year=self,
                                                     entry__date_value__gte=self.begin, entry__date_value__lte=self.end)
        entrylines = entrylines.exclude(entry__in=self.get_result_entries())
        return get_amount_sum(entrylines.aggregate(Sum('amount')))

    @property
    def total_revenue(self):
        return self.get_total_income(ChartsAccount.TYPE_REVENUE)

    @property
    def total_expense(self):
        return self.get_total_income(ChartsAccount.TYPE_EXPENSE)

    @property
    def total_cash(self):
        return get_amount_sum(EntryLineAccount.objects.filter(account__code__regex=current_system_account().get_cash_mask(),
                                                              account__year=self, entry__date_value__gte=self.begin, entry__date_value__lte=self.end).aggregate(Sum('amount')))

    @property
    def total_cash_close(self):
        return get_amount_sum(EntryLineAccount.objects.filter(entry__close=True, account__code__regex=current_system_account().get_cash_mask(),
                                                              account__year=self, entry__date_value__gte=self.begin, entry__date_value__lte=self.end).aggregate(Sum('amount')))

    def get_total_result_text(self):
        value = []
        value.append(self.total_revenue)
        value.append(self.total_expense)
        value.append(self.total_revenue - self.total_expense)
        value.append(self.total_cash)
        value.append(self.total_cash_close)
        return value

    @property
    def has_no_lastyear_entry(self):
        val = get_amount_sum(EntryLineAccount.objects.filter(entry__journal__id=Journal.DEFAULT_LASTYEAR, account__year=self).aggregate(Sum('amount')))
        return abs(val) < 0.0001

    def import_charts_accounts(self):
        if self.last_fiscalyear is None:
            raise LucteriosException(
                IMPORTANT, _("This fiscal year has not a last fiscal year!"))
        if self.status == FiscalYear.STATUS_FINISHED:
            raise LucteriosException(IMPORTANT, _('Fiscal year finished!'))
        for last_charts_account in self.last_fiscalyear.chartsaccount_set.all():
            self.getorcreate_chartaccount(last_charts_account.code, last_charts_account.name, last_charts_account.rubric)

    def run_report_lastyear(self, import_result):
        if self.last_fiscalyear is None:
            raise LucteriosException(IMPORTANT, _("This fiscal year has not a last fiscal year!"))
        if self.status != 0:
            raise LucteriosException(IMPORTANT, _("This fiscal year is not 'in building'!"))
        return current_system_account().import_lastyear(self, import_result)

    def getorcreate_chartaccount(self, code, name=None, rubric=""):
        code = correct_accounting_code(code)
        try:
            return self.chartsaccount_set.get(code=code)
        except ObjectDoesNotExist:
            descript, typeaccount = current_system_account().new_charts_account(code)
            if name is None:
                name = descript
            return ChartsAccount.objects.create(year=self, code=code, name=name, rubric=rubric, type_of_account=typeaccount)

    def move_entry_noclose(self):
        if self.status == FiscalYear.STATUS_RUNNING:
            next_ficalyear = None
            for entry_noclose in EntryAccount.objects.filter(close=False, entrylineaccount__account__year=self).distinct():
                if next_ficalyear is None:
                    try:
                        next_ficalyear = FiscalYear.objects.get(last_fiscalyear=self)
                    except BaseException:
                        raise LucteriosException(IMPORTANT, _("This fiscal year has entries not closed and not next fiscal year!"))
                for entryline in entry_noclose.entrylineaccount_set.all():
                    entryline.account = next_ficalyear.getorcreate_chartaccount(entryline.account.code, entryline.account.name, entryline.account.rubric)
                    entryline.save()
                entry_noclose.year = next_ficalyear
                entry_noclose.date_value = next_ficalyear.begin
                entry_noclose.save()

    def unlink_entry_multiyear(self):
        entrylines = EntryLineAccount.objects.filter(entry__year=self, link__isnull=False, multilink__isnull=False)
        for entryline in entrylines:
            entryline.unlink()

    @classmethod
    def get_current(cls, select_year=None):
        if select_year is None:
            try:
                year = FiscalYear.objects.get(is_actif=True)
            except ObjectDoesNotExist:
                raise LucteriosException(IMPORTANT, _('No fiscal year define!'))
        elif isinstance(select_year, date):
            year = FiscalYear.objects.filter(begin__lte=select_year, end__gte=select_year).first()
        else:
            year = FiscalYear.objects.get(id=select_year)
        return year

    def get_account_list(self, num_cpt_txt, num_cpt):
        account_list = []
        first_account = None
        current_account = None
        for account in self.chartsaccount_set.all().filter(code__startswith=num_cpt_txt).order_by('code'):
            account_list.append((account.id, str(account)))
            if first_account is None:
                first_account = account
            if account.id == num_cpt:
                current_account = account
        if current_account is None:
            current_account = first_account

        return account_list, current_account

    def get_rubric_list(self, type_of_account=None):
        account_filter = Q()
        if isinstance(type_of_account, tuple):
            account_filter = Q(type_of_account__in=type_of_account)
        rubric_list = [account.rubric for account in self.chartsaccount_set.filter(account_filter) if account.rubric != ""]
        rubric_list = list(set(rubric_list))
        rubric_list.sort()
        return rubric_list

    def get_context(self):
        entries_by_journal = []
        for journal in Journal.objects.all():
            entries = self.entryaccount_set.filter(journal=journal, close=True).exclude(entrylineaccount__isnull=True)
            if len(entries) > 0:
                entries_by_journal.append((journal, entries))
        if len(entries_by_journal) == 0:
            raise LucteriosException(IMPORTANT, _('This fiscal year has no validated entrie !'))
        return {'year': self, 'entries_by_journal': entries_by_journal}

    def get_xml_export(self):
        file_name = "fiscalyear_export_%s.xml" % str(self.id)
        xmlfiles = current_system_account().get_export_xmlfiles()
        if xmlfiles is None:
            raise LucteriosException(IMPORTANT, _('No export for this accounting system!'))
        xml_file, xsd_file = xmlfiles
        template = engines['django'].from_string(read_file(xml_file).decode('utf-8'))
        context_data = self.get_context()
        fiscal_year_xml = str(template.render(context_data))
        res_val = xml_validator(fiscal_year_xml, xsd_file)
        if res_val is not None:
            getLogger("diacamma.accounting").exception("Failure to export: '%s' / '%s'" % (context_data, res_val))
            raise LucteriosException(IMPORTANT, _("Failure to export this fiscal year !"))
        save_file(get_user_path("accounting", file_name), fiscal_year_xml)
        return join("accounting", file_name)

    def get_identify(self):
        if self.begin.year != self.end.year:
            return "%d/%d" % (self.begin.year, self.end.year)
        else:
            return str(self.begin.year)

    def __str__(self):
        status = get_value_if_choices(self.status, self._meta.get_field('status'))
        return _("Fiscal year from %(begin)s to %(end)s [%(status)s]") % {'begin': get_date_formating(self.begin), 'end': get_date_formating(self.end), 'status': status}

    @property
    def toText(self):
        return _("Fiscal year from %(begin)s to %(end)s") % {'begin': get_date_formating(self.begin), 'end': get_date_formating(self.end)}

    def set_context(self, xfer):
        setattr(self, 'last_user', xfer.request.user)

    def get_letter(self):
        if self.id is None:
            nb_year = FiscalYear.objects.count()
        else:
            nb_year = FiscalYear.objects.filter(id__lt=self.id).count()
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        res = ''
        while nb_year >= 26:
            div, mod = divmod(nb_year, 26)
            res = letters[mod] + res
            nb_year = int(div) - 1
        return letters[nb_year] + res

    def _check_annexe(self):
        total = 0
        for chart in self.chartsaccount_set.filter(type_of_account=5):
            total += chart.get_current_total(with_correction=False)
        if abs(total) > 0.0001:
            raise LucteriosException(IMPORTANT, _("The sum of annexe account must be null!"))

    def check_to_close(self):
        if self.status == FiscalYear.STATUS_BUILDING:
            raise LucteriosException(IMPORTANT, _("This fiscal year is not 'in running'!"))
        EntryAccount.clear_ghost()
        self._check_annexe()
        nb_entry_noclose = EntryAccount.objects.filter(close=False, entrylineaccount__account__year=self).distinct().count()
        if (nb_entry_noclose > 0) and (FiscalYear.objects.filter(last_fiscalyear=self).count() == 0):
            raise LucteriosException(IMPORTANT, _("This fiscal year has entries not closed and not next fiscal year!"))
        return nb_entry_noclose

    def get_reports(self, printclass, params={}, recreate=False):
        if self.status == FiscalYear.STATUS_FINISHED:
            metadata = '%s-%d' % (printclass.url_text, self.id)
            doc = DocumentContainer.objects.filter(metadata=metadata).first()
            if recreate and (doc is not None):
                doc.delete()
                doc = None
            if doc is None:
                try:
                    last_user = getattr(self, 'last_user', None)
                    if (last_user is not None) and (last_user.id is not None) and last_user.is_authenticated:
                        user_modifier = LucteriosUser.objects.get(pk=last_user.id)
                    else:
                        user_modifier = None
                    own_struct = LegalEntity.objects.get(id=1)
                    params['year'] = self.id
                    doc = self.folder.add_pdf_document(printclass.caption, user_modifier, '%s-%d' % (printclass.url_text, self.id),
                                                       ActionGenerator.createpdf_from_action(printclass, params,
                                                                                             "{[u]}{[b]}%s{[/b]}{[/u]}{[br/]}{[i]}%s{[/i]}" % (own_struct, printclass.caption), 297, 210))
                except Exception:
                    getLogger("diacamma.accounting").exception("Failure to create '%s' report" % printclass.caption)
            return doc
        else:
            return None

    @classmethod
    def save_reports(cls, year, last_user):
        '''Save report'''
        from diacamma.accounting.views_reports import FiscalYearBalanceSheet, FiscalYearIncomeStatement, FiscalYearLedger, FiscalYearTrialBalance
        year.last_user = last_user
        year.get_reports(FiscalYearBalanceSheet)
        year.get_reports(FiscalYearIncomeStatement)
        year.get_reports(FiscalYearTrialBalance, {'filtercode': ''})
        year.get_reports(FiscalYearLedger, {'filtercode': ''})

    def closed(self):
        for cost in CostAccounting.objects.filter(year=self):
            cost.close()
        if self.next_fiscalyear.first() is not None:
            CostAccounting.create_costs_from_lastyear(self.next_fiscalyear.first().id)
        self._check_annexe()
        self.move_entry_noclose()
        self.unlink_entry_multiyear()
        current_system_account().finalize_year(self)
        self.status = FiscalYear.STATUS_FINISHED
        self.save()
        LucteriosScheduler.add_date(FiscalYear.save_reports, datetime=datetime.now() + timedelta(seconds=10), year=self, last_user=getattr(self, 'last_user', None))

    def check_report(self):
        LucteriosScheduler.add_date(FiscalYear.check_report_backend, datetime=datetime.now() + timedelta(seconds=10), year=self)

    @classmethod
    def check_report_backend(cls, year):
        '''Check report'''
        if year.folder is None:
            year.save()
        signal_and_lock.Signal.call_signal("check_report", year)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.create_folder()
        if self.prefix.strip() == '':
            self.prefix = self.get_letter()
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('fiscal year')
        verbose_name_plural = _('fiscal years')
        ordering = ['begin', 'end']


class CostAccounting(LucteriosModel):
    STATUS_OPENED = 0
    STATUS_CLOSED = 1
    LIST_STATUS = ((STATUS_OPENED, _('opened')), (STATUS_CLOSED, _('closed')))

    name = models.CharField(_('name'), max_length=150, unique=True)
    description = models.CharField(_('description'), max_length=200)
    status = models.IntegerField(verbose_name=_('status'), choices=LIST_STATUS, default=STATUS_OPENED)
    last_costaccounting = models.ForeignKey('CostAccounting', verbose_name=_('last cost accounting'),
                                            related_name='next_costaccounting', null=True, on_delete=models.SET_NULL)
    is_default = models.BooleanField(verbose_name=_('default'), default=False)
    is_protected = models.BooleanField(verbose_name=_('default'), default=False)
    year = models.ForeignKey('FiscalYear', verbose_name=_('fiscal year'), null=True, default=None, on_delete=models.CASCADE, db_index=True)

    total_revenue = LucteriosVirtualField(verbose_name=_('total revenue'), compute_from='get_total_revenue', format_string=lambda: format_with_devise(5))
    total_expense = LucteriosVirtualField(verbose_name=_('total expense'), compute_from='get_total_expense', format_string=lambda: format_with_devise(5))
    total_result = LucteriosVirtualField(verbose_name=_('result'), compute_from='get_total_result', format_string=lambda: format_with_devise(5))

    def __str__(self):
        return self.name

    def can_delete(self):
        if self.status == self.STATUS_CLOSED:
            return _('This cost accounting is closed!')
        if self.is_protected:
            return _("This cost accounting is protected by other modules!")
        return ""

    @classmethod
    def get_default_fields(cls):
        return ['name', 'description', 'year', 'total_revenue', 'total_expense', 'total_result', 'status', 'is_default']

    @classmethod
    def get_edit_fields(cls):
        return ['name', 'description', 'year', 'last_costaccounting']

    def get_total_revenue(self):
        return get_amount_sum(EntryLineAccount.objects.filter(account__type_of_account=ChartsAccount.TYPE_REVENUE, costaccounting=self).aggregate(Sum('amount')))

    def get_total_expense(self):
        return get_amount_sum(EntryLineAccount.objects.filter(account__type_of_account=ChartsAccount.TYPE_EXPENSE, costaccounting=self).aggregate(Sum('amount')))

    def get_total_result(self):
        return self.get_total_revenue() - self.get_total_expense()

    def close(self):
        self.check_before_close()
        self.is_default = False
        self.status = self.STATUS_CLOSED
        self.save()

    def change_has_default(self):
        if self.status == self.STATUS_OPENED:
            if self.is_default:
                self.is_default = False
                self.save()
            else:
                for cost_item in CostAccounting.objects.filter(is_default=True):
                    cost_item.is_default = False
                    cost_item.save()
                self.is_default = True
                self.save()

    def check_before_close(self):
        EntryAccount.clear_ghost()
        if self.entrylineaccount_set.filter(entry__close=False).count() > 0:
            raise LucteriosException(IMPORTANT, _('The cost accounting "%s" has some not validated entry!') % self)
        if self.modelentry_set.all().count() > 0:
            raise LucteriosException(IMPORTANT, _('The cost accounting "%s" is include in a model of entry!') % self)

    @classmethod
    def create_costs_from_lastyear(cls, currentyear_id):
        current_year = FiscalYear.objects.get(id=currentyear_id)
        last_year = current_year.last_fiscalyear
        cost_list = CostAccounting.objects.filter(year=last_year, year__next_fiscalyear__status=FiscalYear.STATUS_BUILDING, is_protected=False, next_costaccounting__isnull=True)
        lastconvert_dict = {"begin": str(last_year.begin.year),
                            "end": str(last_year.end.year),
                            'beginshort': str(last_year.begin.year)[-2:],
                            'endshort': str(last_year.end.year)[-2:]}
        newconvert_dict = {"begin": str(current_year.begin.year),
                           "end": str(current_year.end.year),
                           'beginshort': str(current_year.begin.year)[-2:],
                           'endshort': str(current_year.end.year)[-2:]}
        error = []
        new_by_default = None
        for cost_item in cost_list:
            patern_title = cost_item.name
            for convname, convvalue in lastconvert_dict.items():
                if match(r'(^|.*[^0-9])%s($|[^0-9].*)' % convvalue, patern_title):
                    patern_title = patern_title.replace(convvalue, "%%(%s)s" % convname)
            if patern_title != cost_item.name:
                new_name = patern_title % newconvert_dict
                if CostAccounting.objects.filter(name=new_name).count() > 0:
                    getLogger("diacamma.accounting").error("Failure to create new cost accouting '%s' from '%s'", new_name, cost_item)
                    error.append(cost_item.name)
                else:
                    new_cost = CostAccounting.objects.create(name=new_name, description=cost_item.description, year=cost_item.year.next_fiscalyear.first(), status=CostAccounting.STATUS_OPENED, last_costaccounting=cost_item)
                    if cost_item.is_default:
                        new_by_default = new_cost
            else:
                error.append(cost_item.name)
        if new_by_default is not None:
            new_by_default.change_has_default()
        return error

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if (self.id is not None) and (self.year is not None):
            entries = EntryAccount.objects.filter(entrylineaccount__costaccounting=self).exclude(year=self.year)
            if len(entries) > 0:
                raise LucteriosException(IMPORTANT, _('The cost accounting "%s" have entry with another year!') % self)
        res = LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
        for budget_item in self.budget_set.all():
            budget_item.year = self.year
            budget_item.save()
        return res

    class Meta(object):
        verbose_name = _('cost accounting')
        verbose_name_plural = _('costs accounting')
        default_permissions = []
        ordering = ['name']


class ChartsAccount(LucteriosModel):

    TYPE_ASSET = 0  # actif
    TYPE_LIABILITY = 1  # passif
    TYPE_EQUITY = 2  # capitaux
    TYPE_REVENUE = 3  # produit
    TYPE_EXPENSE = 4  # charge
    TYPE_CONTRAACCOUNTS = 5  # autres

    LIST_TYPES = (
        (TYPE_ASSET, _('Asset')),
        (TYPE_LIABILITY, _('Liability')),
        (TYPE_EQUITY, _('Equity')),
        (TYPE_REVENUE, _('Revenue')),
        (TYPE_EXPENSE, _('Expense')),
        (TYPE_CONTRAACCOUNTS, _('Contra-accounts'))
    )

    code = models.CharField(_('code'), max_length=50, db_index=True)
    name = models.CharField(_('name'), max_length=200)
    year = models.ForeignKey('FiscalYear', verbose_name=_('fiscal year'), null=False, on_delete=models.CASCADE, db_index=True)
    type_of_account = models.IntegerField(verbose_name=_('type of account'), choices=LIST_TYPES, null=True, db_index=True)
    rubric = models.CharField(_('rubric'), max_length=200, null=True, default="")

    last_year_total = LucteriosVirtualField(verbose_name=_('total of last year'), compute_from='get_last_year_total', format_string=lambda: format_with_devise(2))
    current_total = LucteriosVirtualField(verbose_name=_('total current'), compute_from='get_current_total', format_string=lambda: format_with_devise(2))
    current_validated = LucteriosVirtualField(verbose_name=_('total validated'), compute_from='get_current_validated', format_string=lambda: format_with_devise(2))

    @classmethod
    def get_default_fields(cls):
        return ['code', 'name', 'last_year_total', 'current_total', 'current_validated']

    @classmethod
    def get_edit_fields(cls):
        return ['code', 'name', 'type_of_account']

    @classmethod
    def get_show_fields(cls):
        return ['code', 'name', 'type_of_account']

    @classmethod
    def get_print_fields(cls):
        return ['code', 'name', 'last_year_total', 'current_total', 'current_validated', 'entrylineaccount_set', 'rubric']

    @classmethod
    def get_current_total_from_code(cls, code, year=None):
        if year is None:
            year_filter = Q(year__is_actif=True)
        else:
            year_filter = Q(year=year)
        account = ChartsAccount.objects.filter(Q(code__regex=code + '.*') & year_filter).first()
        if account is None:
            return None
        else:
            return account.current_total

    def __str__(self):
        return "[%s] %s" % (self.code, self.name)

    def get_name(self):
        return "[%s] %s" % (correct_accounting_code(self.code), self.name)

    def get_last_year_total(self, with_correction=True):
        if with_correction:
            return self.credit_debit_way() * get_amount_sum(self.entrylineaccount_set.filter(entry__journal__id=1).aggregate(Sum('amount')))
        else:
            return get_amount_sum(self.entrylineaccount_set.filter(entry__journal__id=1).aggregate(Sum('amount')))

    def get_current_total(self, with_correction=True):
        if self.id is None:
            return None
        entrylines = self.entrylineaccount_set.all()
        if self.type_of_account in (3, 4, 5):
            entrylines = entrylines.exclude(entry__in=self.year.get_result_entries())
        if with_correction:
            return self.credit_debit_way() * get_amount_sum(entrylines.aggregate(Sum('amount')))
        else:
            return get_amount_sum(entrylines.aggregate(Sum('amount')))

    def get_current_validated(self, with_correction=True):
        entrylines = self.entrylineaccount_set.filter(entry__close=True)
        if self.type_of_account in (3, 4, 5):
            entrylines = entrylines.exclude(entry__in=self.year.get_result_entries())
        if with_correction:
            return self.credit_debit_way() * get_amount_sum(entrylines.aggregate(Sum('amount')))
        else:
            return get_amount_sum(entrylines.aggregate(Sum('amount')))

    def credit_debit_way(self):
        if self.type_of_account in [0, 4]:
            return -1
        else:
            return 1

    @property
    def is_third(self):
        return match(current_system_account().get_third_mask(), self.code) is not None

    @property
    def is_cash(self):
        return match(current_system_account().get_cash_mask(), self.code) is not None

    @property
    def has_validated(self):
        return (self.id is not None) and (EntryAccount.objects.filter(entrylineaccount__account=self, close=True).distinct().count() > 0)

    @classmethod
    def get_account(cls, code, year):
        accounts = ChartsAccount.objects.filter(year=year if year is not None else FiscalYear.get_current(), code=code)
        if len(accounts) == 0:
            return None
        else:
            return accounts[0]

    @classmethod
    def get_chart_account(cls, code):
        current_year = FiscalYear.get_current()
        code = correct_accounting_code(code)
        try:
            chart = current_year.chartsaccount_set.get(code=code)
        except ObjectDoesNotExist:
            descript, typeaccount = current_system_account().new_charts_account(code)
            chart = ChartsAccount(year=current_year, code=code, name=descript, type_of_account=typeaccount)
        return chart

    @classmethod
    def get_rubriclist_from_entryline(self, entryline_filter):
        rubric_list = [account.rubric for account in ChartsAccount.objects.filter(entrylineaccount__in=EntryLineAccount.objects.filter(entryline_filter)) if account.rubric != ""]
        rubric_list = list(set(rubric_list))
        rubric_list.sort()
        return rubric_list

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        try:
            self.code = correct_accounting_code(self.code)
            exist_account = ChartsAccount.objects.get(
                code=self.code, year=self.year)
            if exist_account.id != self.id:
                raise LucteriosException(
                    IMPORTANT, _('Account already exists for this fiscal year!'))
        except ObjectDoesNotExist:
            pass
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @classmethod
    def import_initial(cls, year, account_item):
        if isfile(account_item):
            with open(account_item, 'r', encoding='UTF-8') as fcsv:
                csv_read = DictReader(fcsv, delimiter=';', quoting=QUOTE_NONE)
                for row in csv_read:
                    new_code = correct_accounting_code(row['code'])
                    if cls.get_account(new_code, year) is None:
                        account_desc = current_system_account().new_charts_account(new_code)
                        if account_desc[1] >= 0:
                            ChartsAccount.objects.create(year=year, code=new_code, name=row['name'], type_of_account=account_desc[1], rubric=row['rubric'] if 'rubric' in row else '')

    class Meta(object):
        verbose_name = _('charts of account')
        verbose_name_plural = _('charts of accounts')
        ordering = ['year', 'code']


class Journal(LucteriosModel):

    DEFAULT_LASTYEAR = 1
    DEFAULT_BUYING = 2
    DEFAULT_SELLING = 3
    DEFAULT_PAYMENT = 4
    DEFAULT_OTHER = 5
    LIST_DEFAULTS = [DEFAULT_LASTYEAR, DEFAULT_BUYING, DEFAULT_SELLING, DEFAULT_PAYMENT, DEFAULT_OTHER]

    name = models.CharField(_('name'), max_length=50, unique=True)
    is_default = models.BooleanField(verbose_name=_('default'), default=False, null=False)

    def __str__(self):
        return self.name

    def can_delete(self):
        if self.id in Journal.LIST_DEFAULTS:
            return _('journal reserved!')
        else:
            return ''

    @classmethod
    def get_default_fields(cls):
        return ["name", "is_default"]

    @classmethod
    def get_edit_fields(cls):
        return ['name']

    def change_has_default(self):
        if self.is_default:
            self.is_default = False
            self.save()
        else:
            all_journal = Journal.objects.all()
            for journal_item in all_journal:
                journal_item.is_default = False
                journal_item.save()
            self.is_default = True
            self.save()

    class Meta(object):

        verbose_name = _('accounting journal')
        verbose_name_plural = _('accounting journals')
        default_permissions = []


class AccountLink(LucteriosModel):

    letter = LucteriosVirtualField(verbose_name=_('link'), compute_from='get_letter')
    date_max = models.DateField(verbose_name=_('date max'), null=True, default=None)

    def __str__(self):
        return self.letter

    def get_letter(self):
        if self.id is None:
            return None
        entrylines = self.entrylineaccount_set.all()
        if len(entrylines) == 0:
            return ''
        year = entrylines[0].entry.year
        nb_link = AccountLink.objects.filter(entrylineaccount__entry__year=year, id__lt=self.id).count()
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        res = ''
        while nb_link >= 26:
            div, mod = divmod(nb_link, 26)
            res = letters[mod] + res
            nb_link = int(div) - 1
        res = letters[nb_link] + res
        if entrylines.exclude(entry__year=year).count() > 0:
            res += "&"
        return res

    def fill_date(self):
        search_maxdate = self.entrylineaccount_set.aggregate(Max('entry__date_value'))
        if 'entry__date_value__max' in search_maxdate:
            self.date_max = search_maxdate['entry__date_value__max']
            self.save()

    @classmethod
    def fill_emptydate(cls):
        for link in cls.objects.filter(date_max__isnull=True):
            link.fill_date()

    def is_validity(self):
        if self.id is None:
            return None
        third_info = None
        sum_amount = 0.0
        entrylines = self.entrylineaccount_set.all()
        is_valid = len(entrylines) > 0
        for entryline in entrylines:
            if third_info is None:
                third_info = (entryline.account.code, entryline.third_id)
            elif (third_info[0] != entryline.account.code) or (third_info[1] != entryline.third_id):
                is_valid = False
            sum_amount += float(entryline.amount)
        if abs(sum_amount) > 0.0001:
            is_valid = False
        return is_valid

    def check_validity(self):
        if not self.is_validity():
            self.delete()
            return False
        return True

    @classmethod
    def create_link(cls, entrylines):
        import re
        regex_third = re.compile(current_system_account().get_third_mask())
        years = []
        third_info = None
        sum_amount = 0.0
        for entryline in set(entrylines):
            entryline = EntryLineAccount.objects.get(id=entryline.id)
            if regex_third.match(entryline.account.code) is None:
                raise LucteriosException(IMPORTANT, _("An entry line is not third!"))
            if entryline.entry.year not in years:
                years.append(entryline.entry.year)
            if third_info is None:
                third_info = (entryline.account.code, entryline.third_id)
            elif (third_info[0] != entryline.account.code) or (third_info[1] != entryline.third_id):
                raise LucteriosException(IMPORTANT, _("This entry lines are not in same third!"))
            sum_amount += float(entryline.amount)
            entryline.unlink()
        if len(years) > 2:
            raise LucteriosException(IMPORTANT, _("This entries are over 2 years!"))
        elif (len(years) == 2) and (years[0].last_fiscalyear != years[1]) and (years[1].last_fiscalyear != years[0]):
            raise LucteriosException(IMPORTANT, _("These entries are not on 2 consecutive years!"))
        elif (len(years) == 2) and ((years[0].status == FiscalYear.STATUS_FINISHED) or (years[1].status == FiscalYear.STATUS_FINISHED)):
            raise LucteriosException(IMPORTANT, _("These entries are closed exercises!"))
        if abs(sum_amount) > 0.0001:
            raise LucteriosException(IMPORTANT, _("The input lines are not balanced!"))
        for entryline in entrylines:
            entryline = EntryLineAccount.objects.get(id=entryline.id)
            entryline.unlink()
        new_link = AccountLink.objects.create()
        if len(years) == 2:
            new_multilink = AccountLink.objects.create()
        else:
            new_multilink = None
        for entryline in entrylines:
            entryline.link = new_link
            if entryline.multilink_id is None:
                entryline.multilink = new_multilink
            entryline.save()
        new_link.fill_date()
        if new_multilink is not None:
            new_multilink.fill_date()

    def clean(self):
        if self.id is None:
            return None
        for entry in self.entryaccount_set.all():
            entry.link = None
            if not entry.delete_if_ghost_entry():
                entry.save()
        self.delete()

    class Meta(object):

        verbose_name = _('letter')
        verbose_name_plural = _('letters')
        default_permissions = []


class EntryAccount(LucteriosModel):
    year = models.ForeignKey('FiscalYear', verbose_name=_('fiscal year'), null=False, on_delete=models.CASCADE)
    num = models.IntegerField(verbose_name=_('numeros'), null=True)
    journal = models.ForeignKey('Journal', verbose_name=_('journal'), null=False, default=0, on_delete=models.PROTECT)
    link = models.ForeignKey('AccountLink', verbose_name=_('link'), null=True, on_delete=models.SET_NULL)
    date_entry = models.DateField(verbose_name=_('date entry'), null=True)
    date_value = models.DateField(verbose_name=_('date value'), null=False, db_index=True)
    designation = models.CharField(_('name'), max_length=200)
    costaccounting = models.ForeignKey('CostAccounting', verbose_name=_('cost accounting'), null=True, on_delete=models.PROTECT)
    close = models.BooleanField(verbose_name=_('close'), default=False, db_index=True)

    description = LucteriosVirtualField(verbose_name=_('description'), compute_from='get_description')

    def __str__(self):
        return "%s [%s] %s" % (get_date_formating(convert_date(self.date_value)), self.journal, self.designation)

    @classmethod
    def get_default_fields(cls):
        return ['num', 'date_entry', 'date_value', 'description']

    @classmethod
    def get_edit_fields(cls):
        return ['journal', 'date_value', 'designation']

    @classmethod
    def get_show_fields(cls):
        return ['num', 'journal', 'date_entry', 'date_value', 'designation']

    @classmethod
    def get_print_fields(cls):
        return cls.get_show_fields()

    @classmethod
    def get_search_fields(cls):
        result = ['year', 'date_value', 'num', 'designation', 'date_entry', 'entrylineaccount_set.costaccounting']
        result.append(('entrylineaccount_set.amount', models.DecimalField(_('amount')), 'entrylineaccount__amount__abs', Q()))
        result.extend(['entrylineaccount_set.account.code', 'entrylineaccount_set.account.name',
                       'entrylineaccount_set.account.type_of_account', 'entrylineaccount_set.reference'])
        for fieldname in Third.get_search_fields():
            result.append("entrylineaccount_set.third." + fieldname)
        return result

    @property
    def year_query(self):
        if hasattr(self, 'no_year_close') and self.no_year_close:
            return FiscalYear.objects.filter(status__in=(FiscalYear.STATUS_BUILDING, FiscalYear.STATUS_RUNNING))
        else:
            return FiscalYear.objects.all()

    @property
    def journal_query(self):
        if hasattr(self, 'no_year_close') and self.no_year_close and self.year.status == FiscalYear.STATUS_RUNNING:
            return Journal.objects.exclude(id=1)
        else:
            return Journal.objects.all()

    def set_context(self, xfer):
        if xfer.getparam('no_year_close', False):
            self.no_year_close = True
        elif hasattr(self, 'no_year_close'):
            del self.no_year_close

    @classmethod
    def clear_ghost(cls):
        if not RecordLocker.has_item_lock(cls):
            for entry in cls.objects.filter(close=False):
                if len(entry.entrylineaccount_set.all()) == 0:
                    entry.delete()
            for account_link in AccountLink.objects.annotate(num_entryline=Count('entrylineaccount')).filter(num_entryline=1):
                account_link.delete()

    def get_description(self):
        res = self.designation
        res += "{[br/]}\n"
        res += "{[table style='min-width:200px;']}\n"
        for line in self.entrylineaccount_set.all():
            res += "{[tr]}\n"
            res += "{[td]}%s{[/td]}\n" % line.entry_account
            res += "{[td]}%s{[/td]}\n" % get_amount_from_format_devise(line.debit, 6)
            res += "{[td]}%s{[/td]}\n" % get_amount_from_format_devise(line.credit, 6)
            res += "{[td]}%s{[/td]}\n" % (line.costaccounting if line.costaccounting is not None else '---',)
            res += "{[td]}%s{[/td]}\n" % (line.link if line.link is not None else '---',)
            if (line.reference is not None) and (line.reference != ''):
                res += "{[td]}%s{[/td]}\n" % line.reference
            res += "{[/tr]}\n"
        res += "{[/table]}"
        return res

    @property
    def is_asset(self):
        sum_customer = get_amount_sum(self.entrylineaccount_set.filter(account__code__regex=current_system_account().get_third_mask()).aggregate(Sum('amount')))
        return ((sum_customer < 0) and not self.has_cash) or ((sum_customer > 0) and self.has_cash)

    def reverse_entry(self):
        if self.id is None:
            return None
        for line in self.entrylineaccount_set.all():
            line.amount = -1 * line.amount
            line.save()

    def can_delete(self):
        if self.close:
            return _('entry of account closed!')
        else:
            return ''

    def check_date(self, checking=False):
        res = True
        if self.date_value is None:
            self.date_value = date.today()
            if checking:
                res = False
        if isinstance(self.date_value, date):
            self.date_value = self.date_value.isoformat()
        if self.journal_id == 1:
            self.date_value = self.year.begin.isoformat()
        if self.date_value > self.year.end.isoformat():
            self.date_value = self.year.end.isoformat()
            if checking:
                res = False
        if self.date_value < self.year.begin.isoformat():
            self.date_value = self.year.begin.isoformat()
            if checking:
                res = False
        return res

    def delete(self):
        self.unlink()
        for entryline in self.entrylineaccount_set.all():
            entryline.unlink()
        LucteriosModel.delete(self)

    def get_serial(self, entrylines=None):
        if entrylines is None:
            entrylines = self.entrylineaccount_set.all() if self.id is not None else []
        serial_val = ''
        for line in entrylines:
            if serial_val != '':
                serial_val += '\n'
            serial_val += line.get_serial()
        return serial_val

    def get_entrylineaccounts(self, serial_vals):
        res = QuerySet(model=EntryLineAccount)
        res._result_cache = []
        for serial_val in serial_vals.split('\n'):
            if serial_val != '':
                new_line = EntryLineAccount.get_entrylineaccount(serial_val)
                new_line.entry = self
                if new_line.account.year == self.year:
                    res._result_cache.append(new_line)
        return res

    def save_entrylineaccounts(self, serial_vals, check_integrity=True):
        if not self.close:
            old_linkids = [line.link_id for line in self.entrylineaccount_set.all() if line.link_id is not None]
            self.entrylineaccount_set.all().delete()
            for line in self.get_entrylineaccounts(serial_vals):
                if line.id < 0:
                    line.id = None
                line.save(check_integrity=check_integrity)
            has_link = False
            for line in self.entrylineaccount_set.all():
                if line.link_id is not None:
                    if line.link.check_validity():
                        has_link = True
            if not has_link:
                for old_linkid in old_linkids:
                    try:
                        link = AccountLink.objects.get(id=old_linkid)
                        link.delete()
                    except ObjectDoesNotExist:
                        pass

    def remove_entrylineaccounts(self, serial_vals, entrylineid):
        lines = self.get_entrylineaccounts(serial_vals)
        line_idx = -1
        for idx in range(len(lines)):
            if lines[idx].id == entrylineid:
                line_idx = idx
        del lines._result_cache[line_idx]
        return self.get_serial(lines)

    def add_new_entryline(self, serial_entry, entrylineaccount, num_cpt, credit_val, debit_val, third, costaccounting, reference):
        if self.journal.id == 1:
            charts = ChartsAccount.objects.get(id=num_cpt)
            if match(current_system_account().get_revenue_mask(), charts.code) or \
                    match(current_system_account().get_expence_mask(), charts.code):
                raise LucteriosException(IMPORTANT, _('This kind of entry is not allowed for this journal!'))
        if entrylineaccount != 0:
            serial_entry = self.remove_entrylineaccounts(serial_entry, entrylineaccount)
        if serial_entry != '':
            serial_entry += '\n'
        serial_entry += EntryLineAccount.add_serial(num_cpt, debit_val, credit_val, third, costaccounting, reference)
        return serial_entry

    def serial_control(self, serial_vals):
        total_credit = 0
        total_debit = 0
        serial = self.get_entrylineaccounts(serial_vals)
        current = self.entrylineaccount_set.all() if self.id is not None else []
        no_change = len(serial) > 0
        if len(serial) == len(current):
            for idx in range(len(serial)):
                total_credit += serial[idx].get_credit()
                total_debit += serial[idx].get_debit(with_correction=False)
                no_change = no_change and current[idx].equals(serial[idx])
        else:
            no_change = False
            for idx in range(len(serial)):
                total_credit += serial[idx].get_credit()
                total_debit += serial[idx].get_debit(with_correction=False)
        return no_change, currency_round(max(0, total_credit - total_debit)), currency_round(max(0, total_debit - total_credit))

    def closed(self, check_balance=True, check_needcost=True):
        if (self.year.status != 2) and not self.close:
            if check_balance:
                _no_change, debit_rest, credit_rest = self.serial_control(self.get_serial())
                if abs(debit_rest - credit_rest) >= 0.001:
                    raise LucteriosException(GRAVE, _("Account entry not balanced{[br/]}total credit=%(credit)s - total debit=%(debit)s%(info)s") % {'credit': get_amount_from_format_devise(debit_rest, 7),
                                                                                                                                                     'debit': get_amount_from_format_devise(credit_rest, 7),
                                                                                                                                                     'info': self.get_description()})
            if check_needcost and Params.getvalue("accounting-needcost"):
                nocost_filter = Q(account__type_of_account__in=(ChartsAccount.TYPE_REVENUE,
                                                                ChartsAccount.TYPE_EXPENSE,
                                                                ChartsAccount.TYPE_CONTRAACCOUNTS))
                nocost_filter &= Q(costaccounting__isnull=True)
                enties_nocost = self.entrylineaccount_set.filter(nocost_filter).distinct()
                if enties_nocost.count() > 0:
                    raise LucteriosException(IMPORTANT, _("Cost accounting is mandatory !"))
            self.close = True
            val = self.year.entryaccount_set.all().aggregate(Max('num'))
            if val['num__max'] is None:
                self.num = 1
            else:
                self.num = val['num__max'] + 1
            self.date_entry = date.today()
            self.save()

    def unlink(self):
        if self.year.status != FiscalYear.STATUS_FINISHED:
            if self.link_id is not None:
                self.link.clean()
                self.link = None

    def delete_if_ghost_entry(self):
        if (self.id is not None) and (len(self.entrylineaccount_set.all()) == 0) and not RecordLocker.is_lock(self):
            self.delete()
            return True
        else:
            return False

    def create_linked(self):
        if (self.year.status != FiscalYear.STATUS_FINISHED) and (self.link is None):
            paym_journ = Journal.objects.get(id=4)
            paym_desig = _('payment of %s') % self.designation
            new_entry = EntryAccount.objects.create(
                year=self.year, journal=paym_journ, designation=paym_desig, date_value=date.today())
            serial_val = ''
            for line in self.entrylineaccount_set.all():
                if line.account.is_third:
                    if serial_val != '':
                        serial_val += '\n'
                    serial_val += line.create_clone_inverse()
            return new_entry, serial_val

    def add_entry_line(self, amount, code, name=None, third=None, reference=None, with_correction=False, rubric=""):
        if abs(amount) > 0.0001:
            new_entry_line = EntryLineAccount()
            new_entry_line.entry = self
            new_entry_line.account = self.year.getorcreate_chartaccount(code, name, rubric)
            if with_correction:
                new_entry_line.amount = new_entry_line.account.credit_debit_way() * amount
            else:
                new_entry_line.amount = amount
            new_entry_line.third = third
            new_entry_line.reference = reference
            new_entry_line.save()
            return new_entry_line

    def get_thirds(self):
        return self.entrylineaccount_set.filter(account__code__regex=current_system_account().get_third_mask()).distinct()

    @property
    def has_third(self):
        return self.entrylineaccount_set.filter(account__code__regex=current_system_account().get_third_mask()).count() > 0

    @property
    def has_customer(self):
        return self.entrylineaccount_set.filter(account__code__regex=current_system_account().get_customer_mask()).count() > 0

    @property
    def has_cash(self):
        return self.entrylineaccount_set.filter(account__code__regex=current_system_account().get_cash_mask()).count() > 0

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if (self.costaccounting is not None) and (self.costaccounting.year_id is not None) and (self.costaccounting.year_id != self.year_id):
            self.costaccounting_id = None
        if ((self.id is None) or not self.close) and (self.year.status == FiscalYear.STATUS_FINISHED):
            raise LucteriosException(IMPORTANT, _('Can not save entry account on finished fiscal year !'))
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('entry of account')
        verbose_name_plural = _('entries of account')
        ordering = ['date_value']


class EntryLineAccount(LucteriosModel):
    account = models.ForeignKey('ChartsAccount', verbose_name=_('account'), null=False, on_delete=models.PROTECT)
    entry = models.ForeignKey('EntryAccount', verbose_name=_('entry'), null=False, on_delete=models.CASCADE)
    amount = models.FloatField(_('amount'), db_index=True)
    reference = models.CharField(_('reference'), max_length=200, null=True)
    third = models.ForeignKey('Third', verbose_name=_('third'), null=True, on_delete=models.PROTECT, db_index=True)
    costaccounting = models.ForeignKey('CostAccounting', verbose_name=_('cost accounting'), null=True, on_delete=models.PROTECT)
    link = models.ForeignKey('AccountLink', verbose_name=_('link'), null=True, on_delete=models.SET_NULL)
    multilink = models.ForeignKey('AccountLink', verbose_name=_('link'), null=True, on_delete=models.SET_NULL, related_name="multiyear")

    entry_account = LucteriosVirtualField(verbose_name=_('account'), compute_from='get_entry_account')
    debit = LucteriosVirtualField(verbose_name=_('debit'), compute_from='get_debit', format_string=lambda: format_with_devise(6))
    credit = LucteriosVirtualField(verbose_name=_('credit'), compute_from='get_credit', format_string=lambda: format_with_devise(6))
    designation_ref = LucteriosVirtualField(verbose_name=_('name'), compute_from='get_designation_ref')
    designation_ref_with_third = LucteriosVirtualField(verbose_name=_('name'), compute_from='get_designation_ref_with_third')
    link_costaccounting = LucteriosVirtualField(verbose_name=_('link/cost accounting'), compute_from='get_link_costaccounting')

    def get_auditlog_object(self):
        return self.entry.get_final_child()

    @classmethod
    def get_other_fields(cls):
        return ['entry_account', 'debit', 'credit', 'reference', 'costaccounting', 'link']

    @classmethod
    def get_default_fields(cls):
        return ['entry.num', 'entry.date_entry', 'entry.date_value', 'designation_ref', 'entry_account',
                'debit', 'credit', 'costaccounting', 'link']

    def get_color_ref(self):
        return self.entry_id

    @classmethod
    def get_edit_fields(cls):
        return ['entry.date_entry', 'entry.date_value', 'entry.designation', 'entry_account', 'debit', 'credit']

    @classmethod
    def get_import_fields(cls):
        return ['entry.date_value', 'entry.designation', 'account', 'debit', 'credit', 'third', 'reference', 'costaccounting']

    @classmethod
    def get_show_fields(cls):
        return ['entry.date_entry', 'entry.date_value', 'entry.designation', 'entry_account', 'debit', 'credit']

    @classmethod
    def get_print_fields(cls):
        return ['entry', 'entry_account', 'debit', 'credit', 'reference', 'third.contact.str', 'costaccounting.name']

    @classmethod
    def get_search_fields(cls):
        result = ['entry.year', 'entry.date_value', 'account.code', 'entry.journal']
        result.append(('amount', models.FloatField(_('amount')), 'amount__abs', Q()))
        result.extend(['reference', 'entry.num', 'entry.designation', 'entry.date_entry', 'costaccounting', 'account.name', 'account.type_of_account'])
        for fieldname in Third.get_search_fields():
            result.append(cls.convert_field_for_search('third', fieldname))
        return result

    def __str__(self):
        res = ""
        try:
            res = "%s %s" % (self.entry_account, get_amount_from_format_devise(self.account.credit_debit_way() * self.amount, 2))
            if (self.reference is not None) and (self.reference != ''):
                res += " (%s)" % self.reference
        except BaseException:
            res = "???"
        return res

    def get_thirdstr_in_cache(self):
        return Third.get_cache_text(self.third_id)

    def get_entry_account(self):
        if self.third_id is None:
            return str(self.account)
        else:
            return "[%s %s]" % (self.account.code, self.get_thirdstr_in_cache())

    def get_designation_ref(self):
        val = self.entry.designation
        if (self.reference is not None) and (self.reference != ''):
            val = "%s{[br/]}%s" % (val, self.reference)
        return val

    def get_designation_ref_with_third(self):
        val = self.entry.designation
        if getattr(self, 'full_eval', False) and not self.account.is_third:
            thirds = list(set([line.get_thirdstr_in_cache() for line in self.entry.entrylineaccount_set.filter(third__isnull=False)]))
            thirds.sort()
            if len(thirds) > 0:
                if len(thirds) <= 5:
                    val = "%s (%s)" % (val, ",".join(thirds))
                else:
                    val = "%s (%s ...)" % (val, ",".join(thirds[:5]))
        if (self.reference is not None) and (self.reference != ''):
            val = "%s{[br/]}%s" % (val, self.reference)
        return val

    def get_link_costaccounting(self):
        if self.link is not None:
            return str(self.link)
        if self.costaccounting is not None:
            return str(self.costaccounting)

    def get_debit(self, with_correction=True):
        try:
            if with_correction:
                return min(0, self.account.credit_debit_way() * self.amount)
            else:
                return max((0, -1 * self.account.credit_debit_way() * self.amount))
        except ObjectDoesNotExist:
            return 0.0

    def get_credit(self):
        try:
            return max((0, self.account.credit_debit_way() * self.amount))
        except ObjectDoesNotExist:
            return 0.0

    def set_montant(self, debit_val, credit_val):
        if debit_val > 0:
            self.amount = -1 * debit_val * self.account.credit_debit_way()
        elif credit_val > 0:
            self.amount = credit_val * self.account.credit_debit_way()
        else:
            self.amount = 0

    def equals(self, other):
        res = self.id == other.id
        res = res and (self.account.id == other.account.id)
        res = res and (abs(self.amount - other.amount) < 0.0001)
        res = res and (self.reference == other.reference)
        if self.third is None:
            res = res and (other.third is None)
        else:
            res = res and (self.third.id == other.third.id)
        if self.costaccounting is None:
            res = res and (other.costaccounting is None)
        else:
            res = res and (self.costaccounting.id == other.costaccounting.id)
        return res

    @classmethod
    def initialize_import(cls):
        super(EntryLineAccount, cls).initialize_import()
        if hasattr(cls, 'entry_imported'):
            del cls.entry_imported
        if hasattr(cls, 'serial_entry_imported'):
            del cls.serial_entry_imported

    @classmethod
    def import_data(cls, rowdata, dateformat):
        new_item = None
        if hasattr(cls, 'entry_imported'):
            if (cls.entry_imported.date_value != rowdata['entry.date_value']) or (cls.entry_imported.designation != rowdata['entry.designation']):
                new_item = cls.finalize_import()
        if not hasattr(cls, 'entry_imported'):
            cls.entry_imported = EntryAccount(year_id=rowdata['entry.year'], journal_id=rowdata['entry.journal'], date_value=rowdata['entry.date_value'], designation=rowdata['entry.designation'])
        if not hasattr(cls, 'serial_entry_imported'):
            cls.serial_entry_imported = ""
        account = ChartsAccount.objects.filter(code=rowdata['account'], year_id=rowdata['entry.year']).first()
        third = None
        if ('third' in rowdata) and (rowdata['third'].strip() != ''):
            q_legalentity = Q(contact__legalentity__name=rowdata['third'].strip())
            q_individual = Q(completename=rowdata['third'])
            third = Third.objects.annotate(completename=Concat('contact__individual__lastname',
                                                               Value(' '),
                                                               'contact__individual__firstname')).annotate(num_entryline=Count('entrylineaccount')).filter(q_legalentity | q_individual).first()
            if third is None:
                cls.import_logs.append(_("Third '%s' unknown !") % rowdata['third'].strip())

        costaccounting = None
        if ('costaccounting' in rowdata) and (rowdata['costaccounting'].strip() != ''):
            costaccounting = CostAccounting.objects.filter(name=rowdata['costaccounting'].strip(), status=0).first()
            if costaccounting is None:
                cls.import_logs.append(_("Cost accounting '%s' unknown !") % rowdata['costaccounting'].strip())
        reference = rowdata['reference'] if 'reference' in rowdata else None
        if account is not None:
            cls.serial_entry_imported = cls.entry_imported.add_new_entryline(cls.serial_entry_imported, 0, account.id,
                                                                             credit_val=rowdata['credit'], debit_val=rowdata['debit'],
                                                                             third=third.id if third is not None else 0,
                                                                             costaccounting=costaccounting.id if costaccounting is not None else 0,
                                                                             reference=reference)
        else:
            cls.import_logs.append(_("Account code '%s' unknown !") % rowdata['account'])
        return new_item

    @classmethod
    def finalize_import(cls):
        new_item = None
        if hasattr(cls, 'entry_imported'):
            if not hasattr(cls, 'serial_entry_imported'):
                cls.serial_entry_imported = ""
            if not cls.entry_imported.check_date(checking=True):
                cls.import_logs.append(_("Invalid date '%s' !") % cls.entry_imported.date_value)
            else:
                _no_change, debit_rest, credit_rest = cls.entry_imported.serial_control(cls.serial_entry_imported)
                if (debit_rest < 0.0001) and (credit_rest < 0.0001) and (len(cls.serial_entry_imported) > 0):
                    new_item = cls.entry_imported
                    new_item.save()
                    new_item.save_entrylineaccounts(cls.serial_entry_imported)
                elif len(cls.entry_imported.get_entrylineaccounts(cls.serial_entry_imported)) > 1:
                    cls.import_logs.append(_("Account entry not balanced{[br/]}total credit=%(credit)s - total debit=%(debit)s%(info)s") % {'credit': get_amount_from_format_devise(debit_rest, 7),
                                                                                                                                            'debit': get_amount_from_format_devise(credit_rest, 7), 'info': ''})
                elif len(cls.entry_imported.get_entrylineaccounts(cls.serial_entry_imported)) == 1:
                    cls.import_logs.append(_("Account entry '%s' with only one line") % cls.entry_imported.designation)
            del cls.serial_entry_imported
            del cls.entry_imported
        return new_item

    def get_serial(self):
        # return serial information: "<id>|<accound id>|<third id> or 0|<amount>|<cost id> or 0|<link id> or 0|<reference> or None"
        if self.third is None:
            third_id = 0
        else:
            third_id = self.third.id
        if self.reference is None:
            reference = 'None'
        else:
            reference = self.reference
        if self.costaccounting is None:
            costaccounting_id = 0
        else:
            costaccounting_id = self.costaccounting.id
        if self.link is None:
            link_id = 0
        else:
            link_id = self.link.id
        return "%d|%d|%d|%f|%d|%d|%s|" % (self.id, self.account.id, third_id, self.amount, costaccounting_id, link_id, reference)

    @classmethod
    def add_serial(cls, num_cpt, debit_val, credit_val, thirdid=0, costaccountingid=0, reference=None):
        import time
        new_entry_line = cls()
        new_entry_line.id = -1 * int(time.time() * 60)
        new_entry_line.account = ChartsAccount.objects.get(id=num_cpt)
        if thirdid == 0:
            new_entry_line.third = None
        else:
            new_entry_line.third = Third.objects.get(id=thirdid)
        if (costaccountingid == 0) or (new_entry_line.account.type_of_account not in (3, 4, 5)):
            new_entry_line.costaccounting = None
        else:
            new_entry_line.costaccounting = CostAccounting.objects.get(id=costaccountingid)
        new_entry_line.set_montant(debit_val, credit_val)
        if reference == "None":
            new_entry_line.reference = None
        else:
            new_entry_line.reference = reference
        return new_entry_line.get_serial()

    @classmethod
    def get_entrylineaccount(cls, serial_val):
        serial_vals = serial_val.split('|')
        new_entry_line = cls()
        new_entry_line.id = int(serial_vals[0])
        new_entry_line.account = ChartsAccount.objects.get(id=int(serial_vals[1]))
        if int(serial_vals[2]) == 0:
            new_entry_line.third = None
        else:
            new_entry_line.third = Third.objects.get(id=int(serial_vals[2]))
        new_entry_line.amount = float(serial_vals[3])
        if (int(serial_vals[4]) == 0) or (new_entry_line.account.type_of_account not in (3, 4, 5)):
            new_entry_line.costaccounting = None
        else:
            new_entry_line.costaccounting = CostAccounting.objects.get(id=int(serial_vals[4]))
        if int(serial_vals[5]) == 0:
            new_entry_line.link = None
        else:
            new_entry_line.link = AccountLink.objects.get(id=int(serial_vals[5]))
        new_entry_line.reference = "".join(serial_vals[6:-1])
        if new_entry_line.reference.startswith("None"):
            new_entry_line.reference = None
        return new_entry_line

    def create_clone_inverse(self):
        import time
        new_entry_line = EntryLineAccount()
        new_entry_line.id = -1 * int(time.time() * 60)
        new_entry_line.account = self.account
        if self.third:
            new_entry_line.third = self.third
        else:
            new_entry_line.third = None
        new_entry_line.amount = -1 * self.amount
        if self.costaccounting:
            new_entry_line.costaccounting = self.costaccounting
        else:
            new_entry_line.costaccounting = None
        new_entry_line.reference = self.reference
        return new_entry_line.get_serial()

    @property
    def has_account(self):
        try:
            return self.account is not None
        except ObjectDoesNotExist:
            return False

    def unlink(self, with_multi=False):
        if self.entry.year.status != FiscalYear.STATUS_FINISHED:
            if self.link_id is not None:
                try:
                    self.link.clean()
                except ObjectDoesNotExist:
                    pass
                self.link = None
            if with_multi and (self.multilink_id is not None):
                try:
                    self.multilink.clean()
                except ObjectDoesNotExist:
                    pass
                self.multilink = None

    def delete(self):
        self.unlink()
        LucteriosModel.delete(self)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None, check_integrity=True):
        if self.id == 0:
            self.id = None
        if (self.account.type_of_account not in (3, 4, 5)) and (self.costaccounting is not None):
            self.costaccounting = None
        if check_integrity and (self.costaccounting is not None) and (self.costaccounting.status == CostAccounting.STATUS_CLOSED):
            raise LucteriosException(IMPORTANT, _('The cost accounting "%s" is closed !') % self.costaccounting)
        if check_integrity and (self.costaccounting is not None) and (self.costaccounting.year is not None) and (self.costaccounting.year != self.entry.year):
            raise LucteriosException(IMPORTANT, _('The cost accounting "%s" has another year!') % self.costaccounting)
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('entry line of account')
        verbose_name_plural = _('entry lines of account')
        default_permissions = []
        ordering = ['entry__date_value', 'entry_id', 'account__code', 'third']


class ModelEntry(LucteriosModel):
    journal = models.ForeignKey('Journal', verbose_name=_('journal'), null=False, default=0, on_delete=models.PROTECT)
    designation = models.CharField(_('name'), max_length=200)
    costaccounting = models.ForeignKey('CostAccounting', verbose_name=_('cost accounting'), null=True,
                                       default=None, on_delete=models.SET_NULL)

    total = LucteriosVirtualField(verbose_name=_('total'), compute_from='get_total', format_string=lambda: format_with_devise(5))

    def __str__(self):
        return "[%s] %s (%s)" % (self.journal, self.designation, self.total)

    @classmethod
    def get_default_fields(cls):
        return ['journal', 'designation', 'costaccounting', 'total']

    @classmethod
    def get_edit_fields(cls):
        return ['journal', 'designation', 'costaccounting']

    @classmethod
    def get_show_fields(cls):
        return ['journal', 'designation', 'costaccounting', 'total', 'modellineentry_set']

    def get_total(self):
        if self.id is None:
            return 0.0
        try:
            value = 0.0
            for line in self.modellineentry_set.all():
                value += line.get_credit()
            return value
        except LucteriosException:
            return 0.0

    def get_serial_entry(self, factor, year, costaccounting=None):
        entry_lines = []
        num = 0
        for line in self.modellineentry_set.all():
            entry_lines.append(line.get_entry_line(factor, num, year, costaccounting))
            num += 1
        return EntryAccount().get_serial(entry_lines)

    class Meta(object):
        verbose_name = _('Model of entry')
        verbose_name_plural = _('Models of entry')
        default_permissions = []


class ModelLineEntry(LucteriosModel):
    model = models.ForeignKey('ModelEntry', verbose_name=_('model'), null=False, default=0, on_delete=models.CASCADE)
    code = models.CharField(_('code'), max_length=50)
    third = models.ForeignKey('Third', verbose_name=_('third'), null=True, on_delete=models.PROTECT)
    amount = models.FloatField(_('amount'), default=0)

    debit = LucteriosVirtualField(verbose_name=_('debit'), compute_from='get_debit', format_string=lambda: format_with_devise(0))
    credit = LucteriosVirtualField(verbose_name=_('credit'), compute_from='get_credit', format_string=lambda: format_with_devise(0))
    code_txt = LucteriosVirtualField(verbose_name=_('code'), compute_from='get_code_txt')

    def get_auditlog_object(self):
        return self.model.get_final_child()

    @classmethod
    def get_default_fields(cls):
        return ['code_txt', 'third', 'debit', 'credit']

    @classmethod
    def get_edit_fields(cls):
        return ['code']

    def credit_debit_way(self):
        chart_account = current_system_account().new_charts_account(self.code)
        if chart_account[0] == '':
            raise LucteriosException(IMPORTANT, _("Invalid code"))
        if chart_account[1] in [0, 4]:
            return -1
        else:
            return 1

    def get_debit(self, with_correction=True):
        try:
            return max((0, -1 * self.credit_debit_way() * self.amount))
        except LucteriosException:
            return 0.0

    def get_credit(self):
        try:
            return max((0, self.credit_debit_way() * self.amount))
        except LucteriosException:
            return 0.0

    def get_code_txt(self):
        account = ChartsAccount.get_account(self.code, None)
        if account is None:
            return self.code
        else:
            return str(account)

    def set_montant(self, debit_val, credit_val):
        if debit_val > 0:
            self.amount = -1 * debit_val * self.credit_debit_way()
        elif credit_val > 0:
            self.amount = credit_val * self.credit_debit_way()
        else:
            self.amount = 0

    def get_entry_line(self, factor, num, year, costaccounting=None):
        import time
        try:
            new_entry_line = EntryLineAccount()
            new_entry_line.id = -1 * int(time.time() * 60) + (num * 15)
            new_entry_line.account = ChartsAccount.objects.get(year=year, code=correct_accounting_code(self.code))
            new_entry_line.third = self.third
            new_entry_line.amount = currency_round(self.amount * factor)
            if (costaccounting is not None) and (new_entry_line.account.type_of_account in (3, 4, 5)):
                new_entry_line.costaccounting = costaccounting
            new_entry_line.reference = None
            return new_entry_line
        except ObjectDoesNotExist:
            raise LucteriosException(IMPORTANT, _('Account code "%s" unknown for this fiscal year!') % self.code)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.code = correct_accounting_code(self.code)
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('Model line')
        verbose_name_plural = _('Model lines')
        default_permissions = []


class Budget(LucteriosModel):
    year = models.ForeignKey('FiscalYear', verbose_name=_('fiscal year'), null=True, default=None, on_delete=models.CASCADE)
    cost_accounting = models.ForeignKey('CostAccounting', verbose_name=_('cost accounting'), null=True, default=None, on_delete=models.CASCADE)
    code = models.CharField(_('account'), max_length=50)
    amount = models.FloatField(_('amount'), default=0)

    budget = LucteriosVirtualField(verbose_name=_('code'), compute_from='get_budget')
    montant = LucteriosVirtualField(verbose_name=_('amount'), compute_from='get_montant', format_string=lambda: format_with_devise(2))

    def __str__(self):
        return "[%s] %s : %s" % (self.year, self.budget, get_amount_from_format_devise(self.montant, 2))

    @classmethod
    def get_default_fields(cls):
        return ['budget', 'montant']

    @classmethod
    def get_edit_fields(cls):
        return ['code']

    def get_budget(self):
        chart = ChartsAccount.get_chart_account(self.code)
        return str(chart)

    def credit_debit_way(self):
        chart_account = current_system_account().new_charts_account(self.code)
        if chart_account[0] == '':
            raise LucteriosException(IMPORTANT, _("Invalid code"))
        if chart_account[1] in [0, 4]:
            return -1
        else:
            return 1

    def get_montant(self):
        return self.credit_debit_way() * self.amount

    def get_debit(self, with_correction=True):
        try:
            return max((0, -1 * self.credit_debit_way() * self.amount))
        except LucteriosException:
            return 0.0

    def get_credit(self):
        try:
            return max((0, self.credit_debit_way() * self.amount))
        except LucteriosException:
            return 0.0

    def set_montant(self, debit_val, credit_val):
        if debit_val > 0:
            self.amount = -1 * debit_val * self.credit_debit_way()
        elif credit_val > 0:
            self.amount = credit_val * self.credit_debit_way()
        else:
            self.amount = 0

    @classmethod
    def get_total(cls, year, cost):
        budget_filter = Q()
        if year is not None:
            budget_filter &= Q(year_id=year)
        if cost is not None:
            budget_filter &= Q(cost_accounting_id=cost)
        total_revenue = get_amount_sum(cls.objects.filter(budget_filter & Q(code__regex=current_system_account().get_revenue_mask())).aggregate(Sum('amount')))
        total_expense = get_amount_sum(cls.objects.filter(budget_filter & Q(code__regex=current_system_account().get_expence_mask())).aggregate(Sum('amount')))
        return total_revenue - total_expense

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if (self.cost_accounting is not None) and (self.cost_accounting.year_id is not None):
            self.year = self.cost_accounting.year
        if str(self.id)[0] == 'C':
            value = self.amount
            year = self.year_id
            chart_code = self.code
            self.delete()
            for current_budget in Budget.objects.filter(year_id=year, code=chart_code):
                value -= current_budget.amount
            if abs(value) > 0.001:
                Budget.objects.create(code=chart_code, amount=value, year_id=year)
        else:
            return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def delete(self, using=None):
        if str(self.id)[0] == 'C':
            for budget_line in Budget.objects.filter(Q(year_id=self.year_id) & Q(code=self.code)):
                if budget_line.cost_accounting_id is None:
                    budget_line.delete()
        else:
            LucteriosModel.delete(self, using=using)

    class Meta(object):
        verbose_name = _('Budget line')
        verbose_name_plural = _('Budget lines')
        ordering = ['code']


def is_with_VAT():
    return Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE


def add_vat_info():
    return _(' (duty free)') if is_with_VAT() else ''


def check_accountingcost():
    for entry in EntryAccount.objects.filter(costaccounting_id__gt=0, year__status__in=(FiscalYear.STATUS_BUILDING, FiscalYear.STATUS_RUNNING)):
        try:
            if (entry.costaccounting.status == CostAccounting.STATUS_CLOSED) and not entry.close:
                entry.costaccounting = None
                entry.save()
        except ObjectDoesNotExist:
            entry.costaccounting = None
            entry.save()
    entryline_cmp = 0
    for entryline in EntryLineAccount.objects.filter(costaccounting_id__isnull=True, entry__costaccounting_id__isnull=False, account__type_of_account__in=(ChartsAccount.TYPE_REVENUE, ChartsAccount.TYPE_EXPENSE, ChartsAccount.TYPE_CONTRAACCOUNTS)).distinct():
        entryline.costaccounting_id = entryline.entry.costaccounting_id
        entryline.save(check_integrity=False)
        entryline_cmp += 1
    if entryline_cmp > 0:
        getLogger("diacamma.accounting").info(' * convert costaccounting: nb=%d', entryline_cmp)


def check_accountlink():
    new_link = 0
    old_link = 0
    account_link_list = list(AccountLink.objects.filter(entryaccount__isnull=False))
    for account_link in account_link_list:
        entryline_by_third = {}
        for entry_linked in account_link.entryaccount_set.all():
            for entryline_third in entry_linked.get_thirds():
                third_id = (entryline_third.account.code, entryline_third.third_id)
                if third_id not in entryline_by_third.keys():
                    entryline_by_third[third_id] = []
                entryline_by_third[third_id].append(entryline_third)
        for entrylines in entryline_by_third.values():
            try:
                AccountLink.create_link(set(entrylines))
                new_link += 1
            except LucteriosException as lct_ext:
                getLogger("diacamma.accounting").error('!!! check_accountlink Error: %s  - lines: %s', lct_ext, entrylines)
        old_link += 1
        account_link.delete()
    if old_link > 0:
        from django.utils.module_loading import import_module
        from django.apps.registry import apps
        if apps.is_installed("diacamma.invoice"):
            invoice_model = import_module('diacamma.invoice.models')
            invoice_model.correct_quotation_asset_account()
        if apps.is_installed("diacamma.payoff"):
            payoff_model = import_module('diacamma.payoff.models')
            addon_linked = payoff_model.check_accountlink_from_supporting()
        else:
            addon_linked = 0
        getLogger("diacamma.accounting").info(' * convert AccountLink: old= %d / new= %d + %d', old_link, new_link, addon_linked)


def pre_save_datadb(sender, **kwargs):
    if (sender == EntryAccount) and ('instance' in kwargs):
        if kwargs['instance'].costaccounting_id == 0:
            print('* Convert EntryAccount #%d' % kwargs['instance'].id)
            kwargs['instance'].costaccounting_id = None


def get_meta_currency_iso_list():
    currency_file = join(dirname(__file__), 'currency_iso.csv')
    if isfile(currency_file):
        currency_list = []
        with open(currency_file, 'r', encoding='utf-8') as currency_hdl:
            for line in currency_hdl.readlines():
                line = line.strip()
                if line.count(';') == 1:
                    iso_ident, title = line.split(';')
                    symbole = get_currency_symbole(iso_ident)
                    if iso_ident != symbole:
                        symbole = "%s / %s" % (iso_ident, symbole)
                    currency_list.append((iso_ident, "%s (%s)" % (title, symbole)))
        return currency_list
    else:
        return None


def get_meta_currency_iso():
    currency_list = get_meta_currency_iso_list()
    if currency_list is not None:
        currency_list = get_meta_currency_iso_list()
        return '("","",%s,"",True)' % str(currency_list)
    else:
        return None


@Signal.decorate('fiscalyear_change')
def change_in_accounting():
    current_year = FiscalYear.get_current()
    for cost_item in CostAccounting.objects.filter(year=current_year, is_protected=False):
        if cost_item.last_costaccounting is not None:
            Signal.call_signal("costaccounting_change", cost_item, True, cost_item.last_costaccounting)
        if cost_item.next_costaccounting.first() is not None:
            Signal.call_signal("costaccounting_change", cost_item, False, cost_item.next_costaccounting.first())


@Signal.decorate('costaccounting_change')
def accounting_changecost_model(new_cost, lastcost, old_cost):
    for model in ModelEntry.objects.filter(costaccounting=old_cost):
        model.costaccounting = new_cost
        model.save()
    if lastcost and old_cost.last_costaccounting is not None:
        accounting_changecost_model(new_cost, lastcost=True, old_cost=old_cost.last_costaccounting)
    if not lastcost and old_cost.next_costaccounting.first() is not None:
        accounting_changecost_model(new_cost, lastcost=False, old_cost=old_cost.next_costaccounting.first())


@Signal.decorate('check_report')
def check_report_accounting(year):
    if year.status == FiscalYear.STATUS_FINISHED:
        FiscalYear.save_reports(year, last_user=None)


@Signal.decorate('checkparam')
def accounting_checkparam():
    Parameter.check_and_create(name='accounting-devise-iso', typeparam=Parameter.TYPE_STRING, title=_("accounting-devise-iso"), args="{'Multi':False}",
                               value='EUR', meta=get_meta_currency_iso())
    Parameter.check_and_create(name='accounting-devise-prec', typeparam=Parameter.TYPE_INTEGER, title=_("accounting-devise-prec"), args="{'Min':0, 'Max':4}", value='2')
    Parameter.check_and_create(name='accounting-system', typeparam=Parameter.TYPE_STRING, title=_("accounting-system"), args="{'Multi':False}", value='')
    Parameter.check_and_create(name='accounting-sizecode', typeparam=Parameter.TYPE_INTEGER, title=_("accounting-sizecode"), args="{'Min':3, 'Max':50}", value='3')
    Parameter.check_and_create(name='accounting-needcost', typeparam=Parameter.TYPE_BOOL, title=_("accounting-needcost"), args="{}", value='False')
    Parameter.check_and_create(name='accounting-code-report-filter', typeparam=Parameter.TYPE_STRING, title=_("accounting-code-report-filter"), args="{'Multi':False}", value='')
    Parameter.check_and_create(name="accounting-lettering-check", typeparam=Parameter.TYPE_STRING, title=_("accounting-lettering-check"), args="{'Multi':True}", value='',
                               meta='("accounting","ChartsAccount","import diacamma.accounting.tools;django.db.models.Q(code__regex=diacamma.accounting.tools.current_system_account().get_third_mask()) & django.db.models.Q(year__is_actif=True)", "code", False)')
    Parameter.check_and_create(name='accounting-datecurrent', typeparam=Parameter.TYPE_BOOL, title=_("accounting-datecurrent"), args="{}", value='True')
    Parameter.check_and_create(name='accounting-VAT-arrangements', typeparam=Parameter.TYPE_SELECT, title=_("accounting-VAT-arrangements"),
                               args="{'Enum':2, 'Min':0}", value='-1', param_titles=(_("accounting-VAT-arrangements.-1"), _("accounting-VAT-arrangements.0"), _("accounting-VAT-arrangements.1")))
    Parameter.check_and_create(name='accounting-einvoicing-conf', typeparam=Parameter.TYPE_STRING, title=_("accounting-einvoicing-conf"), args="{'Multi':True}", value='{}')

    LucteriosGroup.redefine_generic(_("# accounting (administrator)"), FiscalYear.get_permission(True, True, True),
                                    ChartsAccount.get_permission(True, True, True), Budget.get_permission(True, True, True),
                                    Third.get_permission(True, True, True), EntryAccount.get_permission(True, True, True))
    LucteriosGroup.redefine_generic(_("# accounting (editor)"), FiscalYear.get_permission(True, True, False),
                                    ChartsAccount.get_permission(True, True, False), Budget.get_permission(True, True, False),
                                    Third.get_permission(True, True, False), EntryAccount.get_permission(True, True, False))
    LucteriosGroup.redefine_generic(_("# accounting (shower)"), ChartsAccount.get_permission(True, False, False), Budget.get_permission(True, False, False),
                                    Third.get_permission(True, False, False), EntryAccount.get_permission(True, False, False))


def check_total_income():
    for year in FiscalYear.objects.all().order_by('end'):
        try:
            year.check_report()
        except Exception:
            getLogger("lucterios.core.print").exception('accounting_convertdata')
        entries = year.get_result_entries()
        if (len(entries) == 1) and (entries[0].entrylineaccount_set.count() == 1):
            current_system_account()._add_total_income_entrylines(year, entries[0])


def check_yearaccount():
    for entryline in EntryLineAccount.objects.exclude(Q(entry__year=F("account__year"))):  # check link between year of entry and year of account code
        entryline.account = entryline.entry.year.getorcreate_chartaccount(entryline.account.code, entryline.account.name, entryline.account.rubric)
        entryline.save()


def check_third():
    for entryline in EntryLineAccount.objects.filter(Q(third__isnull=False) & ~Q(account__code__regex=current_system_account().get_third_mask())):
        entryline.third = None
        entryline.save()


def check_multilink():
    for link in AccountLink.objects.filter(entrylineaccount__multilink__isnull=False).exclude(entrylineaccount__entry__year__status=FiscalYear.STATUS_FINISHED):
        lines = link.entrylineaccount_set.all()
        if len(set([line.entry.year for line in lines])) == 1:
            firstline = lines.first()
            if firstline and (firstline.multilink_id is not None):
                try:
                    firstline.multilink.clean()
                    getLogger("diacamma.accounting").info('* remove multilink for %s - %s', link, firstline)
                except ObjectDoesNotExist:
                    pass
                firstline.multilink = None
    AccountLink.fill_emptydate()


def check_prefixyear():
    for year in FiscalYear.objects.filter(prefix=''):
        year.save()


def check_vat_arrangements():
    if Params.getvalue("accounting-VAT-arrangements") == -1:
        vat_arrangements_ret = []
        Signal.call_signal("vat_arrangements", vat_arrangements_ret)
        if len(vat_arrangements_ret) != 1:
            Params.setvalue("accounting-VAT-arrangements", FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE)
        else:
            Params.setvalue("accounting-VAT-arrangements", vat_arrangements_ret[0])


@Signal.decorate('convertdata')
def accounting_convertdata():
    check_accountingcost()
    check_accountlink()
    check_total_income()
    check_yearaccount()
    check_third()
    check_multilink()
    check_prefixyear()
    EntryAccount.clear_ghost()
    check_vat_arrangements()


@Signal.decorate('auditlog_register')
def accounting_auditlog_register():
    auditlog.register(Third, include_fields=["contact", "status"])
    auditlog.register(ThirdCustomField, include_fields=['field', 'data'], mapping_fields=['field'])
    auditlog.register(AccountThird, include_fields=["third", "code"])
    auditlog.register(Journal, exclude_fields=['ID'])
    auditlog.register(FiscalYear, include_fields=['begin', 'end', 'status', 'is_actif'])
    auditlog.register(ModelEntry, include_fields=['journal', 'designation', 'costaccounting'])
    auditlog.register(ModelLineEntry, include_fields=['code', 'third', 'debit', 'credit'])
    auditlog.register(CostAccounting, include_fields=['name', 'description', 'year', 'last_costaccounting', 'status', 'is_default'])
    auditlog.register(ChartsAccount, include_fields=['year', 'code', 'name', 'type_of_account'])
    auditlog.register(Budget, include_fields=['budget', 'montant', 'year', 'cost_accounting'])
    auditlog.register(EntryAccount, include_fields=['num', 'date_entry', 'date_value', 'journal', 'date_value', 'designation', 'year'])
    auditlog.register(EntryLineAccount, include_fields=['entry_account', 'debit', 'credit', 'costaccounting', 'link', 'third', 'reference'])


pre_save.connect(pre_save_datadb)
