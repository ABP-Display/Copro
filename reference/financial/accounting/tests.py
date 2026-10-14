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
from shutil import rmtree
from datetime import date, timedelta
from base64 import b64decode
from unittest import mock
from json import loads

from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.CORE.views import StatusMenu, ParamEdit, ObjectMerge
from lucterios.contacts.views import CustomFieldAddModify

from diacamma.accounting.views import ThirdList, ThirdAdd, ThirdSave, ThirdShow, AccountThirdAddModify, AccountThirdDel, ThirdListing, ThirdDisable, ThirdEdit, ThirdSearch
from diacamma.accounting.views_admin import Configuration, ConfigurationAccountingSystem, JournalAddModify, JournalDel, FiscalYearAddModify, FiscalYearActive, FiscalYearDel, \
    JournalDefault
from diacamma.accounting.views_other import ModelEntryList, ModelEntryAddModify, ModelLineEntryAddModify, \
    ModelEntryShow
from diacamma.accounting.test_tools import initial_contacts, fill_entries_fr, initial_thirds_fr, create_third, fill_accounts_fr, fill_thirds_fr, default_compta_fr, set_accounting_system, add_models
from diacamma.accounting.models import FiscalYear, Third
from diacamma.accounting.system import get_accounting_system, accounting_system_ident
from diacamma.accounting.tools import current_system_account, clear_system_account, \
    format_with_devise
from diacamma.accounting.views_entries import EntryAccountModelSelector
from lucterios.CORE.parameters import Params
from lucterios.contacts.models import CustomField
from lucterios.contacts.views_contacts import IndividualList


class ThirdTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        initial_contacts()
        rmtree(get_user_dir(), True)
        clear_system_account()

    def test_add_abstract(self):
        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 0)

        self.factory.xfer = ThirdAdd()
        self.calljson('/diacamma.accounting/thirdAdd', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdAdd')
        self.assert_comp_equal(('SELECT', 'modelname'), 'contacts.AbstractContact', (1, 0, 4, 1))
        self.assert_select_equal('modelname', 3)  # nb=3
        self.assert_count_equal('abstractcontact', 8)

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'abstractcontact', 'abstractcontact': 5}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assertEqual(self.response_json['action']['action'], 'thirdShow')
        self.assertEqual(self.response_json['action']['params']['third'], 1)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 1)
        self.assert_json_equal('', 'third/@0/contact', 'Dalton Joe')
        self.assert_json_equal('', 'third/@0/accountthird_set', [])

    def test_add_legalentity(self):
        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 0)

        self.factory.xfer = ThirdAdd()
        self.calljson('/diacamma.accounting/thirdAdd', {'modelname': 'contacts.LegalEntity'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdAdd')
        self.assert_comp_equal(('SELECT', 'modelname'), 'contacts.LegalEntity', (1, 0, 4, 1))
        self.assert_grid_equal('legal_entity', {"name": "dénomination", "tel1": "tel1", "tel2": "tel2", "email": "courriel"}, 3)  # nb=4

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'legal_entity', 'legal_entity': 7, 'new_account': '401'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assertEqual(self.response_json['action']['action'], 'thirdShow')
        self.assertEqual(self.response_json['action']['params']['third'], 1)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 1)
        self.assert_json_equal('', 'third/@0/contact', 'Minimum')
        self.assert_json_equal('', 'third/@0/accountthird_set', ['401'])

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_json_equal('LABELFORM', 'contact', 'Minimum')
        self.assert_json_equal('', '#show/action/extension', 'lucterios.contacts')
        self.assert_json_equal('', '#show/action/action', 'legalEntityShow')
        self.assert_json_equal('', '#show/action/params/legal_entity', 7)

    def test_add_individual(self):
        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 0)

        self.factory.xfer = ThirdAdd()
        self.calljson('/diacamma.accounting/thirdAdd', {'modelname': 'contacts.Individual'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdAdd')
        self.assert_comp_equal(('SELECT', 'modelname'), 'contacts.Individual', (1, 0, 4, 1))
        self.assert_grid_equal('individual', {"firstname": "prénom", "lastname": "nom", "tel1": "tel1", "tel2": "tel2", "email": "courriel"}, 5)  # nb=5

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'individual', 'individual': 3, 'new_account': '401;411'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assertEqual(self.response_json['action']['action'], 'thirdShow')
        self.assertEqual(self.response_json['action']['params']['third'], 1)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 1)
        self.assert_json_equal('', 'third/@0/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@0/accountthird_set', ['401', '411'])

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_json_equal('LABELFORM', 'contact', 'Dalton William')
        self.assert_json_equal('', '#show/action/extension', 'lucterios.contacts')
        self.assert_json_equal('', '#show/action/action', 'individualShow')
        self.assert_json_equal('', '#show/action/params/individual', 3)

    def test_check_double(self):
        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 0)

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'abstractcontact', 'abstractcontact': 5}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assertEqual(self.response_json['action']['action'], 'thirdShow')
        self.assertEqual(self.response_json['action']['params']['third'], 1)

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'abstractcontact', 'abstractcontact': 5}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assertEqual(self.response_json['action']['action'], 'thirdShow')
        self.assertEqual(self.response_json['action']['params']['third'], 1)

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'abstractcontact', 'abstractcontact': 5}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assertEqual(self.response_json['action']['action'], 'thirdShow')
        self.assertEqual(self.response_json['action']['params']['third'], 1)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 1)

    def test_show(self):
        create_third([3])
        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertEqual(len(self.json_actions), 2)
        self.assertTrue('__tab_1' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4)
        self.assert_json_equal('LABELFORM', 'contact', 'Dalton William')
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_grid_equal('accountthird', {'code': "code", 'total_txt': "total"}, 0)  # nb=2
        self.assert_count_equal('accountthird', 0)
        self.assert_json_equal('LABELFORM', 'total', 0.0)

        self.factory.xfer = AccountThirdAddModify()
        self.calljson('/diacamma.accounting/accountThirdAddModify', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'accountThirdAddModify')
        self.assert_count_equal('', 2)
        self.assert_json_equal('EDIT', 'code', '')

        self.factory.xfer = AccountThirdAddModify()
        self.calljson('/diacamma.accounting/accountThirdAddModify', {'SAVE': 'YES', "third": 1, 'code': '411'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'accountThirdAddModify')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('accountthird', 1)
        self.assert_json_equal('', 'accountthird/@0/code', '411')
        self.assert_json_equal('', 'accountthird/@0/total_txt', 0.0)
        self.assert_json_equal('LABELFORM', 'total', 0.0)

        self.factory.xfer = AccountThirdDel()
        self.calljson('/diacamma.accounting/accountThirdDel', {'CONFIRME': 'YES', "accountthird": 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'accountThirdDel')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('accountthird', 0)

        fill_thirds_fr()
        default_compta_fr()

        self.factory.xfer = AccountThirdAddModify()
        self.calljson('/diacamma.accounting/accountThirdAddModify', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'accountThirdAddModify')
        self.assert_count_equal('', 2)
        self.assert_json_equal('SELECT', 'code', '401')

    def test_show_withdata(self):
        fill_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)
        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 4}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 3 + 4)
        self.assert_json_equal('LABELFORM', 'contact', 'Minimum')
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_grid_equal('accountthird', {'code': "code", 'total_txt': "total"}, 2)  # nb=2
        self.assert_json_equal('', '#accountthird/headers/@1/@0', 'total_txt')
        self.assert_json_equal('', '#accountthird/headers/@1/@1', 'total')
        self.assert_json_equal('', '#accountthird/headers/@1/@2', "C2EUR")
        self.assert_json_equal('', '#accountthird/headers/@1/@4', '{[p align=\'right\']}{[font color="green"]}Crédit: %s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}Débit: %s{[/font]}{[/p]};{[p align=\'right\']}%s{[/p]}')

        self.assert_json_equal('', 'accountthird/@0/id', '5')
        self.assert_json_equal('', 'accountthird/@0/code', '411')
        self.assert_json_equal('', 'accountthird/@0/total_txt', -34.01)
        self.assert_json_equal('', 'accountthird/@1/id', '6')
        self.assert_json_equal('', 'accountthird/@1/code', '401')
        self.assert_json_equal('', 'accountthird/@1/total_txt', 0.0)
        self.assert_json_equal('LABELFORM', 'total', -34.01)

        self.assert_json_equal('SELECT', 'lines_filter', '0')
        self.assert_select_equal('lines_filter', 4)  # nb=4
        self.assert_count_equal('entryline', 3)
        self.assert_json_equal('', 'entryline/@0/entry.num', '2')
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@0/credit', 63.94)
        self.assert_json_equal('', 'entryline/@1/entry.num', '3')
        self.assert_json_equal('', 'entryline/@1/link', 'A')
        self.assert_json_equal('', 'entryline/@1/debit', -63.94)
        self.assert_json_equal('', 'entryline/@2/entry.num', None)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@2/debit', -34.01)

        self.factory.xfer = AccountThirdDel()
        self.calljson('/diacamma.accounting/accountThirdDel', {"accountthird": 5}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'accountThirdDel')
        self.assert_json_equal('', 'message', "Ce compte n'est pas soldé !")

        self.factory.xfer = AccountThirdDel()
        self.calljson('/diacamma.accounting/accountThirdDel', {"accountthird": 6}, False)
        self.assert_observer('core.dialogbox', 'diacamma.accounting', 'accountThirdDel')

    def test_show_withdata_linesfilter(self):
        fill_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 4, 'lines_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 3 + 4)
        self.assert_json_equal('SELECT', 'lines_filter', '0')
        self.assert_select_equal('lines_filter', 4)  # nb=4
        self.assert_grid_equal('entryline', {"entry.num": "N°", "entry.date_entry": "date d'écriture", "entry.date_value": "date de pièce", "designation_ref": "nom",
                                             "entry_account": "compte", 'debit': 'débit', 'credit': 'crédit', "costaccounting": "comptabilité analytique", "link": "lettrage"}, 3)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 4, 'lines_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 3 + 4)
        self.assert_json_equal('SELECT', 'lines_filter', '1')
        self.assert_select_equal('lines_filter', 4)  # nb=4
        self.assert_count_equal('entryline', 1)

        default_compta_fr()

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 4, 'lines_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 3 + 4)
        self.assert_json_equal('SELECT', 'lines_filter', '0')
        self.assert_select_equal('lines_filter', 4)  # nb=4
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 4, 'lines_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 3 + 4)
        self.assert_json_equal('SELECT', 'lines_filter', '2')
        self.assert_select_equal('lines_filter', 4)  # nb=4
        self.assert_count_equal('entryline', 3)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 4, 'lines_filter': 3}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 3 + 4)
        self.assert_json_equal('SELECT', 'lines_filter', '3')
        self.assert_select_equal('lines_filter', 4)  # nb=4
        self.assert_count_equal('entryline', 1)

    def test_list(self):
        fill_thirds_fr()
        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'legal_entity', 'legal_entity': 7, 'new_account': '421;451'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'individual', 'individual': 3, 'new_account': '421'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('third', {'contact': "contact", 'accountthird_set': "compte"}, 7)  # nb=2
        self.assert_json_equal('', 'third/@0/contact', 'Dalton Avrel')
        self.assert_json_equal('', 'third/@0/accountthird_set', ['401'])
        self.assert_json_equal('', 'third/@1/contact', 'Dalton Jack')
        self.assert_json_equal('', 'third/@1/accountthird_set', ['411'])
        self.assert_json_equal('', 'third/@2/contact', 'Dalton Joe')
        self.assert_json_equal('', 'third/@2/accountthird_set', ['411'])
        self.assert_json_equal('', 'third/@3/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@3/accountthird_set', ['411', '421'])
        self.assert_json_equal('', 'third/@4/contact', 'Luke Lucky')
        self.assert_json_equal('', 'third/@4/accountthird_set', ['411', '401'])
        self.assert_json_equal('', 'third/@5/contact', 'Maximum')
        self.assert_json_equal('', 'third/@5/accountthird_set', ['401'])
        self.assert_json_equal('', 'third/@6/contact', 'Minimum')
        self.assert_json_equal('', 'third/@6/accountthird_set', ['411', '401', '421', '451'])

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'GRID_ORDER%third': '1', 'GRID_ORDER%third+': '-'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 7)
        self.assert_json_equal('', 'third/@0/contact', 'Dalton Avrel')
        self.assert_json_equal('', 'third/@1/contact', 'Dalton Jack')
        self.assert_json_equal('', 'third/@2/contact', 'Dalton Joe')
        self.assert_json_equal('', 'third/@3/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@4/contact', 'Luke Lucky')
        self.assert_json_equal('', 'third/@5/contact', 'Maximum')
        self.assert_json_equal('', 'third/@6/contact', 'Minimum')

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'GRID_ORDER%third': '1', 'GRID_ORDER%third+': '+'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 7)
        self.assert_json_equal('', 'third/@6/contact', 'Dalton Avrel')
        self.assert_json_equal('', 'third/@5/contact', 'Dalton Jack')
        self.assert_json_equal('', 'third/@4/contact', 'Dalton Joe')
        self.assert_json_equal('', 'third/@3/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@2/contact', 'Luke Lucky')
        self.assert_json_equal('', 'third/@1/contact', 'Maximum')
        self.assert_json_equal('', 'third/@0/contact', 'Minimum')

    def test_list_withfilter(self):
        fill_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)

        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'legal_entity', 'legal_entity': 7, 'new_account': '421;451'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')
        self.factory.xfer = ThirdSave()
        self.calljson('/diacamma.accounting/thirdSave', {'pkname': 'individual', 'individual': 3, 'new_account': '421'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdSave')

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'filter': 'dalton joe'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('third', {'contact': "contact", 'accountthird_set': "compte"}, 1)  # nb=2
        self.assert_json_equal('', 'third/@0/contact', 'Dalton Joe')
        self.assert_json_equal('', 'third/@0/accountthird_set', ['411'])

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'thirdtype': 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 5)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'thirdtype': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 4)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'thirdtype': 3}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 1)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'thirdtype': 4}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 2)

    def test_list_display(self):
        fill_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)
        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'show_filter': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('third', {'contact': "contact", 'accountthird_set': "compte", 'total': "total"}, 7)  # nb=3
        self.assert_count_equal('third', 7)
        self.assert_json_equal('', 'third/@1/contact', 'Dalton Jack')
        self.assert_json_equal('', 'third/@1/accountthird_set', ['411'])
        self.assert_json_equal('', 'third/@1/total', 0.0)
        self.assert_json_equal('', 'third/@3/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@3/accountthird_set', ['411'])
        self.assert_json_equal('', 'third/@3/total', -125.97)
        self.assert_json_equal('', 'third/@6/contact', 'Minimum')
        self.assert_json_equal('', 'third/@6/accountthird_set', ['411', '401'])
        self.assert_json_equal('', 'third/@6/total', -34.01)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'show_filter': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('third', {'contact': "contact", 'accountthird_set': "compte", 'total': "total"}, 3)  # nb=3
        self.assert_json_equal('', 'third/@0/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@0/accountthird_set', ['411'])
        self.assert_json_equal('', 'third/@0/total', -125.97)
        self.assert_json_equal('', 'third/@1/contact', 'Maximum')
        self.assert_json_equal('', 'third/@1/accountthird_set', ['401'])
        self.assert_json_equal('', 'third/@1/total', 78.24)
        self.assert_json_equal('', 'third/@2/contact', 'Minimum')
        self.assert_json_equal('', 'third/@2/accountthird_set', ['411', '401'])
        self.assert_json_equal('', 'third/@2/total', -34.01)

    def test_listing(self):
        fill_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)
        self.factory.xfer = ThirdListing()
        self.calljson('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('', 5)
        self.assert_comp_equal(('SELECT', 'PRINT_MODE'), "3", (0, 2, 2, 1))
        self.assert_select_equal('PRINT_MODE', 3)
        self.assert_comp_equal(('SELECT', 'MODEL'), "5", (0, 3, 2, 1))
        self.assert_select_equal('MODEL', 1)  # nb=1
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = ThirdListing()
        self.calljson('/diacamma.accounting/thirdListing',
                      {'PRINT_MODE': '4', 'MODEL': 5}, False)
        self.assert_observer('core.print', 'diacamma.accounting', 'thirdListing')
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 20, str(content_csv))
        self.assertEqual(content_csv[1].strip()[:18], '"Liste de tiers - ')
        self.assertEqual(content_csv[6].strip(), '"contact";"compte";"total";')
        self.assertEqual(content_csv[7].strip(), '"Dalton Avrel";"401";"0,00 €";')
        self.assertEqual(content_csv[8].strip(), '"Dalton Jack";"411";"0,00 €";')
        self.assertEqual(content_csv[9].strip(), '"Dalton Joe";"411";"0,00 €";')
        self.assertEqual(content_csv[10].strip(), '"Dalton William";"411";"-125,97 €";')
        self.assertEqual(content_csv[11].strip(), '"Luke Lucky";"411,401";"0,00 €";')
        self.assertEqual(content_csv[12].strip(), '"Maximum";"401";"78,24 €";')
        self.assertEqual(content_csv[13].strip(), '"Minimum";"411,401";"-34,01 €";')

        self.factory.xfer = ThirdListing()
        self.calljson('/diacamma.accounting/thirdListing', {'PRINT_MODE': '4', 'MODEL': 5, 'filter': 'joe'}, False)
        self.assert_observer('core.print', 'diacamma.accounting', 'thirdListing')
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 14, str(content_csv))
        self.assertEqual(content_csv[1].strip()[:18], '"Liste de tiers - ')
        self.assertEqual(content_csv[6].strip(), '"contact";"compte";"total";', str(content_csv))
        self.assertEqual(content_csv[7].strip(), '"Dalton Joe";"411";"0,00 €";', str(content_csv))

        self.factory.xfer = ThirdListing()
        self.calljson('/diacamma.accounting/thirdListing', {'PRINT_MODE': '4', 'MODEL': 5, 'show_filter': '2'}, False)
        self.assert_observer('core.print', 'diacamma.accounting', 'thirdListing')
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 16, str(content_csv))
        self.assertEqual(content_csv[1].strip()[:18], '"Liste de tiers - ')
        self.assertEqual(content_csv[6].strip(), '"contact";"compte";"total";', str(content_csv))
        self.assertEqual(content_csv[7].strip(), '"Dalton William";"411";"-125,97 €";', str(content_csv))
        self.assertEqual(content_csv[8].strip(), '"Maximum";"401";"78,24 €";', str(content_csv))
        self.assertEqual(content_csv[9].strip(), '"Minimum";"411,401";"-34,01 €";', str(content_csv))

    def test_list_disable(self):
        fill_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)
        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'show_filter': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 7)

        self.factory.xfer = ThirdDisable()
        self.calljson('/diacamma.accounting/thirdDisable', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdDisable')
        self.assert_count_equal('', 2)

        self.factory.xfer = ThirdDisable()
        self.calljson('/diacamma.accounting/thirdDisable', {'limit_date': '2015-02-18'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdDisable')

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'show_filter': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 4)

    def test_with_customize(self):
        CustomField.objects.create(modelname='accounting.Third', name='categorie', kind=4, args="{'list':['---','petit','moyen','gros']}")
        CustomField.objects.create(modelname='accounting.Third', name='value', kind=1, args="{'min':0,'max':100}")
        create_third([3])
        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assertEqual(len(self.json_actions), 3)
        self.assertTrue('__tab_1' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 10 + 4 + 2)
        self.assert_json_equal('LABELFORM', 'contact', 'Dalton William')
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_grid_equal('accountthird', {'code': "code", 'total_txt': "total"}, 0)  # nb=2
        self.assert_json_equal('LABELFORM', 'total', 0.0)
        self.assert_json_equal('', '#total/formatnum', "C2EUR")
        self.assert_json_equal('', '#total/formatstr', "{[p align='right']}%s{[/p]}")

        self.assert_json_equal('LABELFORM', 'custom_1', 0)
        self.assert_json_equal('', '#custom_1/formatnum', {'0': '---', '1': 'petit', '2': 'moyen', '3': 'gros'})
        self.assert_json_equal('LABELFORM', 'custom_2', "0")
        self.assert_json_equal('', '#custom_2/formatnum', "N0")

        self.factory.xfer = ThirdEdit()
        self.calljson('/diacamma.accounting/thirdEdit', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdEdit')
        self.assert_count_equal('', 2 + 2)
        self.assert_json_equal('LABELFORM', 'contact', 'Dalton William')
        self.assert_json_equal('SELECT', 'custom_1', "0")
        self.assert_select_equal('custom_1', 4)  # nb=4
        self.assert_json_equal('FLOAT', 'custom_2', "0")

        self.factory.xfer = ThirdEdit()
        self.calljson('/diacamma.accounting/thirdEdit', {"third": 1, 'custom_1': '2', 'custom_2': '27', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'thirdEdit')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_json_equal('LABELFORM', 'contact', 'Dalton William')
        self.assert_json_equal('LABELFORM', 'custom_1', 2)
        self.assert_json_equal('LABELFORM', 'custom_2', 27)

        my_third = Third.objects.get(id=1)
        self.assertEqual(2, my_third.get_custom_by_name("categorie"))
        self.assertEqual(27, my_third.get_custom_by_name("value"))
        self.assertEqual(None, my_third.get_custom_by_name("truc"))

    def test_search(self):
        CustomField.objects.create(modelname='accounting.Third', name='categorie', kind=4, args="{'list':['---','petit','moyen','gros']}")
        CustomField.objects.create(modelname='accounting.Third', name='value', kind=1, args="{'min':0,'max':100}")
        search_field_list = Third.get_search_fields()
        self.assertEqual(3 + 8 + 2 + 2 + 5, len(search_field_list), search_field_list)

        fill_thirds_fr()
        self.factory.xfer = ThirdSearch()
        self.calljson('/diacamma.accounting/thirdSearch', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdSearch')
        self.assert_count_equal('third', 7)

    def test_print_model(self):
        CustomField.objects.create(modelname='accounting.Third', name='categorie', kind=4, args="{'list':['---','petit','moyen','gros']}")
        CustomField.objects.create(modelname='accounting.Third', name='value', kind=1, args="{'min':0,'max':100}")
        print_field_list = Third.get_all_print_fields()
        self.assertEqual(13, len(print_field_list), print_field_list)

    def test_merge_contact(self):
        fill_thirds_fr()

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 7)
        self.assert_json_equal('', 'third/@0/contact', 'Dalton Avrel')
        self.assert_json_equal('', 'third/@1/contact', 'Dalton Jack')
        self.assert_json_equal('', 'third/@2/contact', 'Dalton Joe')
        self.assert_json_equal('', 'third/@3/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@4/contact', 'Luke Lucky')
        self.assert_json_equal('', 'third/@5/contact', 'Maximum')
        self.assert_json_equal('', 'third/@6/contact', 'Minimum')

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 5)
        self.assert_json_equal('', 'individual/@0/id', 2)
        self.assert_json_equal('', 'individual/@0/firstname', 'Avrel')
        self.assert_json_equal('', 'individual/@0/lastname', 'Dalton')
        self.assert_json_equal('', 'individual/@1/id', 4)
        self.assert_json_equal('', 'individual/@1/firstname', 'Jack')
        self.assert_json_equal('', 'individual/@1/lastname', 'Dalton')
        self.assert_json_equal('', 'individual/@2/id', 5)
        self.assert_json_equal('', 'individual/@2/firstname', 'Joe')
        self.assert_json_equal('', 'individual/@2/lastname', 'Dalton')
        self.assert_json_equal('', 'individual/@3/id', 3)
        self.assert_json_equal('', 'individual/@3/firstname', 'William')
        self.assert_json_equal('', 'individual/@3/lastname', 'Dalton')
        self.assert_json_equal('', 'individual/@4/id', 6)
        self.assert_json_equal('', 'individual/@4/firstname', 'Lucky')
        self.assert_json_equal('', 'individual/@4/lastname', 'Luke')

        self.factory.xfer = ObjectMerge()
        self.calljson('/CORE/objectMerge', {'modelname': 'contacts.Individual', 'field_id': 'individual',
                                            'individual': '2;3;4;5', 'CONFIRME': 'YES', 'mrg_object': '3'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'objectMerge')

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 2)
        self.assert_json_equal('', 'individual/@0/firstname', 'William')
        self.assert_json_equal('', 'individual/@0/lastname', 'Dalton')
        self.assert_json_equal('', 'individual/@1/firstname', 'Lucky')
        self.assert_json_equal('', 'individual/@1/lastname', 'Luke')

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_count_equal('third', 4)
        self.assert_json_equal('', 'third/@0/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@1/contact', 'Luke Lucky')
        self.assert_json_equal('', 'third/@2/contact', 'Maximum')
        self.assert_json_equal('', 'third/@3/contact', 'Minimum')


class AdminTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)

    def test_format(self):
        self.assertEqual(format_with_devise(0), "C2EUR;{[p align='right']}%s{[/p]};;")
        self.assertEqual(format_with_devise(1), "C2EUR;{[p align='right']}Crédit: %s{[/p]};{[p align='right']}Débit: %s{[/p]};{[p align='right']}%s{[/p]}")
        self.assertEqual(format_with_devise(2), "C2EUR;{[p align='right']}{[font color=\"green\"]}Crédit: %s{[/font]}{[/p]};{[p align='right']}{[font color=\"blue\"]}Débit: %s{[/font]}{[/p]};{[p align='right']}%s{[/p]}")
        self.assertEqual(format_with_devise(3), "N2;%s")
        self.assertEqual(format_with_devise(4), "C2EUR;{[p align='right']}%s{[/p]};{[p align='right']}%s{[/p]}")
        self.assertEqual(format_with_devise(5), "C2EUR;{[p align='right']}%s{[/p]}")
        self.assertEqual(format_with_devise(6), "C2EUR;{[p align='right']}{[font color=\"green\"]}%s{[/font]}{[/p]};{[p align='right']}{[font color=\"blue\"]}%s{[/font]}{[/p]};")
        self.assertEqual(format_with_devise(7), "C2EUR")

    def test_summary(self):
        self.factory.xfer = StatusMenu()
        self.calljson('/CORE/statusMenu', {}, False)
        self.assert_observer('core.custom', 'CORE', 'statusMenu')
        self.assert_json_equal('LABELFORM', 'accountingtitle', "Gestion comptable")
        self.assert_json_equal('LABELFORM', 'accounting_error', "Pas d'exercice défini !")
        self.assert_action_equal('GET', '#accounting_conf/action',
                                 ("conf.", None, 'diacamma.accounting', 'configuration', 0, 1, 1))

    def test_default_configuration(self):
        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assertTrue('__tab_5' in self.json_data.keys(), self.json_data.keys())
        self.assertFalse('__tab_6' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 4 + 5 + 2 + 8 + 3)
        self.assert_grid_equal('fiscalyear', {"begin": "début", "end": "fin", "status": "statut", "is_actif": "actif", "prefix": "prefix"}, 0)  # nb=4

        self.assert_grid_equal('journal', {'name': "nom", "is_default": "défaut"}, 5)  # nb=1
        self.assert_json_equal('', 'journal/@0/name', 'Report-à-nouveau')
        self.assert_json_equal('', 'journal/@0/is_default', False)
        self.assert_json_equal('', 'journal/@1/name', 'Achats')
        self.assert_json_equal('', 'journal/@1/is_default', False)
        self.assert_json_equal('', 'journal/@2/name', 'Ventes')
        self.assert_json_equal('', 'journal/@2/is_default', False)
        self.assert_json_equal('', 'journal/@3/name', 'Règlements')
        self.assert_json_equal('', 'journal/@3/is_default', True)
        self.assert_json_equal('', 'journal/@4/name', 'Opérations diverses')
        self.assert_json_equal('', 'journal/@4/is_default', False)

        self.assert_json_equal('LABELFORM', 'accounting-devise-iso', 'Euro Member Countries (EUR / €)')
        self.assert_json_equal('LABELFORM', 'accounting-devise-prec', '2')
        self.assert_json_equal('LABELFORM', 'accounting-VAT-arrangements', 'Non applicable')
        self.assert_json_equal('LABELFORM', 'accounting-sizecode', '3')
        self.assert_json_equal('LABELFORM', 'accounting-needcost', 'Non')
        self.assert_json_equal('LABELFORM', 'accounting-code-report-filter', '')
        self.assert_grid_equal('custom_field', {'name': "nom", 'kind_txt': "type"}, 0)  # nb=2

        self.factory.xfer = ParamEdit()
        self.calljson('/CORE/paramEdit', {'params': 'accounting-devise-iso'}, False)
        self.assert_observer('core.custom', 'CORE', 'paramEdit')
        self.assert_json_equal('SELECT', 'accounting-devise-iso', 'EUR')
        self.assert_select_equal('accounting-devise-iso', 162)

    def test_configuration_accountsystem(self):
        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_select_equal('account_system', {
            '': '---',
            'diacamma.accounting.system.french.FrenchSystemAcounting': 'Plan comptable générale Français',
            'diacamma.accounting.system.belgium.BelgiumSystemAcounting': 'Plan comptable Belge',
            'diacamma.accounting.system.morocco.MoroccoSystemAcounting': 'Plan comptable Marocain'
        })

        self.factory.xfer = ConfigurationAccountingSystem()
        self.calljson('/diacamma.accounting/configurationAccountingSystem', {'account_system': 'diacamma.accounting.system.french.FrenchSystemAcounting'}, False)
        self.assert_observer('core.dialogbox', 'diacamma.accounting', 'configurationAccountingSystem')

        self.factory.xfer = ConfigurationAccountingSystem()
        self.calljson('/diacamma.accounting/configurationAccountingSystem', {'account_system': 'diacamma.accounting.system.french.FrenchSystemAcounting', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'configurationAccountingSystem')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_json_equal('LABELFORM', 'account_system', 'Plan comptable générale Français')

    def test_configuration_journal(self):
        self.factory.xfer = JournalAddModify()
        self.calljson('/diacamma.accounting/journalAddModify', {'journal': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'journalAddModify')
        self.assert_count_equal('', 2)
        self.assert_json_equal('EDIT', 'name', 'Achats')

        self.factory.xfer = JournalAddModify()
        self.calljson('/diacamma.accounting/journalAddModify', {'SAVE': 'YES', 'journal': '2', 'name': 'Dépense'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'journalAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('journal', 5)
        self.assert_json_equal('', 'journal/@1/id', 2)
        self.assert_json_equal('', 'journal/@1/name', 'Dépense')

        self.factory.xfer = JournalAddModify()
        self.calljson('/diacamma.accounting/journalAddModify', {'SAVE': 'YES', 'name': 'Caisse'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'journalAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('journal', 6)
        self.assert_json_equal('', 'journal/@5/id', '6')
        self.assert_json_equal('', 'journal/@5/name', 'Caisse')

        self.factory.xfer = JournalDel()
        self.calljson('/diacamma.accounting/journalDel', {'journal': '2'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'journalDel')
        self.assert_json_equal('', 'message', 'journal réservé !')

        self.factory.xfer = JournalDel()
        self.calljson('/diacamma.accounting/journalDel', {'CONFIRME': 'YES', 'journal': '6'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'journalDel')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('journal', 5)
        self.assert_json_equal('', 'journal/@0/is_default', False)
        self.assert_json_equal('', 'journal/@1/is_default', False)
        self.assert_json_equal('', 'journal/@2/is_default', False)
        self.assert_json_equal('', 'journal/@3/is_default', True)
        self.assert_json_equal('', 'journal/@4/is_default', False)

        self.factory.xfer = JournalDefault()
        self.calljson('/diacamma.accounting/journalDefault', {'journal': '2'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'journalDefault')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('journal', 5)
        self.assert_json_equal('', 'journal/@0/is_default', False)
        self.assert_json_equal('', 'journal/@1/is_default', True)
        self.assert_json_equal('', 'journal/@2/is_default', False)
        self.assert_json_equal('', 'journal/@3/is_default', False)
        self.assert_json_equal('', 'journal/@4/is_default', False)

        self.factory.xfer = JournalDefault()
        self.calljson('/diacamma.accounting/journalDefault', {'journal': '2'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'journalDefault')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('journal', 5)
        self.assert_json_equal('', 'journal/@0/is_default', False)
        self.assert_json_equal('', 'journal/@1/is_default', False)
        self.assert_json_equal('', 'journal/@2/is_default', False)
        self.assert_json_equal('', 'journal/@3/is_default', False)
        self.assert_json_equal('', 'journal/@4/is_default', False)

    def test_configuration_fiscalyear(self):
        to_day = date.today()
        try:
            to_day_plus_1 = date(to_day.year + 1, to_day.month, to_day.day) - timedelta(days=1)
        except ValueError:
            to_day_plus_1 = date(to_day.year + 1, to_day.month, to_day.day - 1)

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_json_equal('', 'message', "Système comptable non défini !")

        set_accounting_system()

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_count_equal('', 6)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('DATE', 'begin', to_day.isoformat())
        self.assert_json_equal('DATE', 'end', to_day_plus_1.isoformat())
        self.assert_json_equal('EDIT', 'prefix', 'A')
        self.assert_select_equal('init_account', {0: 'Blanc', 1: 'Initiaux'})
        self.assert_json_equal('SELECT', 'init_account', 1)

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {'SAVE': 'YES', 'begin': '2015-07-01', 'end': '2016-06-30', 'prefix': '2015-2016'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_grid_equal('fiscalyear', {"begin": "début", "end": "fin", "status": "statut", "is_actif": "actif", "prefix": "prefix"}, 1)  # nb=4

        self.assert_json_equal('', '#fiscalyear/headers/@2/@0', 'status')
        self.assert_json_equal('', '#fiscalyear/headers/@2/@1', 'statut')
        self.assert_json_equal('', '#fiscalyear/headers/@2/@2', {'0': 'en création', '1': 'en cours', '2': 'terminé'})
        self.assert_json_equal('', '#fiscalyear/headers/@2/@4', "%s")

        self.assert_json_equal('', 'fiscalyear/@0/begin', '2015-07-01')
        self.assert_json_equal('', 'fiscalyear/@0/end', '2016-06-30')
        self.assert_json_equal('', 'fiscalyear/@0/status', 0)
        self.assert_json_equal('', 'fiscalyear/@0/is_actif', True)
        self.assert_json_equal('', 'fiscalyear/@0/prefix', '2015-2016')

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_count_equal('', 6)
        self.assertEqual(self.json_context['begin'], "2016-07-01")
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'begin', '2016-07-01')
        self.assert_json_equal('DATE', 'end', '2017-06-30')
        self.assert_json_equal('EDIT', 'prefix', 'B')
        self.assert_select_equal('init_account', {0: 'Blanc', 1: 'Initiaux', 2: 'Import'})
        self.assert_json_equal('SELECT', 'init_account', 2)

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {'SAVE': 'YES', 'begin': '2016-07-01', 'end': '2017-06-30'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('fiscalyear', 2)
        self.assert_json_equal('', 'fiscalyear/@0/begin', '2016-07-01')
        self.assert_json_equal('', 'fiscalyear/@0/end', '2017-06-30')
        self.assert_json_equal('', 'fiscalyear/@0/status', 0)
        self.assert_json_equal('', 'fiscalyear/@0/is_actif', False)
        self.assert_json_equal('', 'fiscalyear/@0/prefix', 'B')

        self.factory.xfer = FiscalYearActive()
        self.calljson('/diacamma.accounting/fiscalYearActive', {'fiscalyear': '2'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearActive')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('fiscalyear', 2)
        self.assert_json_equal('', 'fiscalyear/@1/is_actif', False)
        self.assert_json_equal('', 'fiscalyear/@0/is_actif', True)

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {'fiscalyear': '1'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_json_equal('', 'message', "Cet exercice n'est pas le dernier !")

        self.factory.xfer = FiscalYearAddModify()
        self.calljson('/diacamma.accounting/fiscalYearAddModify', {'fiscalyear': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_count_equal('', 6)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'begin', '2016-07-01')
        self.assert_json_equal('DATE', 'end', '2017-06-30')
        self.assert_json_equal('SELECT', 'folder', 2)
        self.assert_json_equal('EDIT', 'prefix', 'B')

    def test_confi_delete(self):
        year1 = FiscalYear.objects.create(begin='2014-07-01', end='2015-06-30', status=2, is_actif=False, last_fiscalyear=None)
        year2 = FiscalYear.objects.create(begin='2015-07-01', end='2016-06-30', status=1, is_actif=False, last_fiscalyear=year1)
        FiscalYear.objects.create(begin='2016-07-01', end='2017-06-30', status=0,
                                  is_actif=True, last_fiscalyear=year2)
        set_accounting_system()
        initial_thirds_fr()
        fill_accounts_fr()
        fill_entries_fr(3)

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('fiscalyear', 3)

        self.factory.xfer = FiscalYearDel()
        self.calljson(
            '/diacamma.accounting/fiscalYearDel', {'fiscalyear': '1'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearDel')
        self.assert_json_equal('', 'message', "Cet exercice n'est pas le dernier !")

        self.factory.xfer = FiscalYearDel()
        self.calljson('/diacamma.accounting/fiscalYearDel', {'fiscalyear': '2'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearDel')
        self.assert_json_equal('', 'message', "Cet exercice n'est pas le dernier !")

        self.factory.xfer = FiscalYearDel()
        self.calljson('/diacamma.accounting/fiscalYearDel', {'CONFIRME': 'YES', 'fiscalyear': '3'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearDel')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('fiscalyear', 2)

        self.factory.xfer = FiscalYearDel()
        self.calljson('/diacamma.accounting/fiscalYearDel',
                      {'CONFIRME': 'YES', 'fiscalyear': '2'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearDel')

        self.factory.xfer = FiscalYearDel()
        self.calljson('/diacamma.accounting/fiscalYearDel', {'CONFIRME': 'YES', 'fiscalyear': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearDel')

    def test_system_accounting(self):
        clear_system_account()
        self.assertEqual(get_accounting_system('').__class__.__name__, "DefaultSystemAccounting")
        self.assertEqual(get_accounting_system('accountingsystem.foo.DummySystemAcounting').__class__.__name__, "DefaultSystemAccounting")
        self.assertEqual(get_accounting_system('diacamma.accounting.system.french.DummySystemAcounting').__class__.__name__, "DefaultSystemAccounting")
        self.assertEqual(get_accounting_system('diacamma.accounting.system.french.FrenchSystemAcounting').__class__.__name__, "FrenchSystemAcounting")
        self.assertEqual(get_accounting_system('diacamma.accounting.system.belgium.BelgiumSystemAcounting').__class__.__name__, "BelgiumSystemAcounting")
        self.assertEqual(accounting_system_ident('diacamma.accounting.system.french.DummySystemAcounting'), "---")
        self.assertEqual(accounting_system_ident('diacamma.accounting.system.french.FrenchSystemAcounting'), "french")
        self.assertEqual(accounting_system_ident('diacamma.accounting.system.belgium.BelgiumSystemAcounting'), "belgium")

        self.assertEqual(Params.getvalue("accounting-system"), "")
        self.assertEqual(current_system_account().__class__.__name__, "DefaultSystemAccounting")
        set_accounting_system()
        self.assertEqual(current_system_account().__class__.__name__, "FrenchSystemAcounting")

    def test_configuration_customfield(self):
        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('custom_field', 0)
        self.assert_count_equal('#custom_field/actions', 4)

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'aaa', 'modelname': 'accounting.Third', 'kind': '0', 'args_multi': 'n', 'args_min': '0', 'args_max': '0', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('custom_field', 1)

    @staticmethod
    def mocked_requests_request(*args, **kwargs):
        class MockResponse:
            def __init__(self, content, status_code):
                self.content = content
                self.status_code = status_code

            def json(self):
                return loads(self.content)

            def raise_for_status(self):
                pass

        if args[1] == 'https://api.superpdp.tech/afnor-flow':
            return MockResponse("", 200)
        elif args[1] == 'https://api.superpdp.tech/oauth2/token':
            return MockResponse('{"access_token": "AzerTy123456"}', 200)

        return MockResponse(None, 404)

    @mock.patch('diacamma.accounting.einvoicing_flow.request', side_effect=mocked_requests_request)
    def test_einvoicing(self, mock_request):
        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('', 4 + 5 + 2 + 8 + 3)

        self.assert_json_equal('SELECT', 'einvoice_type', 0)
        self.assert_json_equal('BUTTON', 'save-einvoice', '')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {"einvoice_type": 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('', 4 + 5 + 2 + 8 + 9)

        self.assert_json_equal('SELECT', 'einvoice_type', 1)
        self.assert_json_equal('EDIT', 'flow_url', 'https://api.superpdp.tech/afnor-flow')
        self.assert_json_equal('EDIT', 'directory_url', 'https://api.superpdp.tech/afnor-directory')
        self.assert_json_equal('EDIT', 'auth_url', 'https://api.superpdp.tech/oauth2/token')
        self.assert_json_equal('EDIT', 'client_id', '')
        self.assert_json_equal('PASSWD', 'secret_id', '')
        self.assert_json_equal('BUTTON', 'save-einvoice', '')
        self.assert_json_equal('LABELFORM', 'resutl-check', '')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {"einvoice_type": 1,
                                                             'flow_url': 'https://api.superpdp.tech/afnor-flow',
                                                             'directory_url': 'https://api.superpdp.tech/afnor-directory',
                                                             'auth_url': 'https://api.superpdp.tech/oauth2/token',
                                                             'client_id': 'MyClientID',
                                                             'secret_id': 'WOnd3rfu11+P@ssw0rd',
                                                             'SAVE': 'OK'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')

        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('', 4 + 5 + 2 + 8 + 10)
        self.assert_json_equal('SELECT', 'einvoice_type', 1)
        self.assert_json_equal('EDIT', 'flow_url', 'https://api.superpdp.tech/afnor-flow')
        self.assert_json_equal('EDIT', 'directory_url', 'https://api.superpdp.tech/afnor-directory')
        self.assert_json_equal('EDIT', 'auth_url', 'https://api.superpdp.tech/oauth2/token')
        self.assert_json_equal('EDIT', 'client_id', 'MyClientID')
        self.assert_json_equal('PASSWD', 'secret_id', 'WOnd3rfu11+P@ssw0rd')
        self.assert_json_equal('BUTTON', 'save-einvoice', '')
        self.assert_json_equal('BUTTON', 'check-einvoice', '')
        self.assert_json_equal('LABELFORM', 'resutl-check', '')

        self.assertEqual(len(mock_request.call_args_list), 0)
        self.factory.xfer = Configuration()
        self.calljson('/diacamma.accounting/configuration', {"CHECK": "OK"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'configuration')
        self.assert_json_equal('LABELFORM', 'resutl-check', 'Connexion réussi')
        self.assertEqual(len(mock_request.call_args_list), 4)
        self.assertEqual(mock.call('POST', 'https://api.superpdp.tech/oauth2/token',
                                   data={"grant_type": "client_credentials", "client_id": 'MyClientID', "client_secret": 'WOnd3rfu11+P@ssw0rd'}),
                         mock_request.call_args_list[0])
        self.assertEqual(mock.call('GET', 'https://api.superpdp.tech/afnor-flow/v1/healthcheck',
                                   headers={'Accept': 'application/json', "Authorization": "Bearer AzerTy123456"},
                                   params=None, json=None, data=None, files=None),
                         mock_request.call_args_list[1])
        self.assertEqual(mock.call('POST', 'https://api.superpdp.tech/oauth2/token',
                                   data={"grant_type": "client_credentials", "client_id": 'MyClientID', "client_secret": 'WOnd3rfu11+P@ssw0rd'}),
                         mock_request.call_args_list[2])
        self.assertEqual(mock.call('GET', 'https://api.superpdp.tech/afnor-directory/v1/healthcheck',
                                   headers={'Accept': 'application/json', "Authorization": "Bearer AzerTy123456"},
                                   params=None, json=None, data=None, files=None),
                         mock_request.call_args_list[3])


class ModelTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        initial_thirds_fr()
        rmtree(get_user_dir(), True)
        clear_system_account()
        default_compta_fr()

    def test_add(self):
        self.factory.xfer = ModelEntryList()
        self.calljson('/diacamma.accounting/modelEntryList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelEntryList')
        self.assert_count_equal('', 3)
        self.assert_grid_equal('modelentry', {'journal': "journal", 'designation': "nom", "costaccounting": "comptabilité analytique", 'total': "total"}, 0)  # nb=3

        self.factory.xfer = ModelEntryAddModify()
        self.calljson('/diacamma.accounting/modelEntryAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelEntryAddModify')
        self.assert_count_equal('', 4)
        self.assert_select_equal('journal', 4)  # nb=4
        self.assert_select_equal('costaccounting', 1)  # nb=1

        self.factory.xfer = ModelEntryAddModify()
        self.calljson('/diacamma.accounting/modelEntryAddModify', {'SAVE': 'YES', 'journal': '2', 'designation': 'foo'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'modelEntryAddModify')

        self.factory.xfer = ModelEntryList()
        self.calljson('/diacamma.accounting/modelEntryList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelEntryList')
        self.assert_count_equal('', 3)
        self.assert_grid_equal('modelentry', {'journal': "journal", 'designation': "nom", "costaccounting": "comptabilité analytique", 'total': "total"}, 1)  # nb=3
        self.assert_json_equal('', 'modelentry/@0/journal', "Achats")
        self.assert_json_equal('', 'modelentry/@0/designation', "foo")
        self.assert_json_equal('', 'modelentry/@0/total', 0.0)

    def test_addline(self):
        self.factory.xfer = ModelEntryAddModify()
        self.calljson('/diacamma.accounting/modelEntryAddModify', {'SAVE': 'YES', 'journal': '2', 'designation': 'foo'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'modelEntryAddModify')

        self.factory.xfer = ModelLineEntryAddModify()
        self.calljson('/diacamma.accounting/modelLineEntryAddModify',
                      {'modelentry': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelLineEntryAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code_txt', '')
        self.assert_json_equal('SELECT', 'code', '')
        self.assert_select_equal('code', 0)
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')

        self.factory.xfer = ModelLineEntryAddModify()
        self.calljson('/diacamma.accounting/modelLineEntryAddModify',
                      {'modelentry': '1', 'code_txt': '411'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelLineEntryAddModify')
        self.assert_count_equal('', 7)
        self.assert_json_equal('EDIT', 'code_txt', '411')
        self.assert_json_equal('SELECT', 'code', '411')
        self.assert_select_equal('code', {'411': '[411] 411'})
        self.assert_json_equal('SELECT', 'third', '0')
        self.assert_select_equal('third', 6)
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')
        self.assert_json_equal('BUTTON', 'new-third', '')
        self.assert_action_equal('POST', '#new-third/action', ('Créer', 'mdi:mdi-pencil-plus', 'diacamma.accounting', 'thirdAdd', 0, 1, 1, {'new_account': '411'}))

        self.factory.xfer = ModelLineEntryAddModify()
        self.calljson('/diacamma.accounting/modelLineEntryAddModify',
                      {'SAVE': 'YES', 'model': '1', 'modelentry': '1', 'code_txt': '411', 'code': '411', 'third': '3', 'credit_val': '19.37', 'debit_val': '0.0'}, False)

        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'modelLineEntryAddModify')

        self.factory.xfer = ModelEntryList()
        self.calljson('/diacamma.accounting/modelEntryList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelEntryList')
        self.assert_count_equal('', 3)
        self.assert_grid_equal('modelentry', {'journal': "journal", 'designation': "nom", "costaccounting": "comptabilité analytique", 'total': "total"}, 1)  # nb=3

        self.assert_json_equal('', '#modelentry/headers/@3/@0', 'total')
        self.assert_json_equal('', '#modelentry/headers/@3/@2', "C2EUR")
        self.assert_json_equal('', '#modelentry/headers/@3/@4', "{[p align='right']}%s{[/p]}")

        self.assert_json_equal('', 'modelentry/@0/journal', "Achats")
        self.assert_json_equal('', 'modelentry/@0/designation', "foo")
        self.assert_json_equal('', 'modelentry/@0/total', 19.37)

        self.factory.xfer = ModelEntryShow()
        self.calljson('/diacamma.accounting/modelEntryShow', {'modelentry': 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'modelEntryShow')
        self.assert_json_equal('LABELFORM', 'journal', "Achats")
        self.assert_json_equal('LABELFORM', 'designation', "foo")
        self.assert_json_equal('LABELFORM', 'total', 19.37)
        self.assert_grid_equal('modellineentry', {'code_txt': 'code', 'third': 'tiers', 'debit': 'débit', 'credit': 'crédit'}, 1)
        self.assert_json_equal('', '#modellineentry/headers/@2/@0', 'debit')
        self.assert_json_equal('', '#modellineentry/headers/@2/@2', "C2EUR")
        self.assert_json_equal('', '#modellineentry/headers/@2/@4', "{[p align='right']}%s{[/p]};;")
        self.assert_json_equal('', '#modellineentry/headers/@3/@0', 'credit')
        self.assert_json_equal('', '#modellineentry/headers/@3/@2', "C2EUR")
        self.assert_json_equal('', '#modellineentry/headers/@3/@4', "{[p align='right']}%s{[/p]};;")

        self.assert_json_equal('', 'modellineentry/@0/code_txt', "[411] 411")
        self.assert_json_equal('', 'modellineentry/@0/third', "Luke Lucky")
        self.assert_json_equal('', 'modellineentry/@0/debit', 0)
        self.assert_json_equal('', 'modellineentry/@0/credit', 19.37)

    def test_selector(self):
        add_models()
        self.factory.xfer = EntryAccountModelSelector()
        self.calljson('/diacamma.accounting/entryAccountModelSelector', {'year': 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountModelSelector')
        self.assert_count_equal('', 4)
        self.assert_select_equal('model', 3)  # nb=2
        self.assert_json_equal('DATE', 'date_value', '2015-12-31')
        self.assert_json_equal('FLOAT', 'factor', '1.00')

        self.factory.xfer = EntryAccountModelSelector()
        self.calljson('/diacamma.accounting/entryAccountModelSelector', {'year': 1, 'journal': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountModelSelector')
        self.assert_count_equal('', 4)
        self.assert_select_equal('model', 2)  # nb=1
        self.assert_json_equal('FLOAT', 'factor', '1.00')

    def test_selector_nodate(self):
        Params.setvalue('accounting-datecurrent', False)
        add_models()
        self.factory.xfer = EntryAccountModelSelector()
        self.calljson('/diacamma.accounting/entryAccountModelSelector', {'year': 1}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountModelSelector')
        self.assert_count_equal('', 4)
        self.assert_select_equal('model', 3)
        self.assert_json_equal('DATE', 'date_value', None)
        self.assert_json_equal('FLOAT', 'factor', '1.00')

    def test_insert(self):
        add_models()
        self.factory.xfer = EntryAccountModelSelector()
        self.calljson('/diacamma.accounting/entryAccountModelSelector', {'SAVE': 'YES', 'year': 1, 'journal': '2', 'date_value': '2015-10-21', 'model': 1, 'factor': 2.50}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountModelSelector')
        self.assertEqual(len(self.json_context), 4)
        self.assertEqual(self.json_context['year'], '1')
        self.assertEqual(self.json_context['entryaccount'], 1)
        self.assertEqual(self.json_context['journal'], '2')
        self.assertEqual(self.json_context['date_value'], '2015-10-21')
        self.assertEqual(self.response_json["action"]["id"], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(len(self.response_json["action"]["params"]), 1)
        serial_entry = self.response_json["action"]["params"]['serial_entry'].split('\n')
        self.assertEqual(serial_entry[0][-24:], "|1|3|48.430000|0|0|None|", serial_entry[0])
        self.assertEqual(serial_entry[1][-25:], "|2|0|-48.430000|0|0|None|", serial_entry[1])

    def test_insert_with_costaccounting(self):
        add_models()
        self.factory.xfer = EntryAccountModelSelector()
        self.calljson('/diacamma.accounting/entryAccountModelSelector', {'SAVE': 'YES', 'year': 1, 'journal': '2', 'date_value': '2015-10-21', 'model': 3, 'factor': 1.00}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountModelSelector')
        self.assertEqual(len(self.json_context), 4)
        self.assertEqual(self.json_context['year'], '1')
        self.assertEqual(self.json_context['entryaccount'], 1)
        self.assertEqual(self.json_context['journal'], '2')
        self.assertEqual(self.json_context['date_value'], '2015-10-21')
        self.assertEqual(self.response_json["action"]["id"], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(len(self.response_json["action"]["params"]), 1)
        serial_entry = self.response_json["action"]["params"]['serial_entry'].split('\n')
        self.assertEqual(serial_entry[0][-25:], "|1|3|-37.910000|0|0|None|", serial_entry[0])
        self.assertEqual(serial_entry[1][-25:], "|11|0|37.910000|2|0|None|", serial_entry[1])
