# -*- coding: utf-8 -*-
'''
Unit tests for configuration viewer

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
from os.path import join, dirname, exists

from django.utils.translation import gettext_lazy as _

from lucterios.framework.test import LucteriosTest, add_empty_user
from lucterios.framework.filetools import get_user_dir, readimage_to_base64, get_user_path
from lucterios.CORE.models import LucteriosUser, Preference
from lucterios.CORE.views_usergroup import UsersPreference, PreferenceEdit

from lucterios.contacts.views import PostalCodeList, PostalCodeAdd, Configuration, CurrentStructure, \
    CurrentStructureAddModify, Account, AccountAddModify, CurrentStructurePrint, \
    CustomFieldAddModify, CustomFieldUp
from lucterios.contacts.models import LegalEntity
from lucterios.contacts.test_tools import change_ourdetail, create_jack


class PostalCodeTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        ourdetails = LegalEntity.objects.get(id=1)
        ourdetails.postal_code = "97400"
        ourdetails.save()

    def test_listall(self):
        self.factory.xfer = PostalCodeList()
        self.calljson('/lucterios.contacts/postalCodeList',
                      {'filter_postal_code': ''}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assertEqual(self.json_meta['title'], 'Code postal')
        self.assertEqual(len(self.json_context), 1)
        self.assertEqual(len(self.json_actions), 1)
        self.assert_action_equal('POST', self.json_actions[0], ('Fermer', 'mdi:mdi-close'))
        self.assert_count_equal('', 4)
        self.assert_comp_equal(('IMAGE', "img"), 'mdi:mdi-mailbox-outline', (0, 0, 1, 1))
        self.assert_comp_equal(('EDIT', "filter_postal_code"), '', (1, 1, 1, 1))
        self.assert_attrib_equal("filter_postal_code", 'description', 'Filtrer sur le code postal')
        self.assert_coordcomp_equal("postalCode", (0, 2, 2, 1))
        self.assert_attrib_equal("postalCode", 'nb_lines', '333')

        self.assert_attrib_equal("postalCode", 'page_max', '14')
        self.assert_attrib_equal("postalCode", 'page_num', '0')
        self.assert_grid_equal("postalCode", {"postal_code": "code postal", "city": "ville", "country": "pays"}, 25)
        self.assert_json_equal('', "postalCode/@0/postal_code", '97100')
        self.assert_json_equal('', "postalCode/@24/postal_code", '97131')

    def test_listdefault(self):
        self.factory.xfer = PostalCodeList()
        self.calljson('/lucterios.contacts/postalCodeList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_comp_equal(('EDIT', "filter_postal_code"), '97400', (1, 1, 1, 1))
        self.assert_attrib_equal("postalCode", 'nb_lines', '6')
        self.assert_attrib_equal("postalCode", 'page_max', '1')
        self.assert_attrib_equal("postalCode", 'page_num', '0')
        self.assert_count_equal("postalCode", 6)

    def test_filterlist(self):
        self.factory.xfer = PostalCodeList()
        self.calljson('/lucterios.contacts/postalCodeList',
                      {'filter_postal_code': '973'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_attrib_equal("postalCode", 'nb_lines', '27')
        self.assert_json_equal('', "postalCode/@0/postal_code", '97300')
        self.assert_json_equal('', "postalCode/@24/postal_code", '97370')

    def test_pagelist(self):
        self.factory.xfer = PostalCodeList()
        self.calljson('/lucterios.contacts/postalCodeList',
                      {'GRID_PAGE%postalCode': '5', 'filter_postal_code': ''}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_attrib_equal("postalCode", 'nb_lines', '333')
        self.assert_json_equal('', "postalCode/@0/postal_code", '97416')

    def test_add(self):
        self.factory.xfer = PostalCodeAdd()
        self.calljson('/lucterios.contacts/postalCodeAdd', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeAdd')
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[0], ('Ok', 'mdi:mdi-check', 'lucterios.contacts', 'postalCodeAdd', 1, 1, 1))
        self.assert_action_equal('POST', self.json_actions[1], ('Annuler', 'mdi:mdi-cancel'))
        self.assert_count_equal('', 4)

        self.factory.xfer = PostalCodeAdd()
        self.calljson('/lucterios.contacts/postalCodeAdd', {'SAVE': 'YES', 'postal_code': '96999', 'city': 'Trifouilly', 'country': 'LOIN'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'postalCodeAdd')
        self.assertEqual(len(self.json_context), 3)

        self.factory.xfer = PostalCodeList()
        self.calljson('/lucterios.contacts/postalCodeList', {'filter_postal_code': ''}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'postalCodeList')
        self.assert_attrib_equal("postalCode", 'nb_lines', '334')

        self.factory.xfer = PostalCodeAdd()
        self.calljson('/lucterios.contacts/postalCodeAdd',
                      {'SAVE': 'YES', 'postal_code': '96999', 'city': 'Trifouilly', 'country': 'LOIN'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.contacts', 'postalCodeAdd')
        self.assert_json_equal('', 'type', '3')
        self.assert_json_equal('', 'text', str('Cet enregistrement existe déjà!'))


class ConfigurationTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        change_ourdetail()
        create_jack(add_empty_user())
        rmtree(get_user_dir(), True)

    def test_config(self):
        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assertEqual(self.json_meta['title'], 'Configuration des contacts')
        self.assertEqual(len(self.json_context), 0)
        self.assertEqual(len(self.json_actions), 1)
        self.assert_action_equal('POST', self.json_actions[0], ('Fermer', 'mdi:mdi-close'))
        self.assert_count_equal('', 13)
        self.assert_coordcomp_equal("function", (0, 1, 2, 1, 1))
        self.assert_grid_equal("function", {"name": "nom"}, 0)
        self.assert_coordcomp_equal("structure_type", (0, 1, 2, 1, 2))
        self.assert_grid_equal("structure_type", {"name": "nom"}, 0)
        self.assert_coordcomp_equal("custom_field", (0, 1, 2, 1, 3))
        self.assert_grid_equal("custom_field", {"name": "nom", "model_title": "modèle", "kind_txt": "type"}, 0)

    def test_ourdetails(self):
        self.factory.xfer = CurrentStructure()
        self.calljson('/lucterios.contacts/currentStructure', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructure')
        self.assertEqual(self.json_meta['title'], 'Nos coordonnées')
        self.assertEqual(len(self.json_context), 1)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal('POST', self.json_actions[0], (str('Editer'), 'mdi:mdi-pencil-outline', 'lucterios.contacts', 'currentStructureAddModify', 0, 1, 1))
        self.assert_action_equal('GET', self.json_actions[1], ('Imprimer', 'mdi:mdi-printer-outline', 'lucterios.contacts', 'currentStructurePrint', 0, 1, 1))
        self.assert_action_equal('POST', self.json_actions[2], ('Fermer', 'mdi:mdi-close'))
        self.assert_count_equal('', 18)
        self.assert_comp_equal(('LABELFORM', "name"), "WoldCompany", (1, 0, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "address"), "Place des cocotiers", (1, 2, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "postal_code"), "97200", (1, 3, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', "city"), "FORT DE FRANCE", (2, 3, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', "country"), "MARTINIQUE", (1, 4, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "tel1"), "01-23-45-67-89", (1, 5, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', "tel2"), '', (2, 5, 1, 1, 1))
        self.assert_comp_equal(('LINK', "email"), "mr-sylvestre@worldcompany.com", (1, 6, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "comment"), '', (1, 7, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "legal_identification"), '', (1, 8, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "vat_identification"), '', (1, 9, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', "identify_number"), '', (1, 10, 2, 1, 1))
        self.assert_comp_equal(('IMAGE', "logoimg"), "/static/lucterios.contacts/images/NoImage.png", (0, 2, 1, 6, 1))
        self.assert_coordcomp_equal("responsability", (0, 0, 1, 1, 2))

    def test_changedetails(self):
        self.factory.xfer = CurrentStructureAddModify()
        self.calljson('/lucterios.contacts/currentStructureAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructureAddModify')
        self.assertEqual(self.json_meta['title'], str('Nos coordonnées'))
        self.assert_count_equal('', 14)
        self.assert_comp_equal(('EDIT', 'name'), "WoldCompany", (1, 0, 2, 1))
        self.assert_comp_equal(('MEMO', 'address'), "Place des cocotiers", (1, 2, 2, 1))
        self.assert_comp_equal(('EDIT', 'postal_code'), "97200", (1, 3, 1, 1))
        self.assert_comp_equal(('SELECT', 'city'), "FORT DE FRANCE", (2, 3, 1, 1))
        self.assert_comp_equal(('EDIT', 'country'), "MARTINIQUE", (1, 4, 2, 1))
        self.assert_comp_equal(('EDIT', 'tel1'), "01-23-45-67-89", (1, 5, 1, 1))
        self.assert_comp_equal(('EDIT', 'tel2'), '', (2, 5, 1, 1))
        self.assert_comp_equal(('EDIT', 'email'), "mr-sylvestre@worldcompany.com", (1, 6, 2, 1))
        self.assert_comp_equal(('EDIT', "legal_identification"), '', (1, 8, 2, 1))
        self.assert_comp_equal(('EDIT', "vat_identification"), '', (1, 9, 2, 1))
        self.assert_comp_equal(('MEMO', 'identify_number'), '', (1, 10, 2, 1))
        self.assert_comp_equal(('MEMO', 'comment'), '', (1, 11, 2, 1))
        self.assert_coordcomp_equal('uploadlogo', (1, 12, 2, 1))

        self.factory.xfer = CurrentStructureAddModify()
        self.calljson('/lucterios.contacts/currentStructureAddModify', {"address": 'Rue de la liberté{[newline]}BP 123',
                                                                        "comment": 'Big boss: Mr Sylvestre{[newline]}Beuaaaaa....', "name": 'WorldCompany',
                                                                        "city": 'ST PIERRE', "country": 'MARTINIQUE', "tel2": '06-01-02-03-04', "SAVE": 'YES',
                                                                        "tel1": '09-87-65-43-21', "postal_code": '97250', "email": 'jack@worldcompany.com',
                                                                        "identify_number": 'AZERTY123DDSQ'}, False)
        self.assert_observer(
            'core.acknowledge', 'lucterios.contacts', 'currentStructureAddModify')
        self.assertEqual(len(self.json_context), 10)

        self.factory.xfer = CurrentStructure()
        self.calljson('/lucterios.contacts/currentStructure', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructure')
        self.assert_json_equal('LABELFORM', 'name', "WorldCompany")
        self.assert_json_equal('LABELFORM', 'address', "Rue de la liberté{[newline]}BP 123")
        self.assert_json_equal('LABELFORM', 'postal_code', "97250")
        self.assert_json_equal('LABELFORM', 'city', "ST PIERRE")
        self.assert_json_equal('LABELFORM', 'country', "MARTINIQUE")
        self.assert_json_equal('LABELFORM', 'tel1', "09-87-65-43-21")
        self.assert_json_equal('LABELFORM', 'tel2', '06-01-02-03-04')
        self.assert_json_equal('LINK', 'email', "jack@worldcompany.com")
        self.assert_json_equal('LABELFORM', 'comment', 'Big boss: Mr Sylvestre{[newline]}Beuaaaaa....')
        self.assert_json_equal('LABELFORM', 'identify_number', "AZERTY123DDSQ")

    def test_printdetails(self):
        self.factory.xfer = CurrentStructurePrint()
        self.calljson('/lucterios.contacts/currentStructurePrint', {}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'currentStructurePrint')
        self.assertEqual(self.json_meta['title'], str('Nos coordonnées'))
        self.assertEqual(self.response_json['print']['title'], str('Nos coordonnées'))
        self.assertEqual(self.response_json['print']['mode'], 3)
        self.save_pdf()

    def test_logo(self):
        self.assertFalse(exists(get_user_path('contacts', 'Image_1.jpg')))
        logo_path = join(dirname(__file__), 'docs', 'en', 'ResponsabilityLegalEntity.png')
        logo_stream = "image.jpg;" + \
            readimage_to_base64(logo_path, False).decode("utf-8")

        self.factory.xfer = CurrentStructureAddModify()
        self.calljson('/lucterios.contacts/currentStructureAddModify',
                      {"SAVE": 'YES', "uploadlogo": logo_stream}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'currentStructureAddModify')
        self.assertTrue(exists(get_user_path('contacts', 'Image_1.jpg')))

        self.factory.xfer = CurrentStructure()
        self.calljson('/lucterios.contacts/currentStructure', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'currentStructure')
        self.assert_json_equal('IMAGE', 'logoimg', "data:image/jpg;base64,/9j/4AAQSkZJRgABAQAAAQ", True)

        self.factory.xfer = CurrentStructurePrint()
        self.calljson('/lucterios.contacts/currentStructurePrint', {}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'currentStructurePrint')
        self.save_pdf()

    def test_account(self):
        self.factory.user = LucteriosUser.objects.get(username='empty')
        self.factory.xfer = Account()
        self.calljson('/lucterios.contacts/account', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'account')
        self.assertEqual(self.json_meta['title'], str('Votre compte'))
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[1 - 1], (str('Editer'), 'mdi:mdi-pencil-outline', 'lucterios.contacts', 'accountAddModify', 0, 1, 1))
        self.assert_action_equal('POST', self.json_actions[2 - 1], ('Fermer', 'mdi:mdi-close'))
        self.assert_count_equal('', 18)
        self.assert_comp_equal(('LABELFORM', 'genre'), 1, (1, 0, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'firstname'), "jack", (1, 1, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'lastname'), "MISTER", (2, 1, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'address'), "rue de la liberté", (1, 2, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'postal_code'), "97250", (1, 3, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'city'), "LE PRECHEUR", (2, 3, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'country'), "MARTINIQUE", (1, 4, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'tel1'), '', (1, 5, 1, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'tel2'), '02-78-45-12-95', (2, 5, 1, 1, 1))
        self.assert_comp_equal(('LINK', 'email'), "jack@worldcompany.com", (1, 6, 2, 1, 1))
        self.assert_comp_equal(('LABELFORM', 'comment'), '', (1, 7, 2, 1, 1))
        self.assert_comp_equal(('IMAGE', 'logoimg'), "/static/lucterios.contacts/images/NoImage.png", (0, 2, 1, 6, 1))

    def test_accountmodify(self):
        self.factory.xfer = AccountAddModify()
        self.calljson('/lucterios.contacts/accountAddModify', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'accountAddModify')
        self.assertEqual(self.json_meta['title'], str('Mon compte'))
        self.assert_count_equal('', 13)
        self.assert_comp_equal(('SELECT', 'genre'), "1", (1, 0, 2, 1))
        self.assert_select_equal('genre', {1: 'Homme', 2: 'Femme'})  # nb=2

    def test_noaccount(self):
        self.factory.user = LucteriosUser.objects.get(username='admin')
        self.factory.xfer = Account()
        self.calljson('/lucterios.contacts/account', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'account')
        self.assertEqual(self.json_meta['title'], str('Votre compte'))
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal('POST', self.json_actions[0], ('Préférences', 'mdi:mdi-account-cog', 'CORE', 'usersPreference', 0, 1, 1, {}))
        self.assert_action_equal('POST', self.json_actions[1], ('Editer', 'mdi:mdi-pencil-outline', 'CORE', 'usersEdit', 0, 1, 1, {'user_actif': '1'}))
        self.assert_action_equal('POST', self.json_actions[2], ('Fermer', 'mdi:mdi-close'))

    def test_user_preference(self):
        Preference.check_and_create(name="dummy-default-value", typeparam=Preference.TYPE_INTEGER, title=_("dummy-default-value"), args="{'min':0,'max':10}", value='0')
        Preference.check_and_create(name="dummy-default-price", typeparam=Preference.TYPE_REAL, title=_("dummy-default-price"), args="{'min':0,'max':1000,'prec':2}", value='100')
        Preference.check_and_create(name="dummy-default-valid", typeparam=Preference.TYPE_BOOL, title=_("dummy-default-valid"), args="{}", value='False')
        self.factory.user = LucteriosUser.objects.get(username='admin')

        self.factory.xfer = UsersPreference()
        self.calljson('/CORE/usersPreference', {}, False)
        self.assert_observer('core.custom', 'CORE', 'usersPreference')
        self.assert_count_equal('', 3)
        self.assert_count_equal('preferences', 3)
        self.assert_json_equal('', 'preferences/@0/id', 'dummy-default-price')
        self.assert_json_equal('', 'preferences/@0/title', 'dummy-default-price')
        self.assert_json_equal('', 'preferences/@0/value_txt', '100')
        self.assert_json_equal('', 'preferences/@1/id', 'dummy-default-valid')
        self.assert_json_equal('', 'preferences/@1/title', 'dummy-default-valid')
        self.assert_json_equal('', 'preferences/@1/value_txt', 'Non')
        self.assert_json_equal('', 'preferences/@2/id', 'dummy-default-value')
        self.assert_json_equal('', 'preferences/@2/title', 'dummy-default-value')
        self.assert_json_equal('', 'preferences/@2/value_txt', '0')
        self.assert_count_equal('#preferences/actions', 1)
        self.assert_action_equal('POST', '#preferences/actions/@0', ('Modifier', 'mdi:mdi-pencil-outline', 'CORE', 'preferenceEdit', 0, 1, 0))

        self.factory.xfer = PreferenceEdit()
        self.calljson('/CORE/preferenceEdit', {'preferences': 'dummy-default-value'}, False)
        self.assert_observer('core.custom', 'CORE', 'preferenceEdit')
        self.assert_count_equal('', 5)
        self.assert_json_equal('LABELFORM', 'title', 'dummy-default-value')
        self.assert_json_equal('LABELFORM', 'user', 'admin')
        self.assert_json_equal('FLOAT', 'dummy-default-value', '0')
        self.assert_json_equal('CHECK', 'setdefault', False)
        self.assertEqual(self.json_context['user'], self.factory.user.id)

    def test_configuration_customfield(self):
        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_count_equal('custom_field', 0)
        self.assert_count_equal('#custom_field/actions', 4)

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'aaa', 'modelname': 'contacts.LegalEntity', 'kind': '0', 'args_multi': 'n', 'args_min': '0', 'args_max': '0', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'bbb', 'modelname': 'contacts.Individual', 'kind': '1', 'args_multi': 'n', 'args_min': '0', 'args_max': '10', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_count_equal('custom_field', 2)
        self.assert_json_equal('', 'custom_field/@0/id', 1)
        self.assert_json_equal('', 'custom_field/@0/name', 'aaa')
        self.assert_json_equal('', 'custom_field/@0/model_title', 'personne morale')
        self.assert_json_equal('', 'custom_field/@0/kind_txt', 'Chaîne')
        self.assert_json_equal('', 'custom_field/@1/id', 2)
        self.assert_json_equal('', 'custom_field/@1/name', 'bbb')
        self.assert_json_equal('', 'custom_field/@1/model_title', 'personne physique')
        self.assert_json_equal('', 'custom_field/@1/kind_txt', 'Entier [0;10]')

        self.factory.xfer = CustomFieldUp()
        self.calljson('/lucterios.contacts/customFieldUp', {"custom_field": 2}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldUp')

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_count_equal('custom_field', 2)
        self.assert_json_equal('', 'custom_field/@0/id', 2)
        self.assert_json_equal('', 'custom_field/@0/name', 'bbb')
        self.assert_json_equal('', 'custom_field/@0/model_title', 'personne physique')
        self.assert_json_equal('', 'custom_field/@0/kind_txt', 'Entier [0;10]')
        self.assert_json_equal('', 'custom_field/@1/id', 1)
        self.assert_json_equal('', 'custom_field/@1/name', 'aaa')
        self.assert_json_equal('', 'custom_field/@1/model_title', 'personne morale')
        self.assert_json_equal('', 'custom_field/@1/kind_txt', 'Chaîne')

        self.factory.xfer = CustomFieldUp()
        self.calljson('/lucterios.contacts/customFieldUp', {"custom_field": 2}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldUp')

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_count_equal('custom_field', 2)
        self.assert_json_equal('', 'custom_field/@0/id', 2)
        self.assert_json_equal('', 'custom_field/@1/id', 1)
