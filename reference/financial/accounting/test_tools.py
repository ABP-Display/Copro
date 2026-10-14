# -*- coding: utf-8 -*-
'''
Describe test for Django

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
from base64 import b64encode

from lucterios.framework import signal_and_lock
from lucterios.CORE.models import Parameter
from lucterios.CORE.parameters import Params

from lucterios.contacts.models import Individual, LegalEntity, AbstractContact
from lucterios.contacts.test_tools import change_ourdetail
from lucterios.documents.models import DocumentContainer

from diacamma.accounting.tools import clear_system_account
from diacamma.accounting.models import Third, AccountThird, FiscalYear, \
    ChartsAccount, EntryAccount, Journal, AccountLink, \
    CostAccounting, ModelEntry, ModelLineEntry, Budget
from diacamma.accounting.views_reports import FiscalYearReportPrint


def create_individual(firstname, lastname):
    empty_contact = Individual()
    empty_contact.firstname = firstname
    empty_contact.lastname = lastname
    empty_contact.address = "rue de la liberté"
    empty_contact.postal_code = "97250"
    empty_contact.city = "LE PRECHEUR"
    empty_contact.country = "MARTINIQUE"
    empty_contact.tel2 = "02-78-45-12-95"
    empty_contact.email = "%s.%s@worldcompany.com" % (firstname, lastname)
    empty_contact.save()
    return empty_contact


def change_legal(name):
    ourdetails = LegalEntity()
    ourdetails.name = name
    ourdetails.address = "Place des cocotiers"
    ourdetails.postal_code = "97200"
    ourdetails.city = "FORT DE FRANCE"
    ourdetails.country = "MARTINIQUE"
    ourdetails.tel1 = "01-23-45-67-89"
    ourdetails.email = "%s@worldcompany.com" % name
    ourdetails.save()
    return ourdetails


def initial_contacts():
    change_ourdetail()  # contact 1
    create_individual('Avrel', 'Dalton')  # contact 2
    create_individual('William', 'Dalton')  # contact 3
    create_individual('Jack', 'Dalton')  # contact 4
    create_individual('Joe', 'Dalton')  # contact 5
    create_individual('Lucky', 'Luke')  # contact 6
    change_legal("Minimum")  # contact 7
    change_legal("Maximum")  # contact 8


def create_third(abstractids, codes=None):
    for abstractid in abstractids:
        new_third = Third.objects.create(contact=AbstractContact.objects.get(id=abstractid), status=0)
        if codes is not None:
            for code in codes:
                AccountThird.objects.create(third=new_third, code=code)


def create_year(status=0, year=2015, lastyear=None):
    new_year = FiscalYear.objects.create(begin='%s-01-01' % year, end='%s-12-31' % year, status=status, last_fiscalyear=lastyear)
    new_year.set_has_actif()
    return new_year


def create_account(codes, type_of_account, year=None, rubric=""):
    account_ids = []
    if year is None:
        year = FiscalYear.get_current()
    for code in codes:
        chart = ChartsAccount.objects.create(code=code, name=code, rubric=rubric, type_of_account=type_of_account, year=year)
        account_ids.append(chart.id)
    return account_ids


def fill_thirds_fr():
    create_third([2, 8], ['401'])  # 1 2
    create_third([6, 7], ['411', '401'])  # 3 4
    create_third([3, 4, 5], ['411'])  # 5 6 7


def initial_thirds_fr():
    initial_contacts()
    fill_thirds_fr()


def fill_accounts_fr(year=None, with12=True, with8=False, with_rubric=False):
    Params.setvalue('accounting-sizecode', 3)
    create_account(['411'], 0, year)  # 1
    create_account(['512', '531'], 0, year)  # 2 3
    create_account(['401'], 1, year)  # 4
    create_account(['106', '110', '119'], 2, year)  # 5 6 7
    create_account(['701', '706', '707'], 3, year, "DDD" if with_rubric else "")  # 8 9 10
    create_account(['601', '602', '604'], 4, year, "EEE" if with_rubric else "")  # 11 12 13
    create_account(['607', '627'], 4, year, "FFF" if with_rubric else "")  # 14 15
    if with12:
        create_account(['120', '129'], 2, year)  # 16 17
    if with8:
        create_account(['860', '870'], 5, year)  # 18 19


def default_compta_fr(status=0, with12=True, with8=False, with_rubric=False):
    from diacamma.payoff.views_conf import paramchange_payoff
    paramchange_payoff([])
    Params.setvalue('accounting-VAT-arrangements', 0)
    set_accounting_system('FR')
    year = create_year(status)
    fill_accounts_fr(year, with12, with8, with_rubric)


def fill_thirds_be():
    create_third([2, 8], ['440000'])  # 1 2
    create_third([6, 7], ['400000', '440000'])  # 3 4
    create_third([3, 4, 5], ['400000'])  # 5 6 7


def initial_thirds_be():
    initial_contacts()
    fill_thirds_be()


def fill_accounts_be(year=None, with14=True):
    Params.setvalue('accounting-sizecode', 6)
    create_account(['400000', '550000', '570000'], 0, year)  # 1 2 3
    create_account(['440000'], 1, year)  # 4

    create_account(['130000', '132000', '133000'], 2, year)  # 5 6 7
    create_account(['700000', '701000', '705000'], 3, year)  # 8 9 10
    create_account(['600000', '601000', '602000', '603000', '604000'], 4, year)  # 11 12 13 14 15
    if with14:
        create_account(['140000'], 2, year)  # 16
        create_account(['141000'], 2, year)  # 17


def default_compta_be(status=0, with14=True):
    from diacamma.payoff.views_conf import paramchange_payoff
    paramchange_payoff([])
    set_accounting_system('BE')
    year = create_year(status)
    fill_accounts_be(year, with14)


def fill_thirds_ma():
    create_third([2, 8], ['4411'])  # 1 2
    create_third([6, 7], ['4421', '4411'])  # 3 4
    create_third([3, 4, 5], ['4421'])  # 5 6 7


def initial_thirds_ma():
    initial_contacts()
    fill_thirds_ma()


def fill_accounts_ma(year=None, with11=True):
    Params.setvalue('accounting-sizecode', 4)
    create_account(['4421'], 0, year)  # 1
    create_account(['5121', '5161'], 0, year)  # 2 3
    create_account(['4411'], 1, year)  # 4
    create_account(['1140', '1161', '1169'], 2, year)  # 5 6 7
    create_account(['7111', '7121', '7161'], 3, year)  # 8 9 10
    create_account(['6111', '6121', '6131'], 4, year)  # 11 12 13
    create_account(['6161', '6171'], 4, year)  # 14 15
    if with11:
        create_account(['1191', '1199'], 2, year)  # 16 17


def default_compta_ma(status=0, with14=True):
    from diacamma.payoff.views_conf import paramchange_payoff
    paramchange_payoff([])
    set_accounting_system('MA')
    year = create_year(status)
    fill_accounts_ma(year, with14)


def default_costaccounting():
    CostAccounting.objects.create(name='close', description='Close cost', status=1, is_default=False)
    CostAccounting.objects.create(name='open', description='Open cost', status=0, is_default=True)


def add_models():
    default_costaccounting()
    model1 = ModelEntry.objects.create(journal=Journal.objects.get(id=2), designation='achat')
    ModelLineEntry.objects.create(model=model1, code='411', third=Third.objects.get(id=3), amount=19.37)
    ModelLineEntry.objects.create(model=model1, code='512', amount=-19.37)
    model2 = ModelEntry.objects.create(journal=Journal.objects.get(id=3), designation='vente')
    ModelLineEntry.objects.create(model=model2, code='401', third=Third.objects.get(id=6), amount=-68.47)
    ModelLineEntry.objects.create(model=model2, code='531', amount=68.47)
    model3 = ModelEntry.objects.create(journal=Journal.objects.get(id=2), designation='service', costaccounting_id=2)
    ModelLineEntry.objects.create(model=model3, code='411', third=Third.objects.get(id=3), amount=-37.91)
    ModelLineEntry.objects.create(model=model3, code='601', amount=37.91)


def set_accounting_system(country='FR'):
    country_list = {
        'FR': 'diacamma.accounting.system.french.FrenchSystemAcounting',
        'BE': 'diacamma.accounting.system.belgium.BelgiumSystemAcounting',
        'MA': 'diacamma.accounting.system.morocco.MoroccoSystemAcounting'
    }
    Parameter.change_value('accounting-system', country_list[country])
    Params.clear()
    clear_system_account()
    signal_and_lock.Signal.call_signal("param_change", ['accounting-system'])


def get_accounting_system():
    country_list = {'FR': 'diacamma.accounting.system.french.FrenchSystemAcounting', 'BE': 'diacamma.accounting.system.belgium.BelgiumSystemAcounting'}
    for contry, account_system in country_list.items():
        if account_system == Params.getvalue("accounting-system"):
            return contry
    return None


def add_entry(yearid, journalid, date_value, designation, serial_entry, closed=False):
    year = FiscalYear.objects.get(id=yearid)
    journal = Journal.objects.get(id=journalid)
    new_entry = EntryAccount.objects.create(year=year, journal=journal, date_value=date_value, designation=designation)
    new_entry.save_entrylineaccounts(serial_entry, check_integrity=False)
    if closed:
        new_entry.closed()
    return new_entry


def fill_entries_fr(yearid, withyear=False):

    default_costaccounting()
    # cost id=1: dep=12.34 / rec=0.00 => res=-12.34
    # cost id=2: dep=258.02 / rec=70.64 => res=-187.38
    if withyear:
        currentyear = str(FiscalYear.objects.get(id=yearid).begin.year)
    else:
        currentyear = '2015'

    _ = add_entry(yearid, 1, '%s-02-01' % currentyear, 'Report à nouveau', '-1|5|0|1250.380000|0|0|None|\n-2|2|0|1135.930000|0|0|None|\n-3|3|0|114.450000|0|0|None|', True)  # 1 2 3
    entry2 = add_entry(yearid, 2, '%s-02-14' % currentyear, 'depense 1', '-1|12|0|63.940000|2|0|None|\n-2|4|4|63.940000|0|0|None|', True)  # 4 5 - cost 2
    entry3 = add_entry(yearid, 4, '%s-02-15' % currentyear, 'regement depense 1', '-1|2|0|-63.940000|0|0|ch N°34543|\n-2|4|4|-63.940000|0|0|None|', True)  # 6 7
    entry4 = add_entry(yearid, 2, '%s-02-13' % currentyear, 'depense 2', '-1|14|0|194.080000|2|0|None|\n-2|4|1|194.080000|0|0|None|')  # 8 9 - cost 2
    entry5 = add_entry(yearid, 4, '%s-02-17' % currentyear, 'regement depense 2', '-1|3|0|-194.080000|0|0|ch N°34545|\n-2|4|1|-194.080000|0|0|None|')  # 10 11
    _ = add_entry(yearid, 2, '%s-02-20' % currentyear, 'depense 3', '-1|11|0|78.240000|0|0|None|\n-2|4|2|78.240000|0|0|None|')  # 12 13
    entry7 = add_entry(yearid, 3, '%s-02-21' % currentyear, 'vente 1', '-1|10|0|70.640000|2|0|None|\n-2|1|7|70.640000|0|0|None|', True)  # 14 15 - cost 2
    entry8 = add_entry(yearid, 4, '%s-02-22' % currentyear, 'regement vente 1', '-1|2|0|70.640000|0|0|BP N°654321|\n-2|1|7|-70.640000|0|0|None|', True)  # 16 17
    _ = add_entry(yearid, 3, '%s-02-21' % currentyear, 'vente 2', '-1|10|0|125.970000|0|0|None|\n-2|1|5|125.970000|0|0|None|', True)  # 18 19
    _ = add_entry(yearid, 3, '%s-02-24' % currentyear, 'vente 3', '-1|10|0|34.010000|0|0|None|\n-2|1|4|34.010000|0|0|None|')  # 20 21
    _ = add_entry(yearid, 5, '%s-02-20' % currentyear, 'Frais bancaire', '-1|2|0|-12.340000|0|0|None|\n-2|15|0|12.340000|1|0|None|', True)  # 22 23 - cost 1
    Budget.objects.create(year_id=yearid, code='701', amount=67.89)
    Budget.objects.create(year_id=yearid, code='707', amount=123.45)
    Budget.objects.create(year_id=yearid, code='601', amount=8.19)
    Budget.objects.create(year_id=yearid, code='602', amount=7.35)
    Budget.objects.create(year_id=yearid, code='604', amount=6.24)
    AccountLink.create_link(list(entry2.get_thirds()) + list(entry3.get_thirds()))
    AccountLink.create_link(list(entry4.get_thirds()) + list(entry5.get_thirds()))
    AccountLink.create_link(list(entry7.get_thirds()) + list(entry8.get_thirds()))


def fill_entries_be(yearid, withyear=False):

    default_costaccounting()
    # cost id=1: dep=12.34 / rec=0.00 => res=-12.34
    # cost id=2: dep=258.02 / rec=70.64 => res=-187.38
    if withyear:
        currentyear = str(FiscalYear.objects.get(id=yearid).begin.year)
    else:
        currentyear = '2015'

    _ = add_entry(yearid, 1, '%s-02-01' % currentyear, 'Report à nouveau', '-1|5|0|1250.380000|0|0|None|\n-2|2|0|1135.930000|0|0|None|\n-3|3|0|114.450000|0|0|None|', True)  # 1 2 3
    entry2 = add_entry(yearid, 2, '%s-02-14' % currentyear, 'depense 1', '-1|12|0|63.940000|2|0|None|\n-2|4|4|63.940000|0|0|None|', True)  # 4 5 - cost 2
    entry3 = add_entry(yearid, 4, '%s-02-15' % currentyear, 'regement depense 1', '-1|2|0|-63.940000|0|0|ch N°34543|\n-2|4|4|-63.940000|0|0|None|', True)  # 6 7
    entry4 = add_entry(yearid, 2, '%s-02-13' % currentyear, 'depense 2', '-1|14|0|194.080000|2|0|None|\n-2|4|1|194.080000|0|0|None|')  # 8 9 - cost 2
    entry5 = add_entry(yearid, 4, '%s-02-17' % currentyear, 'regement depense 2', '-1|3|0|-194.080000|0|0|ch N°34545|\n-2|4|1|-194.080000|0|0|None|')  # 10 11
    _ = add_entry(yearid, 2, '%s-02-20' % currentyear, 'depense 3', '-1|11|0|78.240000|0|0|None|\n-2|4|2|78.240000|0|0|None|')  # 12 13
    entry7 = add_entry(yearid, 3, '%s-02-21' % currentyear, 'vente 1', '-1|10|0|70.640000|2|0|None|\n-2|1|7|70.640000|0|0|None|', True)  # 14 15 - cost 2
    entry8 = add_entry(yearid, 4, '%s-02-22' % currentyear, 'regement vente 1', '-1|2|0|70.640000|0|0|BP N°654321|\n-2|1|7|-70.640000|0|0|None|', True)  # 16 17
    _ = add_entry(yearid, 3, '%s-02-21' % currentyear, 'vente 2', '-1|10|0|125.970000|0|0|None|\n-2|1|5|125.970000|0|0|None|', True)  # 18 19
    _ = add_entry(yearid, 3, '%s-02-24' % currentyear, 'vente 3', '-1|10|0|34.010000|0|0|None|\n-2|1|4|34.010000|0|0|None|')  # 20 21
    _ = add_entry(yearid, 5, '%s-02-20' % currentyear, 'Frais bancaire', '-1|2|0|-12.340000|0|0|None|\n-2|15|0|12.340000|1|0|None|', True)  # 22 23 - cost 1
    Budget.objects.create(year_id=yearid, code='700000', amount=67.89)
    Budget.objects.create(year_id=yearid, code='705000', amount=123.45)
    Budget.objects.create(year_id=yearid, code='600000', amount=8.19)
    Budget.objects.create(year_id=yearid, code='601000', amount=7.35)
    Budget.objects.create(year_id=yearid, code='602000', amount=6.24)
    AccountLink.create_link(list(entry2.get_thirds()) + list(entry3.get_thirds()))
    AccountLink.create_link(list(entry4.get_thirds()) + list(entry5.get_thirds()))
    AccountLink.create_link(list(entry7.get_thirds()) + list(entry8.get_thirds()))


def fill_entries_ma(yearid, withyear=False):
    default_costaccounting()
    if withyear:
        currentyear = str(FiscalYear.objects.get(id=yearid).begin.year)
    else:
        currentyear = '2015'

    _ = add_entry(yearid, 1, '%s-02-01' % currentyear, 'Report à nouveau', '-1|5|0|1250.380000|0|0|None|\n-2|2|0|1135.930000|0|0|None|\n-3|3|0|114.450000|0|0|None|', True)  # 1 2 3
    entry2 = add_entry(yearid, 2, '%s-02-14' % currentyear, 'depense 1', '-1|12|0|63.940000|2|0|None|\n-2|4|4|63.940000|0|0|None|', True)  # 4 5 - cost 2
    entry3 = add_entry(yearid, 4, '%s-02-15' % currentyear, 'regement depense 1', '-1|2|0|-63.940000|0|0|ch N°34543|\n-2|4|4|-63.940000|0|0|None|', True)  # 6 7
    entry4 = add_entry(yearid, 2, '%s-02-13' % currentyear, 'depense 2', '-1|14|0|194.080000|2|0|None|\n-2|4|1|194.080000|0|0|None|')  # 8 9 - cost 2
    entry5 = add_entry(yearid, 4, '%s-02-17' % currentyear, 'regement depense 2', '-1|3|0|-194.080000|0|0|ch N°34545|\n-2|4|1|-194.080000|0|0|None|')  # 10 11
    _ = add_entry(yearid, 2, '%s-02-20' % currentyear, 'depense 3', '-1|11|0|78.240000|0|0|None|\n-2|4|2|78.240000|0|0|None|')  # 12 13
    entry7 = add_entry(yearid, 3, '%s-02-21' % currentyear, 'vente 1', '-1|10|0|70.640000|2|0|None|\n-2|1|7|70.640000|0|0|None|', True)  # 14 15 - cost 2
    entry8 = add_entry(yearid, 4, '%s-02-22' % currentyear, 'regement vente 1', '-1|2|0|70.640000|0|0|BP N°654321|\n-2|1|7|-70.640000|0|0|None|', True)  # 16 17
    _ = add_entry(yearid, 3, '%s-02-21' % currentyear, 'vente 2', '-1|10|0|125.970000|0|0|None|\n-2|1|5|125.970000|0|0|None|', True)  # 18 19
    _ = add_entry(yearid, 3, '%s-02-24' % currentyear, 'vente 3', '-1|10|0|34.010000|0|0|None|\n-2|1|4|34.010000|0|0|None|')  # 20 21
    _ = add_entry(yearid, 5, '%s-02-20' % currentyear, 'Frais bancaire', '-1|2|0|-12.340000|0|0|None|\n-2|15|0|12.340000|1|0|None|', True)  # 22 23 - cost 1
    Budget.objects.create(year_id=yearid, code='7111', amount=67.89)
    Budget.objects.create(year_id=yearid, code='7161', amount=123.45)
    Budget.objects.create(year_id=yearid, code='6111', amount=8.19)
    Budget.objects.create(year_id=yearid, code='6121', amount=7.35)
    Budget.objects.create(year_id=yearid, code='6131', amount=6.24)
    AccountLink.create_link(list(entry2.get_thirds()) + list(entry3.get_thirds()))
    AccountLink.create_link(list(entry4.get_thirds()) + list(entry5.get_thirds()))
    AccountLink.create_link(list(entry7.get_thirds()) + list(entry8.get_thirds()))


def check_pdfreport(testobj, year, pdfname, printclassname, modulename):
    doc = DocumentContainer.objects.filter(name=pdfname).first()
    testobj.assertTrue(doc is not None)
    doc_content = b64encode(doc.content.read()).decode()

    testobj.factory.xfer = FiscalYearReportPrint()
    testobj.calljson('/diacamma.accounting/fiscalYearReportPrint', {'year': year, 'classname': printclassname, "modulename": modulename, "PRINT_MODE": 3, 'PRINT_PERSITENT_MODE': 0}, False)
    testobj.assert_observer('core.print', 'diacamma.accounting', 'fiscalYearReportPrint')
    testobj.assertEqual(doc_content, testobj.response_json['print']["content"], doc.name)

    testobj.factory.xfer = FiscalYearReportPrint()
    testobj.calljson('/diacamma.accounting/fiscalYearReportPrint', {'year': year, 'classname': printclassname, "modulename": modulename, "PRINT_MODE": 3, 'PRINT_PERSITENT_MODE': 1}, False)
    testobj.assert_observer('core.print', 'diacamma.accounting', 'fiscalYearReportPrint')
    testobj.assertNotEqual(doc_content, testobj.response_json['print']["content"], doc.name)
