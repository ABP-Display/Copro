# -*- coding: utf-8 -*-
'''
Unit tests for contacts viewer

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

from lucterios.framework.test import LucteriosTest, add_empty_user
from lucterios.contacts.test_tools import initial_contact
from lucterios.contacts.views_possessions import ConfPossession, CategoryAddModify, CategoryDel, \
    PossessionShow, PossessionList, PossessionAddModify, PossessionDel, \
    PossessionOwner, PossessionOwnerSave
from lucterios.contacts.models import CustomField, CategoryPossession, Possession
from os.path import exists, join, dirname
from lucterios.framework.filetools import get_user_path, readimage_to_base64
from lucterios.CORE.models import LucteriosUser
from lucterios.contacts.views import Account


class PossessionsTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        initial_contact(add_empty_user())

    def test_config(self):
        self.factory.xfer = ConfPossession()
        self.calljson('/lucterios.contacts/confPossession', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'confPossession')
        self.assertEqual(self.json_meta['title'], 'Configuration des possessions')
        self.assert_count_equal('', 6)
        self.assert_grid_equal("category_possession", {"name": "nom", "description": "description"}, 0)
        self.assert_grid_equal("custom_field", {"name": "nom", "kind_txt": "type"}, 0)

    def test_categorie(self):
        self.factory.xfer = ConfPossession()
        self.calljson('/lucterios.contacts/confPossession', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'confPossession')
        self.assert_count_equal('category_possession', 0)

        self.factory.xfer = CategoryAddModify()
        self.calljson('/lucterios.contacts/categoryAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'categoryAddModify')
        self.assert_action_equal('POST', self.json_actions[0], ('Ok', 'mdi:mdi-check', 'lucterios.contacts', 'categoryAddModify', 1, 1, 1))
        self.assert_action_equal('POST', self.json_actions[1], ('Annuler', 'mdi:mdi-cancel'))
        self.assert_count_equal('', 3)

        self.factory.xfer = CategoryAddModify()
        self.calljson('/lucterios.contacts/categoryAddModify', {'SAVE': 'YES', 'name': 'voiture', 'description': 'jolie voiture'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'categoryAddModify')

        self.factory.xfer = ConfPossession()
        self.calljson('/lucterios.contacts/confPossession', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'confPossession')
        self.assert_count_equal('category_possession', 1)
        self.assert_json_equal('', "category_possession/@0/id", 1)
        self.assert_json_equal('', "category_possession/@0/name", "voiture")
        self.assert_json_equal('', "category_possession/@0/description", "jolie voiture")

        self.factory.xfer = CategoryDel()
        self.calljson('/lucterios.contacts/categoryDel',
                      {'CONFIRME': 'YES', 'category_possession': 1}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'categoryDel')

        self.factory.xfer = ConfPossession()
        self.calljson('/lucterios.contacts/confPossession', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'confPossession')
        self.assert_count_equal('category_possession', 0)

    def _initial_custom_values(self):
        initial_values = [{'name': 'aaa', 'modelname': 'contacts.Possession', 'kind': '0', 'args': "{'multi':False, 'min':0, 'max':0, 'prec':0, 'list':[]}"},
                          {'name': 'bbb', 'modelname': 'contacts.Possession', 'kind': '1',
                           'args': "{'multi':False,'min':0, 'max':100, 'prec':0, 'list':[]}"},
                          {'name': 'ccc', 'modelname': 'contacts.Possession', 'kind': '2',
                           'args': "{'multi':False,'min':-10.0, 'max':10.0, 'prec':1, 'list':[]}"},
                          {'name': 'ddd', 'modelname': 'contacts.Possession', 'kind': '3',
                           'args': "{'multi':False,'min':0, 'max':0, 'prec':0, 'list':[]}"},
                          {'name': 'eee', 'modelname': 'contacts.Possession', 'kind': '4', 'args':
                           "{'multi':False,'min':0, 'max':0, 'prec':0, 'list':['U','V','W','X','Y','Z']}"},
                          {'name': 'fff', 'modelname': 'contacts.Possession', 'kind': '0', 'args': "{'multi':True,'min':0, 'max':0, 'prec':0, 'list':[]}"},
                          {'name': 'ggg', 'modelname': 'contacts.Possession', 'kind': '5', 'args': "{'multi':True,'min':0, 'max':0, 'prec':0, 'list':[]}"}]
        for initial_value in initial_values:
            CustomField.objects.create(**initial_value)
        CategoryPossession.objects.create(name="First", description="First category")
        CategoryPossession.objects.create(name="Second", description="Second category")
        init_object = Possession.objects.create(name="Object", category_possession_id=1, owner_id=2, comment="Super object")
        init_object.set_custom_values({"custom_1": "Bla Bla bla", "custom_2": 123, "custom_3": 45.67,
                                       "custom_4": True, "custom_5": 3, "custom_6": "Bhouuuuu!", "custom_7": "2021-05-13"})

    def test_possession(self):
        self._initial_custom_values()

        self.factory.xfer = PossessionList()
        self.calljson('/lucterios.contacts/possessionList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionList')
        self.assert_count_equal('possession', 1)

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 1}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', "name", "Object")
        self.assert_json_equal('LABELFORM', "owner", "MISTER jack")
        self.assert_json_equal('LABELFORM', "category_possession", "First")
        self.assert_json_equal('LABELFORM', "custom_1", "Bla Bla bla")
        self.assert_json_equal('LABELFORM', "custom_2", 123)
        self.assert_json_equal('LABELFORM', "custom_3", 45.67)
        self.assert_json_equal('LABELFORM', "custom_4", True)
        self.assert_json_equal('LABELFORM', "custom_5", 3)
        self.assert_json_equal('LABELFORM', "custom_6", "Bhouuuuu!")
        self.assert_json_equal('LABELFORM', "custom_7", "2021-05-13")
        self.assert_json_equal('LABELFORM', "comment", "Super object")
        self.assert_json_equal('BUTTON', "change_owner", "")
        self.assert_json_equal('BUTTON', "show_owner", "")

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify', {'possession': 1}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionAddModify')
        self.assert_count_equal('', 12)

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify',
                      {"SAVE": 'YES', 'possession': '1', "name": "Other object",
                       "category_possession": 2, "custom_1": "Blublublu", "custom_2": 987, "custom_3": 65.43,
                       "custom_4": False, "custom_5": 5, "custom_6": "qqqqq", "custom_7": "2004-11-24", "comment": "Bad object"}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'possessionAddModify')

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 1}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_json_equal('LABELFORM', "name", "Other object")
        self.assert_json_equal('LABELFORM', "owner", "MISTER jack")
        self.assert_json_equal('LABELFORM', "category_possession", "Second")
        self.assert_json_equal('LABELFORM', "custom_1", "Blublublu")
        self.assert_json_equal('LABELFORM', "custom_2", 987)
        self.assert_json_equal('LABELFORM', "custom_3", 65.43)
        self.assert_json_equal('LABELFORM', "custom_4", False)
        self.assert_json_equal('LABELFORM', "custom_5", 5)
        self.assert_json_equal('LABELFORM', "custom_6", "qqqqq")
        self.assert_json_equal('LABELFORM', "custom_7", "2004-11-24")
        self.assert_json_equal('LABELFORM', "comment", "Bad object")

        self.factory.xfer = PossessionList()
        self.calljson('/lucterios.contacts/possessionList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionList')
        self.assert_count_equal('possession', 1)

    def test_possession_image(self):
        self._initial_custom_values()

        self.assertFalse(exists(get_user_path('contacts', 'Possession_1.jpg')))
        logo_path = join(dirname(__file__), 'docs', 'en', 'EditIndividual.png')
        logo_stream = "image.png;" + readimage_to_base64(logo_path, False).decode("utf-8")

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_json_equal('IMAGE', 'logoimg', "/static/lucterios.contacts/images/NoImage.png")

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify',
                      {"SAVE": 'YES', 'possession': '1', "uploadlogo": logo_stream}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'possessionAddModify')
        self.assertTrue(exists(get_user_path('contacts', 'Possession_1.jpg')))

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_json_equal('IMAGE', 'logoimg', "data:image/jpg;base64,", True)

    def test_possession_add(self):
        self._initial_custom_values()

        self.factory.xfer = PossessionList()
        self.calljson('/lucterios.contacts/possessionList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionList')
        self.assert_count_equal('possession', 1)
        self.assert_json_equal('', "possession/@0/id", 1)
        self.assert_json_equal('', "possession/@0/name", "Object")
        self.assert_json_equal('', "possession/@0/category_possession", "First")
        self.assert_json_equal('', "possession/@0/owner", "MISTER jack")

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify',
                      {"SAVE": 'YES', "name": "Other object",
                       "category_possession": 2, "custom_1": "Blublublu", "custom_2": 987, "custom_3": 65.43,
                       "custom_4": False, "custom_5": 5, "custom_6": "qqqqq", "custom_7": "2004-11-24", "comment": "Bad object"}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'possessionAddModify')

        self.factory.xfer = PossessionList()
        self.calljson('/lucterios.contacts/possessionList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionList')
        self.assert_count_equal('possession', 2)
        self.assert_json_equal('', "possession/@0/id", 1)
        self.assert_json_equal('', "possession/@0/name", "Object")
        self.assert_json_equal('', "possession/@0/category_possession", "First")
        self.assert_json_equal('', "possession/@0/owner", "MISTER jack")
        self.assert_json_equal('', "possession/@1/id", 2)
        self.assert_json_equal('', "possession/@1/name", "Other object")
        self.assert_json_equal('', "possession/@1/category_possession", "Second")
        self.assert_json_equal('', "possession/@1/owner", None)

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 2}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_count_equal('', 15)
        self.assert_json_equal('LABELFORM', "owner", None)
        self.assert_json_equal('BUTTON', "change_owner", "")
        self.assertFalse('show_owner' in self.json_data.keys(), self.json_data.keys())

        self.factory.xfer = PossessionOwner()
        self.calljson('/lucterios.contacts/possessionOwner', {'possession': 2}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionOwner')
        self.assert_count_equal('abstractcontact', 2)

        self.factory.xfer = PossessionOwnerSave()
        self.calljson('/lucterios.contacts/possessionOwnerSave', {'possession': 2, "pkname": 'abstractcontact', 'abstractcontact': 1}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'possessionOwnerSave')

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 2}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', "owner", "WoldCompany")
        self.assert_json_equal('BUTTON', "change_owner", "")
        self.assert_json_equal('BUTTON', "show_owner", "")

        self.factory.xfer = PossessionList()
        self.calljson('/lucterios.contacts/possessionList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionList')
        self.assert_count_equal('possession', 2)
        self.assert_json_equal('', "possession/@0/id", 1)
        self.assert_json_equal('', "possession/@0/name", "Object")
        self.assert_json_equal('', "possession/@0/category_possession", "First")
        self.assert_json_equal('', "possession/@0/owner", "MISTER jack")
        self.assert_json_equal('', "possession/@1/id", 2)
        self.assert_json_equal('', "possession/@1/name", "Other object")
        self.assert_json_equal('', "possession/@1/category_possession", "Second")
        self.assert_json_equal('', "possession/@1/owner", "WoldCompany")

        self.factory.xfer = PossessionDel()
        self.calljson('/lucterios.contacts/possessionDel',
                      {"CONFIRME": 'YES', 'possession': '2'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'possessionDel')

        self.factory.xfer = PossessionList()
        self.calljson('/lucterios.contacts/possessionList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionList')
        self.assert_count_equal('possession', 1)

    def test_account(self):
        self._initial_custom_values()
        self.factory.user = LucteriosUser.objects.get(username='empty')
        Possession.objects.create(name="NO", category_possession_id=2, owner_id=1, comment="Bad object")

        self.factory.xfer = Account()
        self.calljson('/lucterios.contacts/account', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'account')
        self.assert_count_equal('', 18 + 2)
        self.assert_count_equal('possession', 1)
        self.assert_json_equal('', "possession/@0/id", 1)
        self.assert_json_equal('', "possession/@0/name", "Object")
        self.assert_json_equal('', "possession/@0/category_possession", "First")
        self.assertEqual(self.json_context['owner'], 2)
        self.assertEqual(self.json_context['mng_owner'], False)

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 1, 'mng_owner': False, 'owner': 2}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'possessionShow')
        self.assert_count_equal('', 14)
        self.assert_json_equal('LABELFORM', "name", "Object")
        self.assert_json_equal('LABELFORM', "owner", "MISTER jack")
        self.assert_json_equal('LABELFORM', "category_possession", "First")
        self.assert_json_equal('LABELFORM', "custom_1", "Bla Bla bla")
        self.assert_json_equal('LABELFORM', "custom_2", 123)
        self.assert_json_equal('LABELFORM', "custom_3", 45.67)
        self.assert_json_equal('LABELFORM', "custom_4", True)
        self.assert_json_equal('LABELFORM', "custom_5", 3)
        self.assert_json_equal('LABELFORM', "custom_6", "Bhouuuuu!")
        self.assert_json_equal('LABELFORM', "custom_7", "2021-05-13")
        self.assert_json_equal('LABELFORM', "comment", "Super object")
        self.assertFalse('change_owner' in self.json_data.keys(), self.json_data.keys())
        self.assertFalse('show_owner' in self.json_data.keys(), self.json_data.keys())

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify',
                      {"SAVE": 'YES', "name": "Other object", 'mng_owner': False, 'owner': 2,
                       "category_possession": 2, "custom_1": "Blublublu", "custom_2": 987, "custom_3": 65.43,
                       "custom_4": False, "custom_5": 5, "custom_6": "qqqqq", "custom_7": "2004-11-24", "comment": "Bad object"}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'possessionAddModify')

        self.factory.xfer = Account()
        self.calljson('/lucterios.contacts/account', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'account')
        self.assert_count_equal('possession', 2)
        self.assert_json_equal('', "possession/@0/id", 1)
        self.assert_json_equal('', "possession/@0/name", "Object")
        self.assert_json_equal('', "possession/@0/category_possession", "First")
        self.assert_json_equal('', "possession/@1/id", 3)
        self.assert_json_equal('', "possession/@1/name", "Other object")
        self.assert_json_equal('', "possession/@1/category_possession", "Second")

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 2, 'mng_owner': False, 'owner': 2}, False)
        self.assert_observer('core.exception', 'lucterios.contacts', 'possessionShow')

        self.factory.xfer = PossessionShow()
        self.calljson('/lucterios.contacts/possessionShow', {'possession': 2, 'mng_owner': False, 'owner': 1}, False)
        self.assert_observer('core.exception', 'lucterios.contacts', 'possessionShow')

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify', {'possession': 2, 'mng_owner': False, 'owner': 2}, False)
        self.assert_observer('core.exception', 'lucterios.contacts', 'possessionAddModify')

        self.factory.xfer = PossessionAddModify()
        self.calljson('/lucterios.contacts/possessionAddModify', {'possession': 2, 'mng_owner': False, 'owner': 1}, False)
        self.assert_observer('core.exception', 'lucterios.contacts', 'possessionAddModify')
