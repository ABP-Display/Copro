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
from datetime import date
from _io import StringIO

from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.CORE.parameters import Params

from diacamma.accounting.views_entries import EntryAccountList, \
    EntryAccountEdit, EntryAccountAfterSave, EntryLineAccountAdd, \
    EntryLineAccountEdit, EntryAccountValidate, EntryAccountClose, \
    EntryAccountReverse, EntryAccountCreateLinked, EntryAccountLink, \
    EntryAccountDel, EntryAccountOpenFromLine, EntryAccountShow, \
    EntryLineAccountDel, EntryAccountUnlock, EntryAccountImport
from diacamma.accounting.test_tools import default_compta_fr, initial_thirds_fr, \
    fill_entries_fr, default_costaccounting, fill_thirds_fr, fill_accounts_fr
from diacamma.accounting.models import EntryAccount, CostAccounting, FiscalYear
from diacamma.accounting.views_other import CostAccountingAddModify
from diacamma.accounting.views import ThirdShow
from diacamma.accounting.views_accounts import FiscalYearBegin, FiscalYearClose, \
    FiscalYearReportLastYear, ChartsAccountList


class EntryTest(LucteriosTest):

    def setUp(self):
        initial_thirds_fr()
        LucteriosTest.setUp(self)
        default_compta_fr()
        rmtree(get_user_dir(), True)

    def test_empty_list(self):
        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_json_equal('SELECT', 'year', '1')
        self.assert_select_equal('year', 1)  # nb=1
        self.assert_json_equal('SELECT', 'journal', '4')
        self.assert_select_equal('journal', 6)  # nb=6
        self.assert_json_equal('SELECT', 'filter', '1')
        self.assert_select_equal('filter', 5)  # nb=5
        self.assert_count_equal('entryline', 0)
        self.assert_json_equal('', '#entryline/headers/@5/@0', 'debit')
        self.assert_json_equal('', '#entryline/headers/@5/@2', 'C2EUR')
        self.assert_json_equal('', '#entryline/headers/@5/@4', '{[p align=\'right\']}{[font color="green"]}%s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}%s{[/font]}{[/p]};')
        self.assert_json_equal('', '#entryline/headers/@6/@0', 'credit')
        self.assert_json_equal('', '#entryline/headers/@6/@2', 'C2EUR')
        self.assert_json_equal('', '#entryline/headers/@6/@4', '{[p align=\'right\']}{[font color="green"]}%s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}%s{[/font]}{[/p]};')

        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 0.00, 0.00])

    def test_add_entry(self):
        Params.setvalue('accounting-datecurrent', False)
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'year': '1', 'journal': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 4)
        self.assert_json_equal('SELECT', 'journal', '2')
        self.assert_json_equal('DATE', 'date_value', None)
        self.assert_json_equal('EDIT', 'designation', '')
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountAfterSave")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['entryaccount'], 1)
        self.assertEqual(len(self.json_context), 4)
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")
        self.assertEqual(self.json_context['date_value'], "2015-02-13")
        self.assertEqual(self.json_context['designation'], "un plein cadie")

        self.factory.xfer = EntryAccountAfterSave()
        self.calljson('/diacamma.accounting/entryAccountAfterSave', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                     'date_value': '2015-02-13', 'designation': 'un plein cadie', 'entryaccount': "1"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountAfterSave')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(self.response_json['action']['params'], None)
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], "1")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")

    def test_add_entry_bad_date(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'year': '1', 'journal': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 4)
        self.assert_json_equal('SELECT', 'journal', '2')
        self.assert_json_equal('DATE', 'date_value', '2015-12-31')
        self.assert_json_equal('EDIT', 'designation', '')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2017-04-20', 'designation': 'Truc'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.assertEqual(self.response_json['action']['params']['entryaccount'], 1)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)
        self.assert_json_equal('SELECT', 'journal', '2')
        self.assert_json_equal('DATE', 'date_value', '2015-12-31')
        self.assert_json_equal('EDIT', 'designation', 'Truc')
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2010-04-20', 'designation': 'Machin'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.assertEqual(self.response_json['action']['params']['entryaccount'], 2)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)
        self.assert_json_equal('SELECT', 'journal', '2')
        self.assert_json_equal('DATE', 'date_value', '2015-01-01')
        self.assert_json_equal('EDIT', 'designation', 'Machin')
        self.assertEqual(len(self.json_actions), 2)

    def test_add_line_third(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)

        self.assert_json_equal('SELECT', 'journal', '2')
        self.assert_json_equal('DATE', 'date_value', '2015-02-13')
        self.assert_json_equal('EDIT', 'designation', 'un plein cadie')
        self.assert_count_equal('entrylineaccount_serial', 0)
        self.assert_json_equal('EDIT', 'num_cpt_txt', '')
        self.assert_json_equal('SELECT', 'num_cpt', 'None')
        self.assert_select_equal('num_cpt', 0)  # nb=0
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'num_cpt_txt': '401'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 17)

        self.assert_json_equal('EDIT', 'num_cpt_txt', '401')
        self.assert_json_equal('SELECT', 'num_cpt', '4')
        self.assert_select_equal('num_cpt', 1)  # nb=1
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assert_json_equal('SELECT', 'third', '0')
        self.assert_json_equal('BUTTON', 'new-third', '')
        self.assert_action_equal('POST', '#new-third/action', ('Créer', 'mdi:mdi-pencil-plus', 'diacamma.accounting', 'thirdAdd', 0, 1, 1, {'new_account': '401'}))
        self.assert_select_equal('third', 5)  # nb=5
        self.assert_count_equal('entrylineaccount_serial', 0)
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '2', 'entryaccount': '1', 'num_cpt_txt': '401',
                                                                   'num_cpt': '4', 'third': 0, 'debit_val': '0.0', 'credit_val': '152.34'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], "1")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)

        self.assert_count_equal('entrylineaccount_serial', 1)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/entry_account', '[401] 401')
        self.assert_json_equal('', 'entrylineaccount_serial/@0/debit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/credit', 152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/costaccounting', None)
        self.assertEqual(len(self.json_actions), 2)

    def test_add_line_revenue(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|", 'num_cpt_txt': '60'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 16)

        self.assert_count_equal('entrylineaccount_serial', 1)
        self.assert_json_equal('EDIT', 'num_cpt_txt', '60')
        self.assert_json_equal('SELECT', 'num_cpt', '11')
        self.assert_select_equal('num_cpt', 4)  # nb=4
        self.assert_json_equal('FLOAT', 'debit_val', '152.34')
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|",
                                                                   'num_cpt_txt': '60', 'num_cpt': '12', 'debit_val': '152.34', 'credit_val': '0.0'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], '1')
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|\n-2|12|0|152.340000|0|0|None|"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)

        self.assert_count_equal('entrylineaccount_serial', 2)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/entry_account', '[401] 401')
        self.assert_json_equal('', 'entrylineaccount_serial/@0/debit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/credit', 152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/entry_account', '[602] 602')
        self.assert_json_equal('', 'entrylineaccount_serial/@1/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/debit', -152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/credit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/reference', None)
        self.assertEqual(len(self.json_actions), 2)
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryAccountValidate")

    def test_add_line_payoff(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '3',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '3', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|", 'num_cpt_txt': '5'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 16)

        self.assert_count_equal('entrylineaccount_serial', 1)
        self.assert_json_equal('EDIT', 'num_cpt_txt', '5')
        self.assert_json_equal('SELECT', 'num_cpt', '2')
        self.assert_select_equal('num_cpt', 2)  # nb=2
        self.assert_json_equal('FLOAT', 'debit_val', '152.34')
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assert_json_equal('EDIT', 'reference', '')
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '3', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|",
                                                                   'num_cpt_txt': '5', 'num_cpt': '3', 'debit_val': '152.34', 'credit_val': '0.0', 'reference': 'aaabbb'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], '1')
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "3")

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-1|4|0|152.340000|0|0|None|\n-2|3|0|152.340000|0|0|aaabbb|"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)

        self.assert_count_equal('entrylineaccount_serial', 2)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/entry_account', '[401] 401')
        self.assert_json_equal('', 'entrylineaccount_serial/@0/debit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/credit', 152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/costaccounting', None)

        self.assert_json_equal('', 'entrylineaccount_serial/@1/entry_account', '[531] 531')
        self.assert_json_equal('', 'entrylineaccount_serial/@1/debit', -152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/credit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/reference', 'aaabbb')
        self.assert_json_equal('', 'entrylineaccount_serial/@1/costaccounting', None)
        self.assertEqual(len(self.json_actions), 2)
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryAccountValidate")

    def test_change_line_third(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryLineAccountEdit()
        self.calljson('/diacamma.accounting/entryLineAccountEdit', {'year': '1', 'journal': '2', 'entryaccount': '1',
                                                                    'serial_entry': "-1|4|0|152.340000|0|0|None|\n-2|12|0|152.340000|0|0|None|", 'entrylineaccount_serial': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryLineAccountEdit')
        self.assert_count_equal('', 6)

        self.assert_json_equal('LABELFORM', 'account', '[401] 401')
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')
        self.assert_json_equal('FLOAT', 'credit_val', '152.34')
        self.assert_json_equal('SELECT', 'third', '0')
        self.assert_json_equal('BUTTON', 'new-third', '')
        self.assert_action_equal('POST', '#new-third/action', ('Créer', 'mdi:mdi-pencil-plus', 'diacamma.accounting', 'thirdAdd', 0, 1, 1, {'new_account': '401'}))

        self.assert_select_equal('third', 5)  # nb=5
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryLineAccountAdd")
        self.assertEqual(len(self.json_actions[0]['params']), 1)
        self.assertEqual(self.json_actions[0]['params']['num_cpt'], 4)

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '2', 'entryaccount': '1',
                                                                   'serial_entry': "-1|4|0|152.340000|0|0|None|\n-2|12|0|152.340000|0|0|None|", 'debit_val': '0.0',
                                                                   'credit_val': '152.34', 'entrylineaccount_serial': '-1', 'third': '3', 'num_cpt': '4'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], '1')
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-2|12|0|152.340000|0|0|None|\n-3|4|3|152.340000|0|0|None|"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)

        self.assert_count_equal('entrylineaccount_serial', 2)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/entry_account', '[602] 602')
        self.assert_json_equal('', 'entrylineaccount_serial/@0/debit', -152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/credit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entrylineaccount_serial/@1/debit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/credit', 152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/costaccounting', None)
        self.assertEqual(len(self.json_actions), 2)
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryAccountValidate")

        self.factory.xfer = EntryLineAccountEdit()
        self.calljson('/diacamma.accounting/entryLineAccountEdit', {'year': '1', 'journal': '2', 'entryaccount': '1',
                                                                    'serial_entry': "-1|4|3|152.340000|0|0|None|\n-2|12|0|152.340000|0|0|None|", 'entrylineaccount_serial': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryLineAccountEdit')
        self.assert_count_equal('', 6)

        self.assert_json_equal('LABELFORM', 'account', '[401] 401')
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')
        self.assert_json_equal('FLOAT', 'credit_val', '152.34')
        self.assert_json_equal('SELECT', 'third', '3')
        self.assert_json_equal('BUTTON', 'new-third', '')
        self.assert_select_equal('third', 5)  # nb=5
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryLineAccountAdd")
        self.assertEqual(len(self.json_actions[0]['params']), 1)
        self.assertEqual(self.json_actions[0]['params']['num_cpt'], 4)

    def test_edit_line(self):
        CostAccounting.objects.create(name='close', description='Close cost', status=1, is_default=False)
        CostAccounting.objects.create(name='open', description='Open cost', status=0, is_default=True)
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-1|4|2|87.230000|0|0|None|\n-2|11|0|87.230000|2|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryLineAccountEdit()
        self.calljson('/diacamma.accounting/entryLineAccountEdit', {'year': 1, 'debit_val': 0, 'date_value': '2015-02-13', 'num_cpt_txt': '', 'credit_val': 0,
                                                                    'entrylineaccount_serial': -2,
                                                                    'serial_entry': '-1|4|2|87.230000|0|0|None|\n-2|11|0|87.230000|2|0|None|',
                                                                    'journal': 2, 'designation': 'un plein cadie', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryLineAccountEdit')
        self.assert_count_equal('', 5)
        self.assert_json_equal('LABELFORM', 'account', '[601] 601')
        self.assert_json_equal('FLOAT', 'debit_val', '87.23')
        self.assert_json_equal('FLOAT', 'credit_val', '0')
        self.assert_json_equal('SELECT', 'costaccounting', '2')
        self.assert_select_equal('costaccounting', 2)  # nb=2
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryLineAccountAdd")
        self.assertEqual(len(self.json_actions[0]['params']), 1)
        self.assertEqual(self.json_actions[0]['params']['num_cpt'], 11)

    def test_change_line_payoff(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '3',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryLineAccountEdit()
        self.calljson('/diacamma.accounting/entryLineAccountEdit', {'year': '1', 'journal': '3', 'entryaccount': '1', 'reference': '',
                                                                    'serial_entry': "-1|4|0|152.340000|0|0|None|\n-2|3|0|152.340000|0|0|aaabbb|", 'entrylineaccount_serial': '-2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryLineAccountEdit')
        self.assert_count_equal('', 5)

        self.assert_json_equal('LABELFORM', 'account', '[531] 531')
        self.assert_json_equal('FLOAT', 'debit_val', '152.34')
        self.assert_json_equal('FLOAT', 'credit_val', '0.00')
        self.assert_json_equal('EDIT', 'reference', 'aaabbb')
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryLineAccountAdd")
        self.assertEqual(len(self.json_actions[0]['params']), 1)
        self.assertEqual(self.json_actions[0]['params']['num_cpt'], 3)

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '3', 'entryaccount': '1',
                                                                   'serial_entry': "-1|4|0|152.340000|0|0|None|\n-2|3|0|152.340000|0|0|aaabbb|", 'debit_val': '152.34',
                                                                   'credit_val': '0.0', 'entrylineaccount_serial': '-2', 'reference': 'ccdd', 'num_cpt': '3'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], '1')
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "3")
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        serial_value = self.response_json['action']['params']['serial_entry']
        self.assertEqual(serial_value[-25:], "|3|0|152.340000|0|0|ccdd|")

    def test_valid_entry(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-2|12|0|152.340000|0|0|None|\n-3|4|3|152.340000|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '2', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-02-13')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entryline/@0/credit', 152.34)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[602] 602')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 152.34, -152.34, 0.00, 0.00])

        self.factory.xfer = EntryAccountOpenFromLine()
        self.calljson('/diacamma.accounting/entryAccountOpenFromLine',
                      {'year': '1', 'journal': '2', 'filter': '0', 'entryline': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountOpenFromLine')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(self.response_json['action']['params'], None)
        self.assertEqual(len(self.json_context), 5)
        self.assertEqual(self.json_context['filter'], "0")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")
        self.assertEqual(self.json_context['entryaccount'], 1)

        self.factory.xfer = EntryAccountClose()
        self.calljson('/diacamma.accounting/entryAccountClose',
                      {'CONFIRME': 'YES', 'year': '1', 'journal': '2', "entryline": "1"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountClose')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '2', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/entry.num', '1')
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', date.today())
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-02-13')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entryline/@0/credit', 152.34)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 152.34, -152.34, 0.00, 0.00])

        self.factory.xfer = EntryAccountOpenFromLine()
        self.calljson('/diacamma.accounting/entryAccountOpenFromLine',
                      {'year': '1', 'journal': '2', 'filter': '0', 'entryline': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountOpenFromLine')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountShow")
        self.assertEqual(self.response_json['action']['params'], None)
        self.assertEqual(len(self.json_context), 5)
        self.assertEqual(self.json_context['filter'], "0")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")
        self.assertEqual(self.json_context['entryaccount'], 1)

        self.factory.xfer = EntryAccountShow()
        self.calljson('/diacamma.accounting/entryAccountShow',
                      {'year': '1', 'journal': '2', 'filter': '0', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountShow')
        self.assert_count_equal('', 8)
        self.assert_json_equal('LABELFORM', 'num', '1')
        self.assert_json_equal('LABELFORM', 'journal', 'Achats')
        self.assert_json_equal('LABELFORM', 'date_entry', date.today().isoformat(), True)
        self.assert_json_equal('LABELFORM', 'date_value', '2015-02-13')
        self.assert_json_equal('LABELFORM', 'designation', 'un plein cadie')
        self.assert_count_equal('entrylineaccount', 2)
        self.assert_json_equal('', 'entrylineaccount/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entrylineaccount/@0/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount/@1/entry_account', '[602] 602')
        self.assert_json_equal('', 'entrylineaccount/@1/costaccounting', None)
        self.assert_count_equal('#entrylineaccount/actions', 0)
        self.assertEqual(len(self.json_actions), 2)
        self.assertEqual(self.json_actions[0]['id'], "diacamma.accounting/entryAccountCreateLinked")

        self.factory.xfer = CostAccountingAddModify()
        self.calljson('/diacamma.accounting/costAccountingAddModify', {"SAVE": "YES", 'name': 'aaa', 'description': 'aaa', 'year': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'costAccountingAddModify')  # id = 3

        self.factory.xfer = EntryAccountShow()
        self.calljson('/diacamma.accounting/entryAccountShow',
                      {'year': '1', 'journal': '2', 'filter': '0', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountShow')
        self.assert_count_equal('entrylineaccount', 2)
        self.assert_json_equal('', 'entrylineaccount/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entrylineaccount/@0/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount/@1/entry_account', '[602] 602')
        self.assert_json_equal('', 'entrylineaccount/@1/costaccounting', None)
        self.assert_count_equal('#entrylineaccount/actions', 1)
        self.assertEqual(len(self.json_actions), 2)

    def test_show_close_cost(self):
        fill_entries_fr(1)
        self.factory.xfer = EntryAccountOpenFromLine()
        self.calljson('/diacamma.accounting/entryAccountOpenFromLine',
                      {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '23'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountOpenFromLine')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountShow")
        self.assertEqual(self.response_json['action']['params'], None)
        self.assertEqual(len(self.json_context), 5)
        self.assertEqual(self.json_context['filter'], "0")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "0")
        self.assertEqual(self.json_context['entryaccount'], 11)

        self.factory.xfer = EntryAccountShow()
        self.calljson('/diacamma.accounting/entryAccountShow',
                      {'year': '1', 'journal': '0', 'filter': '0', 'entryaccount': '11'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountShow')
        self.assert_count_equal('', 8)
        self.assert_json_equal('LABELFORM', 'num', '7')
        self.assert_json_equal('LABELFORM', 'journal', 'Opérations diverses')
        self.assert_json_equal('LABELFORM', 'date_value', '2015-02-20')
        self.assert_json_equal('LABELFORM', 'designation', 'Frais bancaire')
        self.assert_count_equal('entrylineaccount', 2)
        self.assert_json_equal('', 'entrylineaccount/@0/entry_account', '[512] 512')
        self.assert_json_equal('', 'entrylineaccount/@0/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount/@1/entry_account', '[627] 627')
        self.assert_json_equal('', 'entrylineaccount/@1/costaccounting', 'close')
        self.assert_count_equal('#entrylineaccount/actions', 0)
        self.assertEqual(len(self.json_actions), 1)

    def test_inverse_entry(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-2|12|0|152.340000|0|0|None|\n-3|4|3|152.340000|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)

        self.assertEqual(len(self.json_actions), 5)
        self.assertEqual(self.json_actions[1]['id'], "diacamma.accounting/entryAccountClose")
        self.assertEqual(self.json_actions[2]['id'], "diacamma.accounting/entryAccountCreateLinked")
        self.assertEqual(self.json_actions[3]['id'], "diacamma.accounting/entryAccountReverse")

        self.factory.xfer = EntryAccountReverse()
        self.calljson('/diacamma.accounting/entryAccountReverse',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountReverse')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 14)

        self.assert_json_equal('LABELFORM', 'asset_warning', "écriture d'un avoir")
        self.assert_json_equal('', '#asset_warning/formatstr', "{[center]}{[i]}%s{[/i]}{[/center]}")

    def test_valid_payment(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-2|12|0|152.340000|0|0|None|\n-3|4|3|152.340000|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountCreateLinked()
        self.calljson('/diacamma.accounting/entryAccountCreateLinked',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountCreateLinked')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(len(self.response_json['action']['params']), 5)
        self.assertEqual(self.response_json['action']['params']['entryaccount'], 2)
        self.assertEqual(self.response_json['action']['params']['linked_entryaccount'], 1)
        self.assertEqual(self.response_json['action']['params']['serial_entry'][-26:-1], "|4|3|-152.340000|0|0|None")
        self.assertEqual(self.response_json['action']['params']['num_cpt_txt'], "5")
        self.assertEqual(self.response_json['action']['params']['journal'], "4")
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], "1")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'year': '1', 'journal': '4', 'entryaccount': '2', 'linked_entryaccount': '1',
                                                                'serial_entry': "-3|4|3|-152.340000|0|0|None|", 'num_cpt_txt': '5'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 16)
        self.assert_json_equal('SELECT', 'journal', '4')
        self.assert_json_equal('DATE', 'date_value', '2015-12-31')
        self.assert_json_equal('EDIT', 'designation', 'règlement de un plein cadie')

        self.assert_count_equal('entrylineaccount_serial', 1)
        self.assert_json_equal('EDIT', 'num_cpt_txt', '5')
        self.assert_json_equal('SELECT', 'num_cpt', '2')
        self.assert_select_equal('num_cpt', 2)  # nb=2
        self.assert_json_equal('FLOAT', 'debit_val', '0.00')
        self.assert_json_equal('FLOAT', 'credit_val', '152.34')
        self.assert_json_equal('EDIT', 'reference', '')

        self.assert_count_equal('entrylineaccount_serial', 1)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entrylineaccount_serial/@0/debit', -152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/credit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/costaccounting', None)
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'year': '1', 'journal': '2', 'entryaccount': '2', 'linked_entryaccount': '1',
                                                                'serial_entry': "-3|4|3|-152.340000|0|0|None|\n-4|2|0|-152.340000|0|0|Ch N°12345|"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)
        self.assert_count_equal('entrylineaccount_serial', 2)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entrylineaccount_serial/@0/debit', -152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/credit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/reference', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@0/costaccounting', None)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/entry_account', '[512] 512')
        self.assert_json_equal('', 'entrylineaccount_serial/@1/debit', 0)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/credit', 152.34)
        self.assert_json_equal('', 'entrylineaccount_serial/@1/reference', 'Ch N°12345')
        self.assert_json_equal('', 'entrylineaccount_serial/@1/costaccounting', None)
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate', {'year': '1', 'journal': '2', 'entryaccount': '2', 'linked_entryaccount': '1',
                                                                    'serial_entry': "-3|4|3|-152.340000|0|0|None||\n-4|2|0|-152.340000|0|0|Ch N°12345|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('entryline', 4)

        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-02-13')
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entryline/@0/credit', 152.34)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[602] 602')
        self.assert_json_equal('', 'entryline/@1/link', None)

        self.assert_json_equal('', 'entryline/@2/entry.num', None)
        self.assert_json_equal('', 'entryline/@2/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@2/entry.date_value', '2015-12-31')
        self.assert_json_equal('', 'entryline/@2/link', 'A')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entryline/@2/debit', -152.34)
        self.assert_json_equal('', 'entryline/@3/entry_account', '[512] 512')
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 152.34, -152.34, -152.34, 0.00])

    def test_valid_payment_canceled(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-02-13', 'designation': 'un plein cadie'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-2|12|0|152.340000|0|0|None|\n-3|4|3|152.340000|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.assertEqual(1, EntryAccount.objects.all().count())

        self.factory.xfer = EntryAccountCreateLinked()
        self.calljson('/diacamma.accounting/entryAccountCreateLinked',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountCreateLinked')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(len(self.response_json['action']['params']), 5)
        self.assertEqual(self.response_json['action']['params']['serial_entry'][-26:-1], "|4|3|-152.340000|0|0|None")
        self.assertEqual(len(self.json_context), 3)

        self.assertEqual(2, EntryAccount.objects.all().count())

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'year': '1', 'journal': '4', 'entryaccount': '2', 'linked_entryaccount': '1',
                                                                'serial_entry': "-3|4|3|-152.340000|0|0|None|", 'num_cpt_txt': '5'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 16)

        self.factory.xfer = EntryAccountUnlock()
        self.calljson('/diacamma.accounting/entryAccountUnlock', {'year': '1', 'journal': '4', 'entryaccount': '2', 'linked_entryaccount': '1',
                                                                  'serial_entry': "-3|4|3|-152.340000|0|0|None|", 'num_cpt_txt': '5'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountUnlock')

        self.assertEqual(1, EntryAccount.objects.all().count())

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-02-13')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[401 Luke Lucky]')
        self.assert_json_equal('', 'entryline/@0/credit', 152.34)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[602] 602')
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)

    def test_link_unlink_entries(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-04-27', 'designation': 'Une belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate', {'year': '1', 'journal': '2', 'entryaccount': '1',
                                                                    'serial_entry': "-6|9|0|364.91|0|0|None|\n-7|1|5|364.91|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '4', 'date_value': '2015-05-03',
                                                                'designation': 'Règlement de belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate', {'year': '1', 'journal': '4', 'entryaccount': '2',
                                                                    'serial_entry': "-9|1|5|-364.91|0|0|None|\n-8|2|0|364.91|0|0|BP N°987654|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '5',
                                                                'date_value': '2015-04-27', 'designation': 'divers'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate', {'year': '1', 'journal': '2', 'entryaccount': '3',
                                                                    'serial_entry': "-11|1|6|-364.91|0|0|None|\n-12|1|5|250.61|0|0|None|\n-13|1|7|114.30|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('entryline', 7)

        self.assert_json_equal('', 'entryline/@0/id', '2')
        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-04-27')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@0/debit', -364.91)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/id', '1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)

        self.assert_json_equal('', 'entryline/@2/id', '6')
        self.assert_json_equal('', 'entryline/@2/entry_account', "[411 Dalton William]")
        self.assert_json_equal('', 'entryline/@2/debit', -250.61)
        self.assert_json_equal('', 'entryline/@3/id', '5')
        self.assert_json_equal('', 'entryline/@3/entry_account', "[411 Dalton Jack]")
        self.assert_json_equal('', 'entryline/@3/credit', 364.91)
        self.assert_json_equal('', 'entryline/@4/id', '7')
        self.assert_json_equal('', 'entryline/@4/entry_account', "[411 Dalton Joe]")
        self.assert_json_equal('', 'entryline/@4/debit', -114.30)

        self.assert_json_equal('', 'entryline/@5/id', '3')
        self.assert_json_equal('', 'entryline/@5/entry.num', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_value', '2015-05-03')
        self.assert_json_equal('', 'entryline/@5/link', None)
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@5/credit', 364.91)
        self.assert_json_equal('', 'entryline/@5/costaccounting', None)
        self.assert_json_equal('', 'entryline/@6/id', '4')
        self.assert_json_equal('', 'entryline/@6/entry_account', '[512] 512')
        self.assert_json_equal('', 'entryline/@6/designation_ref', 'Règlement de belle facture{[br/]}BP N°987654')
        self.assert_json_equal('', 'entryline/@6/costaccounting', None)

        self.assert_json_equal('LABELFORM', 'result', [364.91, 0.00, 364.91, 364.91, 0.00])

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink', {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '2;3'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountLink')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 7)
        self.assert_json_equal('', 'entryline/@0/id', '2')
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@1/id', '1')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@5/id', '3')
        self.assert_json_equal('', 'entryline/@5/link', 'A')
        self.assert_json_equal('', 'entryline/@6/id', '4')
        self.assert_json_equal('', 'entryline/@6/link', None)

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink', {'CONFIRME': 'YES', 'year': '1', 'journal': '0', 'filter': '0', 'entryline': '3'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountLink')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 7)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/link', None)

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink', {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '1;2'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'entryAccountLink')
        self.assert_json_equal('', 'message', "Une ligne d'écriture n'a pas de compte de tiers !")

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink', {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '2;5'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'entryAccountLink')
        self.assert_json_equal('', 'message', "Ces lignes d'écritures ne concernent pas le même tiers !")

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink', {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '2;6'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'entryAccountLink')
        self.assert_json_equal('', 'message', "Ces lignes d'écritures ne s'équilibrent pas !")

    def test_delete_lineentry(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-04-27', 'designation': 'Une belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-6|9|0|364.91|0|0|None|\n-7|1|5|364.91|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)
        self.assert_count_equal('entrylineaccount_serial', 2)
        self.assertEqual(len(self.json_actions), 5)

        self.factory.xfer = EntryLineAccountDel()
        self.calljson('/diacamma.accounting/entryLineAccountDel', {'year': '1', 'journal': '2', 'entryaccount': '1',
                                                                   'serial_entry': "1|9|0|364.91|0|0|None|\n2|1|5|364.91|0|0|None|", "entrylineaccount_serial": '2'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountDel')
        self.assertEqual(self.response_json['action']['id'], "diacamma.accounting/entryAccountEdit")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['serial_entry'], "1|9|0|364.910000|0|0|None|")
        self.assertEqual(len(self.json_context), 3)
        self.assertEqual(self.json_context['entryaccount'], "1")
        self.assertEqual(self.json_context['year'], "1")
        self.assertEqual(self.json_context['journal'], "2")

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', "entrylineaccount_serial": '2', 'serial_entry': "1|9|0|364.91|0|0|None|"}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 13)
        self.assert_count_equal('entrylineaccount_serial', 1)
        self.assertEqual(len(self.json_actions), 2)

    def test_delete_entries(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-04-27', 'designation': 'Une belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '2', 'entryaccount': '1', 'serial_entry': "-6|9|0|364.91|0|0|None|\n-7|1|5|364.91|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '4',
                                                                'date_value': '2015-05-03', 'designation': 'Règlement de belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate',
                      {'year': '1', 'journal': '4', 'entryaccount': '2', 'serial_entry': "-9|1|5|-364.91|0|0|None|\n-8|2|0|364.91|0|0|BP N°987654|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink',
                      {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '2;3'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountLink')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)

        self.assert_json_equal('', 'entryline/@2/link', 'A')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@2/costaccounting', None)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('', 'entryline/@3/entry_account', '[512] 512')
        self.assert_json_equal('', 'entryline/@3/costaccounting', None)

        self.factory.xfer = EntryAccountDel()
        self.calljson('/diacamma.accounting/entryAccountDel',
                      {'CONFIRME': 'YES', 'year': '1', 'journal': '0', 'filter': '0', 'entryline': '1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountDel')

        self.factory.xfer = EntryAccountClose()
        self.calljson('/diacamma.accounting/entryAccountClose',
                      {'CONFIRME': 'YES', 'year': '1', 'journal': '0', 'filter': '0', "entryline": "3"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountClose')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/entry.num', '1')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[512] 512')
        self.assert_json_equal('', 'entryline/@1/debit', -364.91)
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Règlement de belle facture{[br/]}BP N°987654')
        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 364.91, 364.91])

        self.factory.xfer = EntryAccountDel()
        self.calljson('/diacamma.accounting/entryAccountDel',
                      {'year': '1', 'journal': '0', 'filter': '0', 'entryline': '3'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'entryAccountDel')
        self.assert_json_equal('', 'message', 'écriture validée !')

    def test_buyingselling_in_report(self):
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '1',
                                                                'date_value': '2015-03-21', 'designation': 'mauvais report'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '1', 'entryaccount': '1', 'num_cpt_txt': '70',
                                                                   'num_cpt': '9', 'third': 0, 'debit_val': '0.0', 'credit_val': '152.34'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assert_json_equal('', 'message', "Ce type d'écriture n'est pas permis dans ce journal !")

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '1', 'entryaccount': '1', 'num_cpt_txt': '60',
                                                                   'num_cpt': '13', 'third': 0, 'debit_val': '0.0', 'credit_val': '152.34'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'entryLineAccountAdd')
        self.assert_json_equal('', 'message', "Ce type d'écriture n'est pas permis dans ce journal !")

        self.factory.xfer = EntryLineAccountAdd()
        self.calljson('/diacamma.accounting/entryLineAccountAdd', {'year': '1', 'journal': '1', 'entryaccount': '1', 'num_cpt_txt': '401',
                                                                   'num_cpt': '4', 'third': 0, 'debit_val': '0.0', 'credit_val': '152.34'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryLineAccountAdd')

    def test_import_entries(self):
        default_costaccounting()
        fill_thirds_fr()

        csv_content = """date;code;description;debit;credit;third;cost;ref
04/09/2015;512;  Retrait;1 000,00;;;;
04/09/2015;531;  Retrait;;1 000,00;;;
05/09/2015;512;Virement ;1234.56 EUR;;;;#ABC987654
05/09/2015;411;Virement ;;1234.56 EUR;Minimum;;
06/09/2015;701;Sell;;321.47;;open;
06/09/2015;706;Sell;;366,51;;;
06/09/2015;411;Sell;687,98;;Dalton Joe;;
07/09/2015;512;Bad sum;123;;;;
07/09/2015;531;Bad sum;;456;;;
08/09/2015;515;Bad code;20,00;;;;
08/09/2015;531;Bad code;;20,00;;;
09/09/2015;106;alone;99999.99;;;;
10/09/2015;601;Wrong buy;30.02;;;bad;
10/09/2015;602;Wrong buy;37.01;;;close;
10/09/2015;401;Wrong buy;;67.03;Valjean Jean;;
11/09/2016;512;Bad date;500,00;;;;
11/09/2016;531;Bad date;;500,00;;;
"""

        self.factory.xfer = EntryAccountImport()
        self.calljson('/diacamma.accounting/entryAccountImport', {'step': 2, 'year': 1, 'journal': 5, 'quotechar': "'",
                                                                  'delimiter': ';', 'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'importcontent': StringIO(csv_content)}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountImport')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'year', 'Exercice du 1 janvier 2015 au 31 décembre 2015 [en création]')
        self.assert_json_equal('LABELFORM', 'journal', 'Opérations diverses')
        self.assert_select_equal('fld_entry.date_value', 8)
        self.assert_select_equal('fld_entry.designation', 8)
        self.assert_select_equal('fld_account', 8)
        self.assert_select_equal('fld_debit', 8)
        self.assert_select_equal('fld_credit', 8)
        self.assert_select_equal('fld_third', 9)
        self.assert_select_equal('fld_reference', 9)
        self.assert_select_equal('fld_costaccounting', 9)
        self.assert_count_equal('Array', 17)
        self.assert_count_equal('#Array/actions', 0)

        self.factory.xfer = EntryAccountImport()
        self.calljson('/diacamma.accounting/entryAccountImport', {'step': 3, 'year': 1, 'journal': 5, 'quotechar': "'", 'delimiter': ';',
                                                                  'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'importcontent0': csv_content,
                                                                  "fld_entry.date_value": "date", "fld_entry.designation": "description", "fld_account": "code",
                                                                  'fld_debit': 'debit', 'fld_credit': 'credit', 'fld_third': 'third',
                                                                  'fld_reference': 'ref', 'fld_costaccounting': 'cost'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountImport')
        self.assert_count_equal('', 6)
        self.assert_count_equal('Array', 17)
        self.assert_count_equal('#Array/actions', 0)

        self.factory.xfer = EntryAccountImport()
        self.calljson('/diacamma.accounting/entryAccountImport', {'step': 4, 'year': 1, 'journal': 5, 'quotechar': "'", 'delimiter': ';',
                                                                  'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'importcontent0': csv_content,
                                                                  "fld_entry.date_value": "date", "fld_entry.designation": "description", "fld_account": "code",
                                                                  'fld_debit': 'debit', 'fld_credit': 'credit', 'fld_third': 'third',
                                                                  'fld_reference': 'ref', 'fld_costaccounting': 'cost'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountImport')
        self.assert_count_equal('', 4)
        self.assert_json_equal('LABELFORM', 'result', "4 éléments ont été importés")
        self.assert_json_equal('LABELFORM', 'import_error', ["Écriture comptable non équilibré{[br/]}total crédit=333,00\xa0€ - total débit=0,00\xa0€",
                                                             'Code comptable "515" inconnu !',
                                                             "L'écriture 'Bad code' n'a qu'une seule ligne.",
                                                             "L'écriture 'alone' n'a qu'une seule ligne.",
                                                             "Comptabilité analytique 'bad' inconnue !",
                                                             "Comptabilité analytique 'close' inconnue !",
                                                             "Tiers 'Valjean Jean' inconnu !",
                                                             "Date '2015-12-31' invalide !"])
        self.assert_count_equal('entryline', 10)
        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-09-04')
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Retrait')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[512] 512')
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@0/debit', -1000.00)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/credit', 1000.00)

        self.assert_json_equal('', 'entryline/@2/entry.date_value', '2015-09-05')
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Virement')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@2/costaccounting', None)
        self.assert_json_equal('', 'entryline/@2/credit', 1234.56)
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Virement{[br/]}#ABC987654')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[512] 512')
        self.assert_json_equal('', 'entryline/@3/costaccounting', None)
        self.assert_json_equal('', 'entryline/@3/debit', -1234.56)

        self.assert_json_equal('', 'entryline/@4/entry.date_value', '2015-09-06')
        self.assert_json_equal('', 'entryline/@4/designation_ref', 'Sell')
        self.assert_json_equal('', 'entryline/@4/entry_account', '[411 Dalton Joe]')
        self.assert_json_equal('', 'entryline/@4/costaccounting', None)
        self.assert_json_equal('', 'entryline/@4/debit', -687.98)
        self.assert_json_equal('', 'entryline/@5/entry_account', '[701] 701')
        self.assert_json_equal('', 'entryline/@5/costaccounting', 'open')
        self.assert_json_equal('', 'entryline/@5/credit', 321.47)
        self.assert_json_equal('', 'entryline/@6/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@6/costaccounting', None)
        self.assert_json_equal('', 'entryline/@6/credit', 366.51)

        self.assert_json_equal('', 'entryline/@7/entry.date_value', '2015-09-10')
        self.assert_json_equal('', 'entryline/@7/designation_ref', 'Wrong buy')
        self.assert_json_equal('', 'entryline/@7/entry_account', '[401] 401')
        self.assert_json_equal('', 'entryline/@7/costaccounting', None)
        self.assert_json_equal('', 'entryline/@7/credit', 67.03)
        self.assert_json_equal('', 'entryline/@8/entry_account', '[601] 601')
        self.assert_json_equal('', 'entryline/@8/costaccounting', None)
        self.assert_json_equal('', 'entryline/@8/debit', -30.02)
        self.assert_json_equal('', 'entryline/@9/entry_account', '[602] 602')
        self.assert_json_equal('', 'entryline/@9/costaccounting', None)
        self.assert_json_equal('', 'entryline/@9/debit', -37.01)

    def test_link_entries_multiyear(self):
        # data last year
        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin', {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '1', 'journal': '2',
                                                                'date_value': '2015-12-27', 'designation': 'Une belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate', {'year': '1', 'journal': '2', 'entryaccount': '1',
                                                                    'serial_entry': "-6|9|0|364.91|0|0|None|\n-7|1|5|364.91|0|0|None|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')
        self.factory.xfer = EntryAccountClose()
        self.calljson('/diacamma.accounting/entryAccountClose',
                      {'CONFIRME': 'YES', 'year': '1', 'journal': '2', "entryline": "1"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountClose')

        # data new year
        new_year = FiscalYear.objects.create(begin='2016-01-01', end='2016-12-31', status=0, last_fiscalyear_id=1)
        fill_accounts_fr(new_year)
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'SAVE': 'YES', 'year': '2', 'journal': '4', 'date_value': '2016-01-03',
                                                                'designation': 'Règlement de belle facture'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountEdit')
        self.factory.xfer = EntryAccountValidate()
        self.calljson('/diacamma.accounting/entryAccountValidate', {'year': '2', 'journal': '4', 'entryaccount': '2',
                                                                    'serial_entry': "-9|18|5|-364.91|0|0|None|\n-8|19|0|364.91|0|0|BP N°987654|"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountValidate')
        self.factory.xfer = EntryAccountClose()
        self.calljson('/diacamma.accounting/entryAccountClose',
                      {'CONFIRME': 'YES', 'year': '2', 'journal': '4', "entryline": "4"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountClose')

        # begin test
        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 5, 'lines_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/id', '2')
        self.assert_json_equal('', 'entryline/@0/entry.num', 1)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-12-27')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Une belle facture')
        self.assert_json_equal('', 'entryline/@0/debit', -364.91)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/id', '3')
        self.assert_json_equal('', 'entryline/@1/entry.num', 1)
        self.assert_json_equal('', 'entryline/@1/entry.date_value', '2016-01-03')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Règlement de belle facture')
        self.assert_json_equal('', 'entryline/@1/credit', 364.91)
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)

        self.factory.xfer = EntryAccountLink()
        self.calljson('/diacamma.accounting/entryAccountLink', {'entryline': '2;3'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'entryAccountLink')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 5, 'lines_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/id', '2')
        self.assert_json_equal('', 'entryline/@0/entry.num', 1)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-12-27')
        self.assert_json_equal('', 'entryline/@0/link', "A&")
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Une belle facture')
        self.assert_json_equal('', 'entryline/@0/debit', -364.91)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/id', '3')
        self.assert_json_equal('', 'entryline/@1/entry.num', 1)
        self.assert_json_equal('', 'entryline/@1/entry.date_value', '2016-01-03')
        self.assert_json_equal('', 'entryline/@1/link', "A&")
        self.assert_json_equal('', 'entryline/@1/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Règlement de belle facture')
        self.assert_json_equal('', 'entryline/@1/credit', 364.91)
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)

        self.factory.xfer = FiscalYearClose()
        self.calljson('/diacamma.accounting/fiscalYearClose', {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearClose')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 5, 'lines_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('entryline', 3)
        self.assert_json_equal('', 'entryline/@0/id', '2')
        self.assert_json_equal('', 'entryline/@0/entry.num', 1)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-12-27')
        self.assert_json_equal('', 'entryline/@0/link', "A")
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Une belle facture')
        self.assert_json_equal('', 'entryline/@0/debit', -364.91)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/id', '7')
        self.assert_json_equal('', 'entryline/@1/entry.num', 3)
        self.assert_json_equal('', 'entryline/@1/entry.date_value', '2015-12-31')
        self.assert_json_equal('', 'entryline/@1/link', "A")
        self.assert_json_equal('', 'entryline/@1/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@1/designation_ref', "Cloture d'exercice - Tiers{[br/]}Une belle facture")
        self.assert_json_equal('', 'entryline/@1/credit', 364.91)
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)
        self.assert_json_equal('', 'entryline/@2/id', '3')
        self.assert_json_equal('', 'entryline/@2/entry.num', 1)
        self.assert_json_equal('', 'entryline/@2/entry.date_value', '2016-01-03')
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Règlement de belle facture')
        self.assert_json_equal('', 'entryline/@2/credit', 364.91)
        self.assert_json_equal('', 'entryline/@2/costaccounting', None)

        self.factory.xfer = FiscalYearReportLastYear()
        self.calljson('/diacamma.accounting/fiscalYearReportLastYear', {'CONFIRME': 'YES', 'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearReportLastYear')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 5, 'lines_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/id', '2')
        self.assert_json_equal('', 'entryline/@0/entry.num', 1)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-12-27')
        self.assert_json_equal('', 'entryline/@0/link', "A")
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Une belle facture')
        self.assert_json_equal('', 'entryline/@0/debit', -364.91)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/id', '7')
        self.assert_json_equal('', 'entryline/@1/entry.num', 3)
        self.assert_json_equal('', 'entryline/@1/entry.date_value', '2015-12-31')
        self.assert_json_equal('', 'entryline/@1/link', "A")
        self.assert_json_equal('', 'entryline/@1/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@1/designation_ref', "Cloture d'exercice - Tiers{[br/]}Une belle facture")
        self.assert_json_equal('', 'entryline/@1/credit', 364.91)
        self.assert_json_equal('', 'entryline/@1/costaccounting', None)
        self.assert_json_equal('', 'entryline/@2/id', '12')
        self.assert_json_equal('', 'entryline/@2/entry.num', 3)
        self.assert_json_equal('', 'entryline/@2/entry.date_value', '2016-01-01')
        self.assert_json_equal('', 'entryline/@2/link', "A")
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Report à nouveau - Dette tiers{[br/]}Une belle facture')
        self.assert_json_equal('', 'entryline/@2/debit', -364.91)
        self.assert_json_equal('', 'entryline/@2/costaccounting', None)
        self.assert_json_equal('', 'entryline/@3/id', '3')
        self.assert_json_equal('', 'entryline/@3/entry.num', 1)
        self.assert_json_equal('', 'entryline/@3/entry.date_value', '2016-01-03')
        self.assert_json_equal('', 'entryline/@3/link', "A")
        self.assert_json_equal('', 'entryline/@3/entry_account', '[411 Dalton William]')
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Règlement de belle facture')
        self.assert_json_equal('', 'entryline/@3/credit', 364.91)
        self.assert_json_equal('', 'entryline/@3/costaccounting', None)
