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
from os.path import join, dirname, exists
from _io import StringIO
from base64 import b64decode

from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import readimage_to_base64, get_user_path
from lucterios.framework.xfersearch import get_search_query_from_criteria
from lucterios.CORE.views_usergroup import UsersEdit
from lucterios.CORE.views import ObjectMerge

from lucterios.contacts.views import Configuration, CustomFieldAddModify, ContactImport
from lucterios.contacts.models import LegalEntity, Individual, Function, Responsability, CustomField, ContactCustomField
from lucterios.contacts.test_tools import initial_contact, create_jack
from lucterios.contacts.views_contacts import IndividualList, LegalEntityList, \
    LegalEntityAddModify, IndividualAddModify, IndividualShow, IndividualUserAdd, \
    IndividualUserValid, LegalEntityDel, LegalEntityShow, ResponsabilityAdd, \
    ResponsabilityModify, LegalEntitySearch, IndividualSearch, \
    LegalEntityListing, LegalEntityLabel, IndividualListing, IndividualLabel, \
    AbstractContactFindDouble, AbstractContactShow


class ContactsTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        initial_contact()

    def test_individual(self):
        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_comp_equal(('EDIT', 'filter'), '', (0, 2, 1, 1))
        self.assert_coordcomp_equal('individual', (0, 3, 2, 1))
        self.assert_count_equal('individual', 1)

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualAddModify')
        self.assert_count_equal('', 13)

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify', {"address": 'Avenue de la Paix{[newline]}BP 987',
                                                                  "comment": 'no comment', "firstname": 'Marie', "lastname": 'DUPOND',
                                                                  "city": 'ST PIERRE', "country": 'MARTINIQUE', "tel2": '06-54-87-19-34', "SAVE": 'YES',
                                                                  "tel1": '09-96-75-15-00', "postal_code": '97250', "email": 'marie.dupond@worldcompany.com',
                                                                  "genre": "2"}, False)

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 2)

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {'filter': 'e'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 2)

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {'filter': 'marie'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 1)

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {'filter': 'dupon'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 1)

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {'filter': 'jack'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 1)

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {'filter': 'truc'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 0)

    def test_individual_image(self):
        self.assertFalse(exists(get_user_path('contacts', 'Image_2.jpg')))
        logo_path = join(dirname(__file__), 'docs', 'en', 'EditIndividual.png')
        logo_stream = "image.png;" + \
            readimage_to_base64(logo_path, False).decode("utf-8")

        self.factory.xfer = IndividualShow()
        self.calljson('/lucterios.contacts/individualShow', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualShow')
        self.assert_json_equal('IMAGE', 'logoimg', "/static/lucterios.contacts/images/NoImage.png")

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify',
                      {"SAVE": 'YES', 'individual': '2', "uploadlogo": logo_stream}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'individualAddModify')
        self.assertTrue(exists(get_user_path('contacts', 'Image_2.jpg')))

        self.factory.xfer = IndividualShow()
        self.calljson('/lucterios.contacts/individualShow', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualShow')
        self.assert_json_equal('IMAGE', 'logoimg', "data:image/jpg;base64,", True)

    def test_individual_user(self):
        self.factory.xfer = IndividualShow()
        self.calljson('/lucterios.contacts/individualShow', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'genre', 1)
        self.assert_json_equal('LABELFORM', 'firstname', "jack")
        self.assert_json_equal('LABELFORM', 'lastname', "MISTER")
        self.assert_json_equal('LINK', 'email', "jack@worldcompany.com")

        self.assert_comp_equal(('LABELFORM', 'user'), None, (1, 8, 2, 1, 1))
        self.assert_coordcomp_equal('userbtn', (3, 8, 1, 1, 1))
        self.assert_action_equal('POST', '#userbtn/action', ('Ajouter', 'mdi:mdi-pencil-plus-outline', 'lucterios.contacts', 'individualUserAdd', 0, 1, 1))

        self.factory.xfer = IndividualUserAdd()
        self.calljson('/lucterios.contacts/individualUserAdd', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualUserAdd')
        self.assert_count_equal('', 2)
        self.assert_comp_equal(('EDIT', 'username'), 'jackM', (1, 0, 1, 1))
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[1 - 1], ('Ok', 'mdi:mdi-check', 'lucterios.contacts', 'individualUserValid', 1, 1, 1))
        self.assert_action_equal('POST', self.json_actions[2 - 1], ('Annuler', 'mdi:mdi-cancel'))

        self.factory.xfer = IndividualUserValid()
        self.calljson('/lucterios.contacts/individualUserValid',
                      {'individual': '2', 'username': 'jacko'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'individualUserValid')
        self.assertEqual(len(self.json_context), 2)
        self.assertEqual(self.json_context['individual'], "2")
        self.assertEqual(self.json_context['username'], "jacko")
        self.assert_action_equal('POST', self.response_json['action'], ('Créer', "mdi:mdi-pencil-plus", "CORE", "usersEdit", 1, 1, 1,
                                                                        {"user_actif": "2", "IDENT_READ": "YES"}))
        self.factory.xfer = UsersEdit()
        self.calljson('/CORE/usersEdit', {'individual': '2', 'username':
                                          'jacko', 'user_actif': '2', 'IDENT_READ': 'YES'}, False)
        self.assert_observer('core.custom', 'CORE', 'usersEdit')
        self.assert_json_equal('LABELFORM', 'username', "jacko")
        self.assert_json_equal('LABELFORM', 'first_name', "jack")
        self.assert_json_equal('LABELFORM', 'last_name', "MISTER")
        self.assert_json_equal('LABELFORM', 'email', "jack@worldcompany.com")

        self.factory.xfer = IndividualShow()
        self.calljson('/lucterios.contacts/individualShow', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualShow')
        self.assert_comp_equal(('LABELFORM', 'user'), "jacko", (1, 8, 2, 1, 1))
        self.assert_action_equal('POST', '#userbtn/action', ('Modifier', 'mdi:mdi-pencil-outline', 'CORE', 'usersEdit', 0, 1, 1))

    def test_individual_search(self):
        fieldnames = Individual.get_search_fields()
        self.assertEqual(15, len(fieldnames))

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify', {"address": 'Avenue de la Paix{[newline]}BP 987',
                                                                  "comment": 'no comment', "firstname": 'Marie', "lastname": 'DUPOND',
                                                                  "city": 'ST PIERRE', "country": 'MARTINIQUE', "tel2": '06-54-87-19-34', "SAVE": 'YES',
                                                                  "tel1": '09-96-75-15-00', "postal_code": '97250', "email": 'marie.dupond@worldcompany.com',
                                                                  "genre": "2"}, False)

        self.factory.xfer = IndividualSearch()
        self.calljson('/lucterios.contacts/individualSearch', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualSearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [])
        self.assert_count_equal('', 6)
        self.assert_count_equal('individual', 2)

        self.factory.xfer = IndividualSearch()
        self.calljson('/lucterios.contacts/individualSearch',
                      {'CRITERIA': 'genre||8||1;2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualSearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["genre", 8, ["1", "2"]]])
        self.assert_count_equal('', 7)
        self.assert_count_equal('individual', 2)

        self.factory.xfer = IndividualSearch()
        self.calljson('/lucterios.contacts/individualSearch',
                      {'CRITERIA': '[["genre",8,["1"]]]'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualSearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["genre", 8, ["1"]]])
        self.assert_count_equal('', 7)
        self.assert_count_equal('individual', 1)

        self.factory.xfer = IndividualSearch()
        self.calljson('/lucterios.contacts/individualSearch',
                      {'CRITERIA': '[["genre",8,"2"]]'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualSearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["genre", 8, "2"]])
        self.assert_count_equal('', 7)
        self.assert_count_equal('individual', 1)

        self.factory.xfer = IndividualSearch()
        self.calljson('/lucterios.contacts/individualSearch',
                      {'CRITERIA': 'responsability_set.functions||9||1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualSearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["responsability_set.functions", 9, "1"]])
        self.assert_count_equal('', 6)
        self.assert_count_equal('individual', 0)

        self.factory.xfer = IndividualSearch()
        self.calljson('/lucterios.contacts/individualSearch',
                      {'CRITERIA': '[["user.username",5,"empt"]]'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualSearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["user.username", 5, "empt"]])
        self.assert_count_equal('', 6)
        self.assert_count_equal('individual', 0)

    def test_individual_listing(self):
        self.factory.xfer = IndividualListing()
        self.calljson('/lucterios.contacts/individualListing', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualListing')
        self.assertEqual(self.json_meta['title'], str('Personnes physiques'))
        self.assert_count_equal('', 5)
        self.assert_comp_equal(('SELECT', 'PRINT_MODE'), "3", (0, 2, 2, 1))
        self.assert_select_equal('PRINT_MODE', {3: 'Fichier PDF', 4: 'Fichier CSV', 2: "Fichier ODS"})  # nb=3
        self.assert_comp_equal(('SELECT', 'MODEL'), "3", (0, 3, 2, 1))
        self.assert_select_equal('MODEL', {3: 'liste'})  # nb=1
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = IndividualListing()
        self.calljson('/lucterios.contacts/individualListing',
                      {'PRINT_MODE': '4', 'MODEL': 3, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'individualListing')
        self.assertEqual(self.json_meta['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['mode'], 4)
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 14, str(content_csv))
        self.assertEqual(content_csv[1].strip(), '"Personnes physiques"')
        self.assertEqual(content_csv[6].strip(), '"#";"prénom";"nom";"adresse";"ville";"tel";"courriel";')

        self.factory.xfer = IndividualListing()
        self.calljson('/lucterios.contacts/individualListing',
                      {'PRINT_MODE': '4', 'MODEL': 3, 'filter': 'marie', 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'individualListing')
        self.assertEqual(self.json_meta['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['mode'], 4)
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 13, str(content_csv))
        self.assertEqual(content_csv[1].strip(), '"Personnes physiques"')
        self.assertEqual(content_csv[6].strip(), '"#";"prénom";"nom";"adresse";"ville";"tel";"courriel";', str(content_csv))

    def test_individual_listing_pdf(self):
        self.factory.xfer = IndividualListing()
        self.calljson('/lucterios.contacts/individualListing',
                      {'PRINT_MODE': '3', 'MODEL': 3, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'individualListing')
        self.save_pdf()

    def test_individual_listing_ods(self):
        self.factory.xfer = IndividualListing()
        self.calljson('/lucterios.contacts/individualListing',
                      {'PRINT_MODE': '2', 'MODEL': 3, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'individualListing')
        self.save_ods()

    def test_individual_label(self):
        self.factory.xfer = IndividualLabel()
        self.calljson('/lucterios.contacts/individualLabel', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualLabel')
        self.assertEqual(self.json_meta['title'], str('Personnes physiques'))
        self.assert_count_equal('', 4)
        self.assert_comp_equal(('SELECT', 'PRINT_MODE'), "3", (0, 2, 2, 1))
        self.assert_select_equal('PRINT_MODE', {3: 'Fichier PDF'})  # nb=1
        self.assert_comp_equal(('SELECT', 'LABEL'), "1", (0, 3, 2, 1))
        self.assert_select_equal('LABEL', 6)
        self.assert_comp_equal(('FLOAT', 'FIRSTLABEL'), "1", (0, 4, 2, 1))
        self.assert_comp_equal(('SELECT', 'MODEL'), "4", (0, 5, 2, 1))
        self.assert_select_equal('MODEL', {4: 'label'})  # nb=1
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = IndividualLabel()
        self.calljson('/lucterios.contacts/individualLabel',
                      {'PRINT_MODE': '3', 'LABEL': 3, 'FIRSTLABEL': 5, 'MODEL': 4, 'name_filter': 'marie'}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'individualLabel')
        self.assertEqual(self.json_meta['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['mode'], 3)
        self.save_pdf(ident=1)

        self.factory.xfer = IndividualLabel()
        self.calljson('/lucterios.contacts/individualLabel',
                      {'PRINT_MODE': '3', 'LABEL': 2, 'FIRSTLABEL': 4, 'MODEL': 4}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'individualLabel')
        self.assertEqual(self.json_meta['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes physiques'))
        self.assertEqual(self.response_json['print']['mode'], 3)
        self.save_pdf(ident=2)

    def test_individual_fieldsprint(self):
        self.maxDiff = None
        ourdetails = LegalEntity.objects.get(id=1)
        indiv_jack = Individual.objects.get(id=2)
        resp = Responsability.objects.create(individual=indiv_jack, legal_entity=ourdetails)
        resp.functions.set(Function.objects.filter(id__in=[1, 2]))
        resp.save()

        print_field_list = Individual.get_all_print_fields()
        self.assertEqual(40, len(print_field_list))
        print_text = ""

        for print_field_item in print_field_list:
            if 'image' not in print_field_item[1]:
                print_text += "#%s " % print_field_item[1]
        self.assertEqual("#firstname #lastname #address #postal_code #city #country #tel1 #tel2 #email #comment ", print_text[:86])
        self.assertEqual("#user.username #responsability_set.legal_entity.name #responsability_set.legal_entity.structure_type.name ", print_text[86:192])
        self.assertEqual(
            "#responsability_set.legal_entity.address #responsability_set.legal_entity.postal_code #responsability_set.legal_entity.city #responsability_set.legal_entity.country ", print_text[192:357])
        self.assertEqual("#responsability_set.legal_entity.tel1 #responsability_set.legal_entity.tel2 #responsability_set.legal_entity.email ", print_text[357:472])
        self.assertEqual("#responsability_set.legal_entity.comment #responsability_set.legal_entity.legal_identification #responsability_set.legal_entity.vat_identification #responsability_set.legal_entity.identify_number #responsability_set.functions.name ", print_text[472:703])
        self.assertEqual("#OUR_DETAIL.name #OUR_DETAIL.address #OUR_DETAIL.postal_code #OUR_DETAIL.city #OUR_DETAIL.country ", print_text[703:801])
        self.assertEqual("#OUR_DETAIL.tel1 #OUR_DETAIL.tel2 #OUR_DETAIL.email ", print_text[801:853])
        self.assertEqual("#OUR_DETAIL.comment #OUR_DETAIL.legal_identification #OUR_DETAIL.vat_identification #OUR_DETAIL.identify_number ", print_text[853:965])
        self.assertEqual(
            "jack MISTER rue de la liberté 97250 LE PRECHEUR MARTINIQUE  02-78-45-12-95 jack@worldcompany.com   WoldCompany  Place des cocotiers 97200 FORT DE FRANCE MARTINIQUE 01-23-45-67-89  mr-sylvestre@worldcompany.com     President{[br/]}Secretaire ", indiv_jack.evaluate(print_text[:703]))
        self.assertEqual("WoldCompany Place des cocotiers 97200 FORT DE FRANCE MARTINIQUE 01-23-45-67-89  mr-sylvestre@worldcompany.com     ", indiv_jack.evaluate(print_text[703:]))

    def test_legalentity(self):
        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityList')
        self.assert_comp_equal(('SELECT', 'structure_type'), '0', (0, 2, 1, 1))
        self.assert_select_equal('structure_type', {0: None, 1: 'Type A', 2: 'Type B', 3: 'Type C'})  # nb=4
        self.assert_coordcomp_equal('legal_entity', (0, 3, 2, 1))
        self.assert_count_equal('legal_entity', 1)

        self.factory.xfer = LegalEntityAddModify()
        self.calljson('/lucterios.contacts/legalEntityAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityAddModify')
        self.assert_count_equal('', 15)

        self.factory.xfer = LegalEntityAddModify()
        self.calljson('/lucterios.contacts/legalEntityAddModify', {"address": 'Avenue de la Paix{[newline]}BP 987',
                                                                   "comment": 'no comment', "name": 'truc-muche',
                                                                   "city": 'ST PIERRE', "country": 'MARTINIQUE', "tel2": '06-54-87-19-34', "SAVE": 'YES',
                                                                   "tel1": '09-96-75-15-00', "postal_code": '97250', "email": 'contact@truc-muche.org',
                                                                   "structure_type": 2}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'legalEntityAddModify')

        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {}, False)
        self.assert_count_equal('legal_entity', 2)
        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {"structure_type": 1}, False)
        self.assert_count_equal('legal_entity', 0)
        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {"structure_type": 2}, False)
        self.assert_count_equal('legal_entity', 1)
        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {"structure_type": 3}, False)
        self.assert_count_equal('legal_entity', 0)

    def test_legalentity_delete(self):
        self.factory.xfer = LegalEntityDel()
        self.calljson('/lucterios.contacts/legalEntityDel', {'legal_entity': '1'}, False)
        self.assert_observer('core.exception', 'lucterios.contacts', 'legalEntityDel')
        self.assert_json_equal('', 'message', "Vous ne pouvez pas supprimer cette personne morale !")

    def test_legalentity_responsability(self):
        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_count_equal('', 17)
        self.assert_json_equal('LABELFORM', 'name', "WoldCompany")
        self.assert_grid_equal('responsability', {"individual": "personne physique", 'functions': 'fonctions'}, 0)  # nb=2
        self.assert_count_equal('#responsability/actions', 4)

        self.factory.xfer = ResponsabilityAdd()
        self.calljson('/lucterios.contacts/responsabilityAdd', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'responsabilityAdd')
        self.assert_count_equal('', 4)
        self.assert_json_equal('LABELFORM', 'legal_entity', "WoldCompany")
        self.assert_grid_equal('individual', {'firstname': 'prénom', 'lastname': 'nom', 'tel1': 'tel1', 'tel2': 'tel2', 'email': 'courriel'}, 1)  # nb=5
        self.assert_count_equal('#individual/actions', 3)
        self.assert_json_equal('', 'individual/@0/id', '2')

        self.factory.xfer = ResponsabilityAdd()
        self.calljson('/lucterios.contacts/responsabilityAdd',
                      {'legal_entity': '1', 'name_filter': 'jack'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'responsabilityAdd')
        self.assert_count_equal('', 4)
        self.assert_json_equal('LABELFORM', 'legal_entity', "WoldCompany")
        self.assert_grid_equal('individual', {'firstname': 'prénom', 'lastname': 'nom', 'tel1': 'tel1', 'tel2': 'tel2', 'email': 'courriel'}, 1)  # nb=5
        self.assert_count_equal("#individual/actions", 3)
        self.assert_json_equal('', 'individual/@0/id', '2')

        self.factory.xfer = ResponsabilityModify()
        self.calljson('/lucterios.contacts/responsabilityModify', {'legal_entity': '1', 'individual': '2', "SAVE": "YES"}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'responsabilityModify')

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_json_equal('LABELFORM', 'name', "WoldCompany")
        self.assert_count_equal('responsability', 1)
        self.assert_json_equal('', 'responsability/@0/id', '1')
        self.assert_json_equal('', 'responsability/@0/individual', "MISTER jack")
        self.assert_json_equal('', 'responsability/@0/functions', [])

        self.factory.xfer = ResponsabilityModify()
        self.calljson('/lucterios.contacts/responsabilityModify', {'responsability': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'responsabilityModify')
        self.assert_json_equal('LABELFORM', 'legal_entity', "WoldCompany")
        self.assert_json_equal('LABELFORM', 'individual', "MISTER jack")
        self.assert_attrib_equal("functions", 'description', "fonctions")

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_count_equal('responsability', 1)

        self.factory.xfer = ResponsabilityModify()
        self.calljson('/lucterios.contacts/responsabilityModify', {'responsability': '1', 'functions': '2;4', "SAVE": "YES"}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'responsabilityModify')

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_json_equal('LABELFORM', 'name', "WoldCompany")
        self.assert_count_equal('responsability', 1)
        self.assert_json_equal('', 'responsability/@0/id', '1')
        self.assert_json_equal('', 'responsability/@0/individual', "MISTER jack")
        self.assert_json_equal('', 'responsability/@0/functions', ["Secretaire", "Troufion"])

    def test_legalentity_search(self):
        self.factory.xfer = LegalEntityAddModify()
        self.calljson('/lucterios.contacts/legalEntityAddModify', {"address": 'Avenue de la Paix{[newline]}BP 987',
                                                                   "comment": 'no comment', "name": 'truc-muche',
                                                                   "city": 'ST PIERRE', "country": 'MARTINIQUE', "tel2": '06-54-87-19-34', "SAVE": 'YES',
                                                                   "tel1": '09-96-75-15-00', "postal_code": '97250', "email": 'contact@truc-muche.org',
                                                                   "structure_type": 2}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'legalEntityAddModify')

        self.factory.xfer = LegalEntitySearch()
        self.calljson('/lucterios.contacts/legalEntitySearch', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntitySearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [])
        self.assert_count_equal('', 6)
        self.assert_count_equal('legal_entity', 2)

        self.factory.xfer = LegalEntitySearch()
        self.calljson('/lucterios.contacts/legalEntitySearch',
                      {'CRITERIA': 'name||5||truc//structure_type||8||2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntitySearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["name", 5, "truc"], ["structure_type", 8, "2"]])
        self.assert_count_equal('', 7)
        self.assert_count_equal('legal_entity', 1)

        self.factory.xfer = LegalEntitySearch()
        self.calljson('/lucterios.contacts/legalEntitySearch',
                      {'CRITERIA': '[["name",5,"truc"],["structure_type",8,["2"]]]'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntitySearch')
        self.assert_json_equal("SEARCH", "CRITERIA", [["name", 5, "truc"], ["structure_type", 8, ["2"]]])
        self.assert_count_equal('', 7)
        self.assert_count_equal('legal_entity', 1)

    def test_legalentity_listing(self):
        self.factory.xfer = LegalEntityListing()
        self.calljson('/lucterios.contacts/legalEntityListing', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityListing')
        self.assertEqual(self.json_meta['title'], str('Personnes morales'))
        self.assert_count_equal('', 5)
        self.assert_comp_equal(('SELECT', 'PRINT_MODE'), "3", (0, 2, 2, 1))
        self.assert_select_equal('PRINT_MODE', {3: 'Fichier PDF', 4: 'Fichier CSV', 2: "Fichier ODS"})  # nb=3
        self.assert_comp_equal(('SELECT', 'MODEL'), "1", (0, 3, 2, 1))
        self.assert_select_equal('MODEL', {1: 'liste'})  # nb=1
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = LegalEntityListing()
        self.calljson('/lucterios.contacts/legalEntityListing',
                      {'PRINT_MODE': '4', 'MODEL': 1, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'legalEntityListing')
        self.assertEqual(self.json_meta['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['mode'], 4)
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 14, str(content_csv))
        self.assertEqual(content_csv[1].strip(), '"Personnes morales"')
        self.assertEqual(content_csv[6].strip(), '"#";"nom";"adresse";"ville";"tel";"courriel";', str(content_csv))

        self.factory.xfer = LegalEntityListing()
        self.calljson('/lucterios.contacts/legalEntityListing',
                      {'PRINT_MODE': '4', 'MODEL': 1, 'structure_type': 2, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'legalEntityListing')
        self.assertEqual(self.json_meta['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['mode'], 4)
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 13, str(content_csv))
        self.assertEqual(content_csv[1].strip(), '"Personnes morales"')
        self.assertEqual(content_csv[6].strip(), '"#";"nom";"adresse";"ville";"tel";"courriel";')

    def test_legalentity_listing_pdf(self):
        self.factory.xfer = LegalEntityListing()
        self.calljson('/lucterios.contacts/legalEntityListing',
                      {'PRINT_MODE': '3', 'MODEL': 1, 'structure_type': 2, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'legalEntityListing')
        self.save_pdf()

    def test_legalentity_listing_ods(self):
        self.factory.xfer = LegalEntityListing()
        self.calljson('/lucterios.contacts/legalEntityListing',
                      {'PRINT_MODE': '2', 'MODEL': 1, 'structure_type': 2, 'WITHNUM': True}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'legalEntityListing')
        self.save_ods()

    def test_legalentity_label(self):
        self.factory.xfer = LegalEntityLabel()
        self.calljson('/lucterios.contacts/legalEntityLabel', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityLabel')
        self.assertEqual(self.json_meta['title'], str('Personnes morales'))
        self.assert_count_equal('', 4)
        self.assert_comp_equal(('SELECT', 'PRINT_MODE'), "3", (0, 2, 2, 1))
        self.assert_select_equal('PRINT_MODE', {3: 'Fichier PDF'})  # nb=1
        self.assert_comp_equal(('SELECT', 'LABEL'), "1", (0, 3, 2, 1))
        self.assert_select_equal('LABEL', 6)
        self.assert_comp_equal(('FLOAT', 'FIRSTLABEL'), "1", (0, 4, 2, 1))
        self.assert_comp_equal(('SELECT', 'MODEL'), "2", (0, 5, 2, 1))
        self.assert_select_equal('MODEL', {2: 'label'})  # nb=1
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = LegalEntityLabel()
        self.calljson('/lucterios.contacts/legalEntityLabel',
                      {'PRINT_MODE': '3', 'LABEL': 1, 'FIRSTLABEL': 3, 'MODEL': 2, 'structure_type': 2}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'legalEntityLabel')
        self.assertEqual(self.json_meta['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['mode'], 3)
        self.save_pdf(ident=1)

        self.factory.xfer = LegalEntityLabel()
        self.calljson('/lucterios.contacts/legalEntityLabel',
                      {'PRINT_MODE': '3', 'LABEL': 5, 'FIRSTLABEL': 2, 'MODEL': 2}, False)
        self.assert_observer('core.print', 'lucterios.contacts', 'legalEntityLabel')
        self.assertEqual(self.json_meta['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['title'], str('Personnes morales'))
        self.assertEqual(self.response_json['print']['mode'], 3)
        self.save_pdf(ident=2)

    def test_custom_fields(self):
        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_count_equal('', 13)
        self.assert_grid_equal('custom_field', {"name": "nom", "model_title": "modèle", "kind_txt": "type"}, 0)  # nb=3

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'customFieldAddModify')
        self.assertEqual(self.json_meta['title'], 'Ajouter un champ personnalisé')
        self.assertEqual(len(self.json_context), 0)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[0], ('Ok', 'mdi:mdi-check', 'lucterios.contacts', 'customFieldAddModify', 1, 1, 1, {"SAVE": "YES"}))
        self.assert_action_equal('POST', self.json_actions[1], ('Annuler', 'mdi:mdi-cancel'))
        self.assert_count_equal('', 10)
        self.assert_comp_equal(('SELECT', 'modelname'), 'contacts.AbstractContact', (1, 0, 1, 1))
        self.assert_comp_equal(('EDIT', 'name'), '', (1, 1, 1, 1))
        self.assert_comp_equal(('SELECT', 'kind'), '0', (1, 2, 1, 1))
        self.assert_comp_equal(('CHECK', 'args_multi'), '0', (1, 3, 1, 1))
        self.assert_comp_equal(('FLOAT', 'args_min'), '0', (1, 4, 1, 1))
        self.assert_comp_equal(('FLOAT', 'args_max'), '0', (1, 5, 1, 1))
        self.assert_comp_equal(('FLOAT', 'args_prec'), '0', (1, 6, 1, 1))
        self.assert_comp_equal(('EDIT', 'args_list'), '', (1, 7, 1, 1))
        self.assert_comp_equal(('CHECK', 'args_today'), '0', (1, 8, 1, 1))
        self.assert_select_equal('kind', {0: "Chaîne", 1: "Entier", 2: "Réel", 3: "Booléen",
                                          4: "Sélection", 5: "Date"})

    def test_custom_fields_added(self):
        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'aaa', 'modelname': 'contacts.AbstractContact',
                                                                   'kind': '0', 'args_multi': 'n', 'args_min': '0', 'args_max': '0', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'bbb', 'modelname': 'contacts.AbstractContact',
                                                                   'kind': '1', 'args_multi': 'n', 'args_min': '0', 'args_max': '100', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'ccc', 'modelname': 'contacts.AbstractContact',
                                                                   'kind': '2', 'args_multi': 'n', 'args_min': '-10.0', 'args_max': '10.0', 'args_prec': '1', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'ddd', 'modelname': 'contacts.LegalEntity',
                                                                   'kind': '3', 'args_multi': 'n', 'args_min': '0', 'args_max': '0', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'eee', 'modelname': 'contacts.Individual',
                                                                   'kind': '4', 'args_multi': 'n', 'args_min': '0', 'args_max': '0', 'args_prec': '0', 'args_list': 'U,V,W,X,Y,Z'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = CustomFieldAddModify()
        self.calljson('/lucterios.contacts/customFieldAddModify', {"SAVE": "YES", 'name': 'fff', 'modelname': 'contacts.Individual',
                                                                   'kind': '5', 'args_multi': 'n', 'args_min': '0', 'args_max': '0', 'args_prec': '0', 'args_list': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.contacts', 'customFieldAddModify')

        self.factory.xfer = Configuration()
        self.calljson('/lucterios.contacts/configuration', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'configuration')
        self.assert_count_equal('custom_field', 6)
        self.assert_json_equal('', 'custom_field/@0/name', 'aaa')
        self.assert_json_equal('', 'custom_field/@0/model_title', 'contact générique')
        self.assert_json_equal('', 'custom_field/@0/kind_txt', 'Chaîne')
        self.assert_json_equal('', 'custom_field/@1/name', 'bbb')
        self.assert_json_equal('', 'custom_field/@1/model_title', 'contact générique')
        self.assert_json_equal('', 'custom_field/@1/kind_txt', 'Entier [0;100]')
        self.assert_json_equal('', 'custom_field/@2/name', 'ccc')
        self.assert_json_equal('', 'custom_field/@2/model_title', 'contact générique')
        self.assert_json_equal('', 'custom_field/@2/kind_txt', 'Réel [-10.0;10.0]')
        self.assert_json_equal('', 'custom_field/@3/name', 'ddd')
        self.assert_json_equal('', 'custom_field/@3/model_title', 'personne morale')
        self.assert_json_equal('', 'custom_field/@3/kind_txt', 'Booléen')
        self.assert_json_equal('', 'custom_field/@4/name', 'eee')
        self.assert_json_equal('', 'custom_field/@4/model_title', 'personne physique')
        self.assert_json_equal('', 'custom_field/@4/kind_txt', 'Sélection (U,V,W,X,Y,Z)')
        self.assert_json_equal('', 'custom_field/@5/name', 'fff')
        self.assert_json_equal('', 'custom_field/@5/model_title', 'personne physique')
        self.assert_json_equal('', 'custom_field/@5/kind_txt', 'Date')

    def _initial_custom_values(self):
        initial_values = [{'name': 'aaa', 'modelname': 'contacts.AbstractContact', 'kind': '0', 'args': "{'multi':False, 'min':0, 'max':0, 'prec':0, 'list':[]}"},
                          {'name': 'bbb', 'modelname': 'contacts.AbstractContact', 'kind': '1',
                           'args': "{'multi':False,'min':0, 'max':100, 'prec':0, 'list':[]}"},
                          {'name': 'ccc', 'modelname': 'contacts.AbstractContact', 'kind': '2',
                           'args': "{'multi':False,'min':-10.0, 'max':10.0, 'prec':1, 'list':[]}"},
                          {'name': 'ddd', 'modelname': 'contacts.LegalEntity', 'kind': '3',
                           'args': "{'multi':False,'min':0, 'max':0, 'prec':0, 'list':[]}"},
                          {'name': 'eee', 'modelname': 'contacts.Individual', 'kind': '4', 'args':
                           "{'multi':False,'min':0, 'max':0, 'prec':0, 'list':['U','V','W','X','Y','Z']}"},
                          {'name': 'fff', 'modelname': 'contacts.Individual', 'kind': '0', 'args': "{'multi':True,'min':0, 'max':0, 'prec':0, 'list':[]}"},
                          {'name': 'ggg', 'modelname': 'contacts.LegalEntity', 'kind': '5', 'args': "{'multi':True,'min':0, 'max':0, 'prec':0, 'list':[]}"}]
        for initial_value in initial_values:
            CustomField.objects.create(**initial_value)

    def test_custom_fields_individual(self):
        self._initial_custom_values()

        self.factory.xfer = IndividualShow()
        self.calljson('/lucterios.contacts/individualShow', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualShow')
        self.assert_count_equal('', 21)
        self.assert_json_equal('LABELFORM', 'custom_1', '')
        self.assert_json_equal('', '#custom_1/formatnum', None)
        self.assert_json_equal('LABELFORM', 'custom_2', 0)
        self.assert_json_equal('', '#custom_2/formatnum', 'N0')
        self.assert_json_equal('LABELFORM', 'custom_3', 0.0)
        self.assert_json_equal('', '#custom_3/formatnum', 'N1')
        self.assert_json_equal('LABELFORM', 'custom_5', 0)
        self.assert_json_equal('', '#custom_5/formatnum', {'0': 'U', '1': 'V', '2': 'W', '3': 'X', '4': 'Y', '5': 'Z'})
        self.assert_json_equal('LABELFORM', 'custom_6', "")
        self.assert_json_equal('', '#custom_6/formatnum', None)
        self.assertFalse("custom_7" in self.json_data.keys())

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualAddModify')
        self.assert_count_equal('', 18)
        self.assert_json_equal('EDIT', 'custom_1', '')
        self.assert_json_equal('FLOAT', 'custom_2', 0)
        self.assert_json_equal('FLOAT', 'custom_3', 0.0)
        self.assert_json_equal('SELECT', 'custom_5', 0)
        self.assert_json_equal('MEMO', 'custom_6', '')

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify', {'individual': '2', "SAVE": "YES", "custom_1": 'blabla', "custom_2": "15",
                                                                  "custom_3": "-5.4", "custom_5": "4", "custom_6": "azerty{[br/]}qwerty"}, False)

        self.factory.xfer = IndividualShow()
        self.calljson('/lucterios.contacts/individualShow', {'individual': '2'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualShow')
        self.assert_count_equal('', 21)
        self.assert_json_equal('LABELFORM', 'custom_1', 'blabla')
        self.assert_json_equal('LABELFORM', 'custom_2', 15)
        self.assert_json_equal('LABELFORM', 'custom_3', -5.4)
        self.assert_json_equal('LABELFORM', 'custom_5', 4)
        self.assert_json_equal('LABELFORM', 'custom_6', "azerty{[br/]}qwerty")

    def test_custom_fields_legalentity(self):
        self._initial_custom_values()

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_count_equal('', 22)
        self.assert_json_equal('LABELFORM', 'name', "WoldCompany")
        self.assert_json_equal('LABELFORM', 'custom_1', '')
        self.assert_json_equal('LABELFORM', 'custom_2', 0)
        self.assert_json_equal('LABELFORM', 'custom_3', 0.0)
        self.assert_json_equal('LABELFORM', 'custom_4', False)
        self.assert_json_equal('LABELFORM', 'custom_7', '1900-01-01')
        self.assert_json_equal('', '#custom_4/formatnum', 'B')
        self.assert_json_equal('', '#custom_7/formatnum', 'D')
        self.assertFalse("custom_5" in self.json_data.keys())
        self.assertFalse("custom_6" in self.json_data.keys())

        self.factory.xfer = LegalEntityAddModify()
        self.calljson('/lucterios.contacts/legalEntityAddModify',
                      {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityAddModify')
        self.assert_count_equal('', 19)
        self.assert_json_equal('EDIT', 'custom_1', '')
        self.assert_json_equal('FLOAT', 'custom_2', 0)
        self.assert_json_equal('FLOAT', 'custom_3', 0.0)
        self.assert_json_equal('CHECK', 'custom_4', 0)
        self.assert_json_equal('DATE', 'custom_7', '1900-01-01')

        self.factory.xfer = LegalEntityAddModify()
        self.calljson('/lucterios.contacts/legalEntityAddModify', {'legal_entity': '1', "SAVE": "YES", "custom_1": "n'import quoi", "custom_2": "37",
                                                                   "custom_3": "9.1", "custom_4": "1", "custom_7": "2021-05-14"}, False)

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_count_equal('', 22)
        self.assert_json_equal('LABELFORM', 'name', "WoldCompany")
        self.assert_json_equal('LABELFORM', 'custom_1', "n'import quoi")
        self.assert_json_equal('LABELFORM', 'custom_2', 37)
        self.assert_json_equal('LABELFORM', 'custom_3', 9.1)
        self.assert_json_equal('LABELFORM', 'custom_4', True)
        self.assert_json_equal('LABELFORM', 'custom_7', "2021-05-14")

    def test_custom_fields_printing(self):
        self._initial_custom_values()

        self.factory.xfer = IndividualAddModify()
        self.calljson('/lucterios.contacts/individualAddModify',
                      {'individual': '2', "SAVE": "YES", "custom_1": 'boum!', "custom_2": "-67", "custom_3": "9.9", "custom_5": "2", "custom_6": "a{[br/]}z"}, False)

        print_field_list = Individual.get_all_print_fields()
        self.assertEqual(55, len(print_field_list), print_field_list)
        print_text = ""
        for print_field_item in print_field_list:
            if 'custom_' in print_field_item[1]:
                print_text += "#%s " % print_field_item[1]
        self.assertEqual("#responsability_set.legal_entity.custom_1 #responsability_set.legal_entity.custom_2 ", print_text[:84])
        self.assertEqual("#responsability_set.legal_entity.custom_3 #responsability_set.legal_entity.custom_4 #responsability_set.legal_entity.custom_7 ", print_text[84:210])
        self.assertEqual("#OUR_DETAIL.custom_1 #OUR_DETAIL.custom_2 #OUR_DETAIL.custom_3 #OUR_DETAIL.custom_4 #OUR_DETAIL.custom_7 ", print_text[210:315])
        self.assertEqual("#custom_1 #custom_2 #custom_3 #custom_5 #custom_6 ", print_text[315:])

        indiv_jack = Individual.objects.get(id=2)
        self.assertEqual(" 0 0,0 Non 1 janvier 1900 ", indiv_jack.evaluate(print_text[210:315]))
        self.assertEqual("boum! -67 9,9 W a{[br/]}z ", indiv_jack.evaluate(print_text[315:]))

    def test_custom_fields_search(self):
        from django.db.models import Q
        self._initial_custom_values()
        custom_1 = ContactCustomField.objects.get_or_create(
            contact_id=2, field_id=1)
        custom_1[0].value = "pas beau!!!"
        custom_1[0].save()

        fieldnames = Individual.get_search_fields()
        self.assertEqual(20, len(fieldnames))
        self.assertEqual('custom_1', fieldnames[-9][0])
        self.assertEqual('custom_2', fieldnames[-8][0])
        self.assertEqual('custom_3', fieldnames[-7][0])
        self.assertEqual('custom_5', fieldnames[-6][0])
        self.assertEqual('custom_6', fieldnames[-5][0])

        filter_result, desc_result = get_search_query_from_criteria(
            "", Individual)
        self.assertEqual({}, desc_result)
        self.assertEqual(str(Q()), str(filter_result))

        filter_result, desc_result = get_search_query_from_criteria(
            "custom_1||5||beau", Individual)
        self.assertEqual({'0': '{[b]}aaa{[/b]} contient {[i]}"beau"{[/i]}'}, desc_result)
        q_res = Q(contactcustomfield__field__id=1) & Q(
            **{'contactcustomfield__value__icontains': 'beau'})
        self.assertEqual(str(q_res), str(filter_result))

        find_indiv = list(Individual.objects.filter(q_res))
        self.assertEqual(1, len(find_indiv), find_indiv)

    def test_duplicate_merge(self):
        self._initial_custom_values()
        self.factory.xfer = AbstractContactFindDouble()
        self.calljson('/lucterios.contacts/abstractContactFindDouble',
                      {'modelname': 'contacts.Individual', 'field_id': 'individual'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'abstractContactFindDouble')
        self.assert_count_equal('', 3)
        self.assert_coordcomp_equal('individual', (0, 1, 2, 1))
        self.assert_count_equal('individual', 0)

        create_jack()

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 2)

        self.factory.xfer = AbstractContactFindDouble()
        self.calljson('/lucterios.contacts/abstractContactFindDouble',
                      {'modelname': 'contacts.Individual', 'field_id': 'individual'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'abstractContactFindDouble')
        self.assert_count_equal('individual', 2)
        self.assert_json_equal('', 'individual/@0/id', '2')
        self.assert_json_equal('', 'individual/@1/id', '3')

        self.factory.xfer = ObjectMerge()
        self.calljson('/CORE/objectMerge',
                      {'modelname': 'contacts.Individual', 'field_id': 'individual', 'individual': '2;3'}, False)
        self.assert_observer('core.custom', 'CORE', 'objectMerge')
        self.assert_count_equal('', 2)
        self.assert_grid_equal('mrg_object', {'value': 'désignation', 'select': 'principal?'}, 2)  # nb=2
        self.assert_json_equal('', 'mrg_object/@0/value', 'MISTER jack')
        self.assert_json_equal('', 'mrg_object/@0/select', True)
        self.assert_json_equal('', 'mrg_object/@1/value', 'MISTER jack')
        self.assert_json_equal('', 'mrg_object/@1/select', False)

        self.factory.xfer = ObjectMerge()
        self.calljson('/CORE/objectMerge',
                      {'modelname': 'contacts.Individual', 'field_id': 'individual', 'individual': '2;3', 'CONFIRME': 'OPEN', 'mrg_object': '3'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'objectMerge')
        self.assert_action_equal('GET', self.response_json['action'], ('Editer', 'mdi:mdi-text-box-outline', 'lucterios.contacts', 'individualShow', 1, 1, 1, {"individual": 3}))

        self.factory.xfer = ObjectMerge()
        self.calljson('/CORE/objectMerge',
                      {'modelname': 'contacts.Individual', 'field_id': 'individual', 'individual': '2;3', 'mrg_object': '3'}, False)
        self.assert_observer('core.custom', 'CORE', 'objectMerge')
        self.assert_json_equal('', 'mrg_object/@0/value', 'MISTER jack')
        self.assert_json_equal('', 'mrg_object/@0/select', False)
        self.assert_json_equal('', 'mrg_object/@1/value', 'MISTER jack')
        self.assert_json_equal('', 'mrg_object/@1/select', True)

        self.factory.xfer = ObjectMerge()
        self.calljson('/CORE/objectMerge',
                      {'modelname': 'contacts.Individual', 'field_id': 'individual', 'individual': '2;3', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'objectMerge')
        self.assert_action_equal('GET', self.response_json['action'], ('Editer', 'mdi:mdi-text-box-outline', 'lucterios.contacts', 'individualShow', 1, 1, 1, {"individual": "2"}))

        self.factory.xfer = IndividualList()
        self.calljson('/lucterios.contacts/individualList', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'individualList')
        self.assert_count_equal('individual', 1)

        self.factory.xfer = AbstractContactShow()
        self.calljson('/lucterios.contacts/abstractContactShow',
                      {"abstractcontact": "2"}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'abstractContactShow')
        self.assert_count_equal('', 21)
        self.assert_json_equal('LABELFORM', 'genre', 1)
        self.assert_json_equal('LABELFORM', 'firstname', "jack")
        self.assert_json_equal('LABELFORM', 'lastname', "MISTER")
        self.assert_json_equal('LINK', 'email', "jack@worldcompany.com")

    def test_merge_legalentities(self):
        entity1 = LegalEntity.objects.create(name='entity1')
        entity2 = LegalEntity.objects.create(name='entity2')
        indiv1 = Individual.objects.create(genre=1, firstname="Avrel", lastname="Dalton")
        indiv2 = Individual.objects.create(genre=1, firstname="Lucky", lastname="Luke")
        indiv3 = Individual.objects.create(genre=2, firstname="Ma'a", lastname="Dalton")

        resp = Responsability.objects.create(legal_entity=entity1, individual=indiv1)
        resp.functions.set(Function.objects.filter(id__in=[1, 2]))
        resp = Responsability.objects.create(legal_entity=entity1, individual=indiv2)
        resp.functions.set(Function.objects.filter(id__in=[3]))
        resp = Responsability.objects.create(legal_entity=entity2, individual=indiv2)
        resp.functions.set(Function.objects.filter(id__in=[1, 3]))
        resp = Responsability.objects.create(legal_entity=entity2, individual=indiv3)
        resp.functions.set(Function.objects.filter(id__in=[2]))

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': entity1.id}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_json_equal('LABELFORM', 'name', "entity1")
        self.assert_count_equal('responsability', 2)
        self.assert_json_equal('', 'responsability/@0/individual', "Dalton Avrel")
        self.assert_json_equal('', 'responsability/@0/functions', ['President', 'Secretaire'])
        self.assert_json_equal('', 'responsability/@1/individual', "Luke Lucky")
        self.assert_json_equal('', 'responsability/@1/functions', ['Tresorier'])

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': entity2.id}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_json_equal('LABELFORM', 'name', "entity2")
        self.assert_count_equal('responsability', 2)
        self.assert_json_equal('', 'responsability/@0/individual', "Luke Lucky")
        self.assert_json_equal('', 'responsability/@0/functions', ['President', 'Tresorier'])
        self.assert_json_equal('', 'responsability/@1/individual', "Dalton Ma'a")
        self.assert_json_equal('', 'responsability/@1/functions', ['Secretaire'])

        self.factory.xfer = ObjectMerge()
        self.calljson('/CORE/objectMerge', {'modelname': 'contacts.LegalEntity', 'field_id': 'legalentity',
                                            'legalentity': '%d;%d' % (entity1.id, entity2.id), 'mrg_object': entity2.id, 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'CORE', 'objectMerge')

        self.factory.xfer = LegalEntityShow()
        self.calljson('/lucterios.contacts/legalEntityShow', {'legal_entity': entity2.id}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'legalEntityShow')
        self.assert_json_equal('LABELFORM', 'name', "entity2")
        self.assert_count_equal('responsability', 3)
        self.assert_json_equal('', 'responsability/@0/individual', "Dalton Avrel")
        self.assert_json_equal('', 'responsability/@0/functions', ['President', 'Secretaire'])
        self.assert_json_equal('', 'responsability/@1/individual', "Luke Lucky")
        self.assert_json_equal('', 'responsability/@1/functions', ['President', 'Tresorier'])
        self.assert_json_equal('', 'responsability/@2/individual', "Dalton Ma'a")
        self.assert_json_equal('', 'responsability/@2/functions', ['Secretaire'])

    def test_import_contacts(self):
        csv_content = """value;nom;adresse;codePostal;ville;fixe;portable;mail;Num;Type;OtherDate
4.6;USIF;37 avenue de la plage;99673;TOUINTOUIN;0502851031;0439423854;pierre572@free.fr;1000029;Type B;2021-01-02
7.1;NOJAXU;11 avenue du puisatier;99247;BELLEVUE;0022456300;0020055601;amandine723@hotmail.fr;1000030;Type A;2021-03-04
2.9;GOC;33 impasse du 11 novembre;99150;BIDON SUR MER;0632763718;0310231012;marie762@free.fr;1000031;Type C;2021-05-06
5.4;UHADIK;1 impasse de l'Oisan;99410;VIENVITEVOIR;0699821944;0873988470;marie439@orange.fr;1000032;Type B;2021-07-08
7.1;NOJAXU;11 avenue du puisatier;99247;BELLEVUE;0022456300;0020055601;amandine723@hotmail.fr;1000030;Type A;2021-09-10
"""
        self._initial_custom_values()

        self.factory.xfer = ContactImport()
        self.calljson('/lucterios.contacts/contactImport', {}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'contactImport')
        self.assert_count_equal('', 9)
        self.assertEqual(len(self.json_actions), 1)
        self.assert_action_equal('POST', self.json_actions[0], ('Annuler', 'mdi:mdi-cancel'))

        self.factory.xfer = ContactImport()
        self.calljson('/lucterios.contacts/contactImport', {'step': 2, 'modelname': 'contacts.LegalEntity', 'quotechar': "'",
                                                            'delimiter': ';', 'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'importcontent': StringIO(csv_content)}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'contactImport')
        self.assert_count_equal('', 7 + 18)
        self.assert_attrib_equal("fld_name", 'description', "dénomination")
        self.assert_select_equal('fld_name', 11)  # nb=10
        self.assert_select_equal('fld_structure_type', 12)  # nb=11
        self.assert_select_equal('fld_address', 11)  # nb=10
        self.assert_select_equal('fld_postal_code', 11)  # nb=10
        self.assert_select_equal('fld_city', 11)  # nb=10
        self.assert_select_equal('fld_country', 12)  # nb=11
        self.assert_select_equal('fld_tel1', 12)  # nb=11
        self.assert_select_equal('fld_tel2', 12)  # nb=11
        self.assert_select_equal('fld_email', 12)  # nb=11
        self.assert_select_equal('fld_comment', 12)  # nb=11
        self.assert_select_equal('fld_legal_identification', 12)  # nb=11
        self.assert_select_equal('fld_vat_identification', 12)  # nb=11
        self.assert_select_equal('fld_identify_number', 12)  # nb=11
        self.assert_select_equal('fld_custom_1', 12)  # nb=11
        self.assert_select_equal('fld_custom_2', 12)  # nb=11
        self.assert_select_equal('fld_custom_3', 12)  # nb=11
        self.assert_select_equal('fld_custom_4', 12)  # nb=11
        self.assert_select_equal('fld_custom_7', 12)  # nb=11
        cases_id = []
        cases_val = []
        for case_idx in range(1, 13):
            json_value = self.get_json_path("#fld_custom_4/case/@%d" % (case_idx - 1))
            cases_id.append(str(json_value[0]))
            cases_val.append(str(json_value[1]))
        self.assertEqual("|value|nom|adresse|codePostal|ville|fixe|portable|mail|Num|Type|OtherDate", "|".join(cases_id))
        self.assertEqual("None|value|nom|adresse|codePostal|ville|fixe|portable|mail|Num|Type|OtherDate", "|".join(cases_val))
        self.assert_grid_equal('Array', {'value': 'value', 'nom': 'nom', 'adresse': 'adresse', 'codePostal': 'codePostal', 'ville': 'ville', 'fixe': 'fixe', 'portable': 'portable', 'mail': 'mail', 'Num': 'Num', 'Type': 'Type', 'OtherDate': 'OtherDate'}, 5)  # nb=10
        self.assert_count_equal('Array', 5)
        self.assert_count_equal('#Array/actions', 0)
        self.assertEqual(len(self.json_actions), 1)
        self.assert_action_equal('POST', self.json_actions[0], ('Annuler', 'mdi:mdi-cancel'))
        self.assertEqual(len(self.json_context), 8)

        self.factory.xfer = ContactImport()
        self.calljson('/lucterios.contacts/contactImport', {'step': 3, 'modelname': 'contacts.LegalEntity', 'quotechar': "'", 'delimiter': ';', 'encoding': 'utf-8',
                                                            'dateformat': '%d/%m/%Y', 'importcontent0': csv_content, "fld_name": "nom", "fld_structure_type": "Type",
                                                            "fld_address": "adresse", "fld_postal_code": "codePostal", "fld_city": "ville", "fld_tel1": "fixe",
                                                            "fld_email": "mail", "fld_identify_number": "Num", "fld_custom_3": "value", "fld_custom_7": 'OtherDate'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'contactImport')
        self.assert_count_equal('', 5)
        self.assert_grid_equal('Array', {"name": "dénomination", "structure_type": "type de structure", "address": "adresse",
                                         "postal_code": "code postal", "city": "ville", "tel1": "tel1", "email": "courriel",
                                         "identify_number": "autres informations d'identification", "custom_3": "ccc", "custom_7": 'ggg'}, 5)
        self.assert_count_equal('#Array/actions', 0)
        self.assertEqual(len(self.json_actions), 1)
        self.assert_action_equal('POST', self.json_actions[0], ('Annuler', 'mdi:mdi-cancel'))

        self.factory.xfer = ContactImport()
        self.calljson('/lucterios.contacts/contactImport', {'step': 4, 'modelname': 'contacts.LegalEntity', 'quotechar': "'", 'delimiter': ';', 'encoding': 'utf-8',
                                                            'dateformat': '%d/%m/%Y', 'importcontent0': csv_content, "fld_name": "nom", "fld_structure_type": "Type",
                                                            "fld_address": "adresse", "fld_postal_code": "codePostal", "fld_city": "ville", "fld_tel1": "fixe",
                                                            "fld_email": "mail", "fld_identify_number": "Num", "fld_custom_3": "value", "fld_custom_7": 'OtherDate'}, False)
        self.assert_observer('core.custom', 'lucterios.contacts', 'contactImport')
        self.assert_count_equal('', 3)
        self.assert_json_equal('LABELFORM', 'result', "4 éléments ont été importés")
        self.assert_json_equal('LABELFORM', 'import_error', [])
        self.assertEqual(len(self.json_actions), 1)

        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {}, False)
        self.assert_count_equal('legal_entity', 5)
        self.assert_json_equal('', 'legal_entity/@0/name', 'GOC')
        self.assert_json_equal('', 'legal_entity/@1/name', 'NOJAXU')
        self.assert_json_equal('', 'legal_entity/@2/name', 'UHADIK')
        self.assert_json_equal('', 'legal_entity/@3/name', 'USIF')
        self.assert_json_equal('', 'legal_entity/@4/name', 'WoldCompany')

        self.factory.xfer = LegalEntityList()
        self.calljson('/lucterios.contacts/legalEntityList', {"structure_type": 2}, False)
        self.assert_count_equal('legal_entity', 2)
