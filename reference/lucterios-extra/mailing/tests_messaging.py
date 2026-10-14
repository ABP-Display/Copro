# -*- coding: utf-8 -*-
'''
lucterios.contacts package

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
from base64 import b64decode
from time import sleep
import logging


from lucterios.framework.test import LucteriosTest, AsychronousLucteriosTest
from lucterios.framework.model_fields import LucteriosScheduler
from lucterios.CORE.models import LucteriosUser, PrintModel

from lucterios.contacts.test_tools import change_ourdetail, create_jack

from lucterios.documents.tests import create_doc
from lucterios.documents.models import DocumentContainer

from lucterios.mailing.models import Message
from lucterios.mailing.email_functions import will_mail_send
from lucterios.mailing.views_message import MessageAddModify, MessageDel, MessageShow, MessageValidRecipient, MessageDelRecipient, MessageLetter, MessageTransition, MessageInsertDoc, \
    MessageValidInsertDoc, MessageRemoveDoc, MessageSendEmailTry, MessageEmailList, MessageSMSList, \
    MessageSendSMSTry, MessageShowDoc
from lucterios.mailing.test_tools import configSMTP, decode_b64, TestReceiver, \
    configSMS, clean_sms_testfile, read_sms
from lucterios.mailing.sms_functions import AbstractProvider
from lucterios.contacts.models import CustomField

if len(logging.getLogger("lucterios.mailing.test").handlers) == 0:
    logging.getLogger("lucterios.mailing.test").addHandler(logging.StreamHandler())


class MailingTest(LucteriosTest):

    smtp_port = 1225

    def setUp(self):
        LucteriosTest.setUp(self)
        change_ourdetail()
        self.jack = create_jack(firstname="jack", lastname="MISTER", with_email=True)
        self.jean = create_jack(firstname="jean", lastname="Valjean", with_email=False)
        MailingTest.smtp_port += 1
        self.maxDiff = None
        logging.getLogger("lucterios.mailing.test").setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger("lucterios.mailing.test").setLevel(logging.NOTSET)
        LucteriosTest.tearDown(self)

    def test_messages(self):
        self.factory.xfer = MessageEmailList()
        self.calljson('/lucterios.mailing/messageEmailList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageEmailList')
        self.assertEqual(len(self.json_context), 1)
        self.assertEqual(self.json_context['message_type'], 0)
        self.assert_count_equal("message", 0)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageAddModify')
        self.assert_count_equal('', 4)
        self.assert_json_equal('EDIT', "subject", "")
        self.assert_json_equal('MEMO', "body", "")
        self.assert_json_equal('CHECK', "doc_in_link", False)
        self.assert_json_equal('', "#subject/description", "sujet")
        self.assert_json_equal('', "#body/with_hypertext", True)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'doc_in_link': 0, 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageEmailList()
        self.calljson('/lucterios.mailing/messageEmailList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageEmailList')
        self.assert_count_equal("message", 1)
        self.assert_json_equal('', "message/@0/status", 0)
        self.assert_json_equal('', "message/@0/date", None)
        self.assert_json_equal('', "#message/headers/@2/@1", 'sujet')
        self.assert_json_equal('', "message/@0/subject", 'new message')

        self.factory.xfer = MessageSMSList()
        self.calljson('/lucterios.mailing/messageSMSList', {}, False)
        self.assert_count_equal("message", 0)

        self.factory.xfer = MessageDel()
        self.calljson('/lucterios.mailing/messageDel',
                      {'message': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDel')

        self.factory.xfer = MessageEmailList()
        self.calljson('/lucterios.mailing/messageEmailList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageEmailList')
        self.assert_count_equal("message", 0)

    def test_show_message(self):
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_json_equal('LABELFORM', "date", None)
        self.assert_json_equal('', "#subject/description", "sujet")
        self.assert_json_equal('LABELFORM', "subject", "new message")
        self.assert_json_equal('LABELFORM', "body", "{[div style='border:1px solid black;background-color:#EEE;padding:5px;']}{[b]}", txtrange=True)
        self.assert_count_equal("recipient_list", 0)
        self.assert_count_equal("attachment", 0)
        self.assert_json_equal('LABELFORM', 'doc_in_link', False)

        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[0], ('Modifier', 'mdi:mdi-pencil-outline', 'lucterios.mailing', 'messageAddModify', 1, 1, 0))
        self.assert_action_equal('POST', self.json_actions[1], ('Fermer', 'mdi:mdi-close'))

        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.AbstractContact', 'CRITERIA': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': 'name||5||truc'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 13)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal('POST', self.json_actions[0], ('Valider', 'mdi:mdi-share', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'valid'}))
        self.assert_action_equal('POST', self.json_actions[1], ('Modifier', 'mdi:mdi-pencil-outline', 'lucterios.mailing', 'messageAddModify', 1, 1, 0))
        self.assert_action_equal('POST', self.json_actions[2], ('Fermer', 'mdi:mdi-close'))
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_count_equal("#recipient_list/actions", 2)
        self.assert_count_equal("recipient_list", 3)
        self.assert_json_equal('', "recipient_list/@0/model", "Personne Physique")
        self.assert_json_equal('', "recipient_list/@0/filter", '{[b]}genre{[/b]} égal {[i]}"Homme"{[/i]}')
        self.assert_json_equal('', "recipient_list/@1/model", "Contact Générique")
        self.assert_json_equal('', "recipient_list/@2/model", "Personne Morale")
        self.assert_json_equal('LABELFORM', "contact_nb", 5)

        self.factory.xfer = MessageDelRecipient()
        self.calljson('/lucterios.mailing/messageDelRecipient',
                      {'message': '1', 'recipient_list': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDelRecipient')
        self.factory.xfer = MessageDelRecipient()
        self.calljson('/lucterios.mailing/messageDelRecipient',
                      {'message': '1', 'recipient_list': '0', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDelRecipient')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 13)
        self.assert_count_equal("recipient_list", 1)
        self.assert_json_equal('LABELFORM', "contact_nb", 0)

    def test_validate_message(self):
        configSMTP('', 25)
        self.assertFalse(will_mail_send(), 'no email')
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.assertFalse(will_mail_send(), 'no email')
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', "status", 1)
        self.assert_count_equal("#recipient_list/actions", 0)
        self.assert_count_equal("recipient_list", 2)
        self.assert_json_equal('LABELFORM', "contact_nb", '3')
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('GET', self.json_actions[0], ('Lettres', 'mdi:mdi-file-sign', 'lucterios.mailing', 'messageLetter', 0, 1, 0))
        self.assert_action_equal('POST', self.json_actions[1], ('Fermer', 'mdi:mdi-close'))

        configSMTP('localhost', MailingTest.smtp_port)
        self.assertTrue(will_mail_send(), 'with email')
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 14)
        self.assert_json_equal('LABELFORM', "contact_noemail", ['Valjean jean'])
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal('POST', self.json_actions[0], ('Courriels', 'mdi:mdi-email-outline', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'sending'}))
        self.assert_action_equal('GET', self.json_actions[1], ('Lettres', 'mdi:mdi-file-sign', 'lucterios.mailing', 'messageLetter', 0, 1, 0))
        self.assert_action_equal('POST', self.json_actions[2], ('Fermer', 'mdi:mdi-close'))

        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'sending'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'messageTransition')
        self.assert_json_equal('', 'text', 'Voulez-vous envoyer ce message à 2 contacts ?')

    def test_letter_message(self):
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.factory.xfer = MessageLetter()
        self.calljson('/lucterios.mailing/messageLetter', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageLetter')
        self.assert_json_equal('SELECT', "MODEL", '5')

        self.factory.xfer = MessageLetter()
        self.calljson('/lucterios.mailing/messageLetter',
                      {'message': '1', 'PRINT_MODE': '3', 'MODEL': 5}, False)
        self.assert_observer('core.print', 'lucterios.mailing', 'messageLetter')
        self.save_pdf()

    def test_letter_message_html(self):
        html_content = """
{[p]}{[u]}{[b]}{[span style="font-size:24px;"]}Titre{[/span]}{[/b]}{[/u]}{[/p]}
Lorem ipsum dolor sit amet, consectetur adipiscing elit. Tu enim ista lenius, hic Stoicorum more nos vexat.{[br]}
{[i]}Quando enim Socrates, qui parens philosophiae iure dici potest, quicquam tale fecit?{[/i]}{[br]}
{[strike]}Quodsi ipsam honestatem undique pertectam atque absolutam. Duo Reges: constructio interrete.{[/strike]}{[br]}
Quid ad utilitatem tantae pecuniae? Sed nimis multa.{[br]}
{[br]}
Choix:{[br]}
{[ul]}{[li]}{[span style="color:rgb(0,0,255);"]}Bleu{[/span]}{[/li]}{[li]}{[span style="color:rgb(255,0,0);"]}Rouge{[/span]}{[/li]}{[li]}{[span style="color:rgb(255,255,0);"]}Jaune{[/span]}{[/li]}{[/ul]}
{[blockquote]}Multoque hoc melius nos veriusque quam Stoici.{[br]}
Ea possunt paria non esse.{[br]}
Cui Tubuli nomen odio non est?{[br]}
Quamquam tu hanc copiosiorem etiam soles dicere.{[br]}
Ita redarguitur ipse a sese, convincunturque scripta eius probitate ipsius ac moribus.{[br]}
Varietates autem iniurasque fortunae facile veteres philosophorum praeceptis instituta vita superabat.{[br]}
Tum Quintus: Est plane, Piso, ut dicis, inquit. Id est enim, de quo quaerimus.{[br]}
Nec mihi illud dixeris: Haec enim ipsa mihi sunt voluptati, et erant illa Torquatis.{[br]}
Deque his rebus satis multa in nostris de re publica libris sunt dicta a Laelio.{[br]}
{[/blockquote]}{[br]}
{[hr]}
{[p]}{[br]}
{[/p]}
{[p align="left"]}A Gauche{[/p]}
{[p align="center"]}Au Centre{[br]}
{[/p]}
{[p align="right"]}A Droite{[br]}
{[/p]}
{[br]}
{[blockquote]}{[blockquote]}{[b]}Adresse:{[/b]} {[a href="https://www.diacamma.org"]}diacamma.org{[/a]}{[br]}
{[/blockquote]}{[/blockquote]}{[p]}{[br]}
{[/p]}
{[p]}{[i]}Grosses papouille{[/i]}{[/p]}
{[p]}{[/p]}
"""

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'subject': 'new message', 'body': html_content}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)

        self.factory.xfer = MessageLetter()
        self.calljson('/lucterios.mailing/messageLetter', {'message': '1', 'PRINT_MODE': '3', 'MODEL': 5}, False)
        self.assert_observer('core.print', 'lucterios.mailing', 'messageLetter')
        self.save_pdf()

    def test_manage_docs(self):
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()

        create_doc(self.factory.user, with_folder=False)
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'doc_in_link': 0, 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_grid_equal('attachment', {"name": 'nom', "description": 'description', "date_modification": 'date de modification'}, 0)
        self.assert_json_equal('LABELFORM', "doc_in_link", False)
        self.assert_count_equal("#attachment/actions", 3)
        self.assert_action_equal('GET', "#attachment/actions/@0", ('Editer', 'mdi:mdi-text-box-outline', 'lucterios.mailing', 'messageShowDoc', 0, 1, 0))
        self.assert_action_equal('DELETE', "#attachment/actions/@1", ('Retirer', 'mdi:mdi-delete-outline', 'lucterios.mailing', 'messageRemoveDoc', 0, 1, 2))
        self.assert_action_equal('POST', "#attachment/actions/@2", ('Insérer', 'mdi:mdi-pencil-plus-outline', 'lucterios.mailing', 'messageInsertDoc', 0, 1, 1))

        self.factory.xfer = MessageInsertDoc()
        self.calljson('/lucterios.mailing/messageInsertDoc', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageInsertDoc')
        self.assert_count_equal("document", 3)
        self.assert_count_equal("#document/actions", 2)
        self.assert_action_equal('POST', "#document/actions/@0", ('Sélection', 'mdi:mdi-check', 'lucterios.mailing', 'messageValidInsertDoc', 1, 1, 0))

        self.factory.xfer = MessageValidInsertDoc()
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '1'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidInsertDoc')
        self.factory.xfer = MessageValidInsertDoc()
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '3'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidInsertDoc')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_count_equal("attachment", 2)
        self.assert_json_equal('', "attachment/@0/id", 1)
        self.assert_json_equal('', "attachment/@0/name", 'doc1.png')
        self.assert_json_equal('', "attachment/@1/id", 3)
        self.assert_json_equal('', "attachment/@1/name", 'doc3.png')
        self.assert_count_equal("#attachment/actions", 3)
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = MessageShowDoc()
        self.calljson('/lucterios.mailing/messageShowDoc', {'message': '1', 'attachment': '3'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageShowDoc')
        self.assert_action_equal('GET', self.response_json['action'], ('Editer', "mdi:mdi-text-box-outline", "lucterios.documents", "documentShow", 1, 1, 1, {"document": 3}))

        self.factory.xfer = MessageRemoveDoc()
        self.calljson('/lucterios.mailing/messageRemoveDoc',
                      {'message': '1', 'attachment': '1;2', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageRemoveDoc')

        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_count_equal("attachment", 1)
        self.assert_json_equal('', "attachment/@0/id", 3)
        self.assert_json_equal('', "attachment/@0/name", 'doc3.png')
        self.assert_count_equal("#attachment/actions", 3)
        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', "status", 1)
        self.assert_count_equal("attachment", 1)
        self.assert_count_equal("#attachment/actions", 1)

    def test_trysend(self):
        configSMTP('', 25)
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'subject': 'new message', 'body':
                                                              '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'}, False)

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assertEqual(len(self.json_actions), 2)

        configSMTP('localhost', MailingTest.smtp_port)
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assertEqual(len(self.json_actions), 3)

        server = TestReceiver()
        server.start(MailingTest.smtp_port)
        try:
            self.assertEqual(0, server.count())
            self.factory.xfer = MessageSendEmailTry()
            self.calljson('/lucterios.mailing/messageSendEmailTry', {'message': '1'}, False)
            self.assert_observer('core.custom', 'lucterios.mailing', 'messageSendEmailTry')
            self.assert_json_equal('EDIT', "recipient", 'mr-sylvestre@worldcompany.com')

            self.factory.xfer = MessageSendEmailTry()
            self.calljson('/lucterios.mailing/messageSendEmailTry', {'message': '1', 'CONFIRME': 'YES', "recipient": 'behoa@worldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.mailing', 'messageSendEmailTry')
            self.assert_json_equal('', 'text', 'Courriel envoyé, veuillez le vérifier.')
            self.assert_json_equal('', 'type', 1)

            self.factory.xfer = MessageSendEmailTry()
            self.calljson('/lucterios.mailing/messageSendEmailTry', {'message': '1', 'CONFIRME': 'YES', "recipient": 'behoaworldcompany.com'}, False)
            self.assert_observer('core.dialogbox', 'lucterios.mailing', 'messageSendEmailTry')
            self.assert_json_equal('', 'text', 'Destinataires non valides !')
            self.assert_json_equal('', 'type', 4)

            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['behoa@worldcompany.com'], server.get(0)[2])
        finally:
            server.stop()

    def test_send_classic(self):
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()
        create_doc(self.factory.user, with_folder=False)

        configSMTP('localhost', MailingTest.smtp_port)
        server = TestReceiver()
        server.start(MailingTest.smtp_port)
        try:
            email_msg = Message.objects.create(subject="Sending '#reference'", body="{[b]}#name{[/b]}{[br/]}{[br/]}With Document: {[i]}#doc{[/i]}{[br/]}{[br/]}Bye", message_type=0)
            email_msg.add_recipient('contacts.Individual', 'genre||8||1')
            email_msg.add_recipient('contacts.LegalEntity', '')
            email_msg.save()
            email_msg.attachments.add(DocumentContainer.objects.get(id=1))
            email_msg.valid()
            self.assertEqual(3, email_msg.contact_nb)
            self.assertEqual(['Valjean jean'], email_msg.contact_noemail)
            email_msg.prep_sending()
            email_msg.status = 2
            email_msg.save()
            self.assertEqual(0, server.count())

            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(2, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(1)[1])
            self.assertEqual(['jack@worldcompany.com'], server.get(1)[2])

            msg_txt, msg, msg_file1 = server.get_msg_index(0, "Sending ''")

            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("<html><body><b>WoldCompany</b><br/><br/>With Document: <i>doc1.png</i><br/><br/>Bye<img src='http://testserver/lucterios.mailing/emailSentAddForStatistic?emailsent=1' alt=''/></body></html>",
                             decode_b64(msg.get_payload()))

            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('base64', msg_txt.get('Content-Transfer-Encoding', ''))
            self.assertEqual('**WoldCompany**  \n  \nWith Document: _doc1.png_  \n  \nBye\n\n', decode_b64(msg_txt.get_payload()))

            self.assertTrue('doc1.png' in msg_file1.get('Content-Type', ''), msg_file1.get('Content-Type', ''))
        finally:
            server.stop()

    def test_send_classic_with_bad_email(self):
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()

        self.jack.email = self.jack.email + ';titi@machin.com'
        self.jack.save()

        configSMTP('localhost', MailingTest.smtp_port)
        server = TestReceiver()
        server.start(MailingTest.smtp_port)
        server.smtp.wrong_email = 'titi@machin.com'
        try:
            email_msg = Message.objects.create(subject="Sending '#reference'", body="{[b]}#name{[/b]}{[br/]}{[br/]}With Document: {[i]}#doc{[/i]}{[br/]}{[br/]}Bye", message_type=0)
            email_msg.add_recipient('contacts.Individual', 'genre||8||1')
            email_msg.add_recipient('contacts.LegalEntity', '')
            email_msg.save()
            self.assertEqual(3, email_msg.contact_nb)
            self.assertEqual(['Valjean jean'], email_msg.contact_noemail)
            email_msg.prep_sending()
            email_msg.status = 2
            email_msg.save()
            self.assertEqual(0, server.count())

            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(2, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(1)[1])
            self.assertEqual(['jack@worldcompany.com'], server.get(1)[2])

            email_sent_list = email_msg.emailsent_set.all()
            self.assertEqual(3, len(email_sent_list))
            self.assertEqual('mr-sylvestre@worldcompany.com', email_sent_list[0].email)
            self.assertEqual('', email_sent_list[0].error)
            self.assertEqual('titi@machin.com', email_sent_list[1].email)
            self.assertEqual("{'titi@machin.com': (550, b'Bad <address> : titi@machin.com')}", email_sent_list[1].error)
            self.assertEqual('jack@worldcompany.com', email_sent_list[2].email)
            self.assertEqual('', email_sent_list[2].error)
        finally:
            server.stop()

    def get_print_model(self):
        print_model = PrintModel.objects.create(name="Report", kind="2", modelname="contacts.Individual")
        print_model.value = """
    <model hmargin="10.0" vmargin="10.0" page_width="210.0" page_height="297.0">
    <header extent="0.0"/>
    <bottom extent="0.0"/>
    <body>
    <text height="8.0" width="190.0" top="0.0" left="0.0" padding="1.0" spacing="0.0" border_color="black" border_style="" border_width="0.2" text_align="center" line_height="15" font_family="sans-serif" font_weight="" font_size="15">
    {[b]}#firstname #lastname{[/b]}
    </text>
    </body>
    </model>
    """
        print_model.save()
        return print_model

    def test_send_dynamic(self):
        print_model = self.get_print_model()

        create_jack(firstname="jack", lastname='Dalton')
        create_jack(firstname="joe", lastname='Dalton')
        create_jack(firstname="wiliam", lastname='Dalton')
        create_jack(firstname="avrel", lastname='Dalton')

        configSMTP('localhost', MailingTest.smtp_port)
        server = TestReceiver()
        server.start(MailingTest.smtp_port)
        try:
            email_msg = Message.objects.create(subject="Sending '#reference'", body="{[b]}#name{[/b]}{[br/]}{[br/]}With Document: {[i]}#doc{[/i]}{[br/]}{[br/]}Bye",
                                               email_to_send="contacts.Individual:0:%d" % print_model.id, message_type=0)
            email_msg.add_recipient('contacts.Individual', 'id||8||4;5;6;7')
            email_msg.save()
            email_msg.valid()
            self.assertEqual(4, email_msg.contact_nb)
            self.assertEqual([], email_msg.contact_noemail)
            email_msg.prep_sending()
            email_msg.status = 2
            email_msg.save()
            self.assertEqual(0, server.count())

            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(4, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['jack@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(0)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(1)[1])
            self.assertEqual(['joe@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(1)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(2)[1])
            self.assertEqual(['wiliam@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(2)[2])
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(3)[1])
            self.assertEqual(['avrel@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(3)[2])

            msg_txt, msg, msg_file1 = server.get_msg_index(2, "Sending '6'")

            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("<html><body><b>wiliam Dalton</b><br/><br/>With Document: <i>Report.pdf</i><br/><br/>Bye<img src='http://testserver/lucterios.mailing/emailSentAddForStatistic?emailsent=3' alt=''/></body></html>",
                             decode_b64(msg.get_payload()))

            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('base64', msg_txt.get('Content-Transfer-Encoding', ''))
            self.assertEqual('**wiliam Dalton**  \n  \nWith Document: _Report.pdf_  \n  \nBye\n\n', decode_b64(msg_txt.get_payload()))

            self.assertTrue('Report.pdf' in msg_file1.get('Content-Type', ''), msg_file1.get('Content-Type', ''))
            for msg_index in range(4):
                _msg, _msg_txt, msg_file = server.get_msg_index(msg_index)
                self.save_pdf(base64_content=msg_file.get_payload(), ident=msg_index + 1)
        finally:
            server.stop()

    def test_send_dynamic_with_bad_email(self):
        print_model = self.get_print_model()

        jack = create_jack(firstname="jack", lastname='Dalton')
        create_jack(firstname="joe", lastname='Dalton')
        create_jack(firstname="wiliam", lastname='Dalton')
        create_jack(firstname="avrel", lastname='Dalton')
        jack.email = self.jack.email + ';titi@machin.com'
        jack.save()

        configSMTP('localhost', MailingTest.smtp_port)
        server = TestReceiver()
        server.start(MailingTest.smtp_port)
        server.smtp.wrong_email = 'titi@machin.com'
        try:
            email_msg = Message.objects.create(subject="Sending '#reference'", body="{[b]}#name{[/b]}{[br/]}{[br/]}With Document: {[i]}#doc{[/i]}{[br/]}{[br/]}Bye",
                                               email_to_send="contacts.Individual:0:%d" % print_model.id, message_type=0)
            email_msg.add_recipient('contacts.Individual', 'id||8||4;5;6;7')
            email_msg.save()
            email_msg.valid()
            self.assertEqual(4, email_msg.contact_nb)
            self.assertEqual([], email_msg.contact_noemail)
            email_msg.prep_sending()
            email_msg.status = 2
            email_msg.save()
            self.assertEqual(0, server.count())

            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(4, server.count())

            self.assertEqual(['jack@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(0)[2])
            server.get_msg_index(0, params={'To': 'jack@worldcompany.com, titi@machin.com', 'Cc': ''})

            self.assertEqual(['joe@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(1)[2])
            server.get_msg_index(1, params={'To': 'joe@worldcompany.com', 'Cc': ''})

            self.assertEqual(['wiliam@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(2)[2])
            server.get_msg_index(2, params={'To': 'wiliam@worldcompany.com', 'Cc': ''})

            self.assertEqual(['avrel@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(3)[2])
            server.get_msg_index(3, params={'To': 'avrel@worldcompany.com', 'Cc': ''})

            email_sent_list = email_msg.emailsent_set.all()
            self.assertEqual(4, len(email_sent_list))
            self.assertEqual(['jack@worldcompany.com;titi@machin.com'], email_sent_list[0].get_emails()[0])
            self.assertEqual("{'titi@machin.com': (550, b'Bad <address> : titi@machin.com'), 'jack@worldcompany.com': 'OK'}", email_sent_list[0].error)
            self.assertEqual(['joe@worldcompany.com'], email_sent_list[1].get_emails()[0])
            self.assertEqual('', email_sent_list[1].error)
            self.assertEqual(['wiliam@worldcompany.com'], email_sent_list[2].get_emails()[0])
            self.assertEqual('', email_sent_list[2].error)
            self.assertEqual(['avrel@worldcompany.com'], email_sent_list[3].get_emails()[0])
            self.assertEqual('', email_sent_list[3].error)
        finally:
            server.stop()


class SMSTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        initial_values = [{'name': 'aaa', 'modelname': 'contacts.AbstractContact', 'kind': '0', 'args': "{'multi':False"},
                          {'name': 'bbb', 'modelname': 'contacts.AbstractContact', 'kind': '1', 'args': "{'min':0, 'max':100, 'prec':0"},
                          {'name': 'ccc', 'modelname': 'contacts.LegalEntity', 'kind': '0', 'args': "{'multi':False"},
                          {'name': 'ddd', 'modelname': 'contacts.Individual', 'kind': '0', 'args': "{'multi':False"},
                          {'name': 'eee', 'modelname': 'contacts.Individual', 'kind': '0', 'args': "{'multi':True"}]
        for initial_value in initial_values:
            CustomField.objects.create(**initial_value)
        change_ourdetail(tel2="07-45-12-95-78", custom_1='abcd', custom_2=5, custom_3='0689674523')
        self.jack = create_jack(firstname="jack", lastname="MISTER", with_email=False, tel1="06-89-67-45-23", custom_1='uvw', custom_2=1, custom_4='0345987650', custom_5='blablabla')
        self.jean = create_jack(firstname="jean", lastname="Valjean", with_email=False, tel1="07-67-45-23-01", custom_1='xyz', custom_2=7, custom_4='0795623148', custom_5='blablabla')
        logging.getLogger("lucterios.mailing.test").setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger("lucterios.mailing.test").setLevel(logging.NOTSET)
        LucteriosTest.tearDown(self)

    def test_messages(self):
        self.factory.xfer = MessageSMSList()
        self.calljson('/lucterios.mailing/messageSMSList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSMSList')
        self.assertEqual(len(self.json_context), 1)
        self.assertEqual(self.json_context['message_type'], 1)
        self.assert_count_equal("message", 0)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 1}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageAddModify')
        self.assert_count_equal('', 4)
        self.assert_json_equal('EDIT', "subject", "")
        self.assert_json_equal('MEMO', "body", "")
        self.assert_json_equal('CHECKLIST', "sms_field_names", [])
        self.assert_json_equal('', "#sms_field_names/case", [['tel1', 'tel1'], ['tel2', 'tel2'], ['custom_1', 'aaa'],
                                                             ['custom_3', 'ccc'], ['custom_4', 'ddd'], ['custom_5', 'eee']])
        self.assert_json_equal('', "#subject/description", "titre")
        self.assert_json_equal('', "#body/with_hypertext", False)

        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 1, 'SAVE': 'YES', 'subject': 'test message', 'body': 'Small message to give a big kiss ;){[br/]}Bye',
                                                              "sms_field_names": ['tel1', 'tel2']}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageSMSList()
        self.calljson('/lucterios.mailing/messageSMSList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSMSList')
        self.assert_count_equal("message", 1)
        self.assert_json_equal('', "message/@0/status", 0)
        self.assert_json_equal('', "message/@0/date", None)
        self.assert_json_equal('', "#message/headers/@2/@1", 'titre')
        self.assert_json_equal('', "message/@0/subject", 'test message')

        self.factory.xfer = MessageEmailList()
        self.calljson('/lucterios.mailing/messageEmailList', {}, False)
        self.assert_count_equal("message", 0)

        self.factory.xfer = MessageDel()
        self.calljson('/lucterios.mailing/messageDel', {'message': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageDel')

        self.factory.xfer = MessageSMSList()
        self.calljson('/lucterios.mailing/messageSMSList', {}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSMSList')
        self.assert_count_equal("message", 0)

    def test_show_message(self):
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 1, 'SAVE': 'YES', 'subject': 'test message', 'body': 'Small message to give a big kiss ;){[br/]}Bye',
                                                              "sms_field_names": 'tel1;tel2'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageAddModify')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 10)
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_json_equal('LABELFORM', "date", None)
        self.assert_json_equal('', "#subject/description", "titre")
        self.assert_json_equal('LABELFORM', "subject", "test message")
        self.assert_json_equal('LABELFORM', "body", "Small message to give a big kiss ;){[br/]}Bye")
        self.assert_json_equal('LABELFORM', "size_sms", 39)
        self.assert_json_equal('LABELFORM', "sms_field_names", ['tel1', 'tel2'])
        self.assert_count_equal("recipient_list", 0)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[0], ('Modifier', 'mdi:mdi-pencil-outline', 'lucterios.mailing', 'messageAddModify', 1, 1, 0))
        self.assert_action_equal('POST', self.json_actions[1], ('Fermer', 'mdi:mdi-close'))

        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.AbstractContact', 'CRITERIA': ''}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient',
                      {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': 'name||5||truc'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageValidRecipient')

        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal('POST', self.json_actions[0], ('Valider', 'mdi:mdi-share', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'valid'}))
        self.assert_action_equal('POST', self.json_actions[1], ('Modifier', 'mdi:mdi-pencil-outline', 'lucterios.mailing', 'messageAddModify', 1, 1, 0))
        self.assert_action_equal('POST', self.json_actions[2], ('Fermer', 'mdi:mdi-close'))
        self.assert_json_equal('LABELFORM', "status", 0)
        self.assert_count_equal("#recipient_list/actions", 2)
        self.assert_count_equal("recipient_list", 3)
        self.assert_json_equal('', "recipient_list/@0/model", "Personne Physique")
        self.assert_json_equal('', "recipient_list/@0/filter", '{[b]}genre{[/b]} égal {[i]}"Homme"{[/i]}')
        self.assert_json_equal('', "recipient_list/@1/model", "Contact Générique")
        self.assert_json_equal('', "recipient_list/@2/model", "Personne Morale")
        self.assert_json_equal('LABELFORM', "contact_nb", 5)

    def test_validate_message(self):
        self.jean.tel1 = ''
        self.jean.save()
        configSMS()
        clean_sms_testfile(create_new=False)
        self.assertFalse(AbstractProvider.is_current_active(), 'no sms')
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 1, 'SAVE': 'YES', 'subject': 'test message', 'body': 'Small message to give a big kiss ;){[br/]}Bye',
                                                              "sms_field_names": 'tel1;tel2;custom_3'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'}, False)
        self.factory.xfer = MessageValidRecipient()
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''}, False)
        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'lucterios.mailing', 'messageTransition')

        self.assertFalse(AbstractProvider.is_current_active(), 'no sms')
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', "status", 1)
        self.assert_count_equal("#recipient_list/actions", 0)
        self.assert_count_equal("recipient_list", 2)
        self.assert_json_equal('LABELFORM', "contact_nb", '3')
        self.assertEqual(len(self.json_actions), 1)
        self.assert_action_equal('POST', self.json_actions[0], ('Fermer', 'mdi:mdi-close'))

        clean_sms_testfile(create_new=True)
        self.assertTrue(AbstractProvider.is_current_active(), 'with sms')
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', "contact_nosms", ['Valjean jean : 02-78-45-12-95'])
        self.assertEqual(len(self.json_actions), 2)
        self.assert_action_equal('POST', self.json_actions[0], ('SMS', 'mdi:mdi-message-outline', 'lucterios.mailing', 'messageTransition', 0, 1, 1, {'TRANSITION': 'sending'}))
        self.assert_action_equal('POST', self.json_actions[1], ('Fermer', 'mdi:mdi-close'))

        self.factory.xfer = MessageTransition()
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'sending'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'messageTransition')
        self.assert_json_equal('', 'text', 'Voulez-vous envoyer ce message à 2 contacts ?')

    def test_trysend(self):
        configSMS()
        clean_sms_testfile(create_new=False)
        self.factory.xfer = MessageAddModify()
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 1, 'SAVE': 'YES', 'subject': 'test message', 'body': 'Small message to give a big kiss ;){[br/]}Bye',
                                                              "sms_field_names": 'tel1;tel2'}, False)
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assertEqual(len(self.json_actions), 2)

        clean_sms_testfile(create_new=True)
        self.factory.xfer = MessageShow()
        self.calljson('/lucterios.mailing/messageShow', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assertEqual(len(self.json_actions), 3)

        self.assertEqual(read_sms(), [])
        self.factory.xfer = MessageSendSMSTry()
        self.calljson('/lucterios.mailing/messageSendSMSTry', {'message': '1'}, False)
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSendSMSTry')
        self.assert_json_equal('EDIT', "phone", '0123456789')

        self.factory.xfer = MessageSendSMSTry()
        self.calljson('/lucterios.mailing/messageSendSMSTry', {'message': '1', 'CONFIRME': 'YES', "phone": '0623456789'}, False)
        self.assert_observer('core.dialogbox', 'lucterios.mailing', 'messageSendSMSTry')
        self.assert_json_equal('', 'text', 'SMS envoyé, veuillez le vérifier.')
        self.assertEqual(read_sms(), ["WoldCompany : +33623456789 => 'Small message to give a big kiss ;)|Bye'\n"])

    def test_send_classic(self):
        configSMS(max_sms=6)
        clean_sms_testfile(create_new=True)
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()
        self.jean.tel1 = ''
        self.jean.save()

        sms_msg = Message.objects.create(subject="test message'", body="Small message to give a big kiss ;){[br/]}Bye", message_type=1)
        sms_msg.set_sms_field_names('tel1;tel2;custom_3')
        sms_msg.add_recipient('contacts.Individual', 'genre||8||1')
        sms_msg.add_recipient('contacts.LegalEntity', '')
        sms_msg.valid()
        self.assertEqual(['tel1', 'tel2', 'custom_3'], list(sms_msg.get_sms_field_names(translate=False)))
        self.assertEqual(3, sms_msg.contact_nb)
        self.assertEqual(['Valjean jean : 02-78-45-12-95'], sms_msg.contact_nosms)
        self.assertEqual(2, sms_msg.prep_sending(), sms_msg.email_to_send)
        sms_msg.status = 2
        sms_msg.save()

        self.assertEqual(read_sms(), [])
        sms_msg.sendSMS()

        sms_msg = Message.objects.get(id=sms_msg.id)
        self.assertEqual(sms_msg.status, 1)
        self.assertEqual(sms_msg.email_to_send, '')
        self.assertEqual(read_sms(), ["WoldCompany : +33745129578 => 'Small message to give a big kiss ;)|Bye'\n",
                                      "WoldCompany : +33689674523 => 'Small message to give a big kiss ;)|Bye'\n"])

        sms_sent_list = sms_msg.emailsent_set.all().order_by('id')
        self.assertEqual(2, len(sms_sent_list))
        self.assertEqual("0745129578", sms_sent_list[0].email)
        self.assertEqual("", sms_sent_list[0].error)
        self.assertEqual("0689674523", sms_sent_list[1].email)
        self.assertEqual("", sms_sent_list[1].error)

    def test_send_classic_with_bad_sms(self):
        configSMS(max_sms=3)
        clean_sms_testfile(create_new=True)
        self.factory.user = LucteriosUser.objects.create(username='empty')
        self.factory.user.is_superuser = True
        self.factory.user.save()
        self.jack.set_custom_values({'custom_5': '0675315946'})
        self.jean.set_custom_values({'custom_5': '0795175364'})

        sms_msg = Message.objects.create(subject="test message'", body="Small message to give a big kiss ;){[br/]}Bye", message_type=1)
        sms_msg.set_sms_field_names('tel1;tel2;custom_5')
        sms_msg.add_recipient('contacts.Individual', 'genre||8||1')
        sms_msg.add_recipient('contacts.LegalEntity', '')
        sms_msg.valid()
        self.assertEqual(['tel1', 'tel2', 'custom_5'], list(sms_msg.get_sms_field_names(translate=False)))
        self.assertEqual(3, sms_msg.contact_nb)
        self.assertEqual([], sms_msg.contact_nosms)
        self.assertEqual(5, sms_msg.prep_sending(), sms_msg.email_to_send)
        sms_msg.status = 2
        sms_msg.save()

        self.assertEqual(read_sms(), [])
        sms_msg.sendSMS()

        sms_msg = Message.objects.get(id=sms_msg.id)
        self.assertEqual(sms_msg.status, 1)
        self.assertEqual(sms_msg.email_to_send, '')
        self.assertEqual(read_sms(), ["WoldCompany : +33745129578 => 'Small message to give a big kiss ;)|Bye'\n",
                                      "WoldCompany : +33675315946 => 'Small message to give a big kiss ;)|Bye'\n",
                                      "WoldCompany : +33689674523 => 'Small message to give a big kiss ;)|Bye'\n"])

        sms_sent_list = sms_msg.emailsent_set.all().order_by('id')
        self.assertEqual(5, len(sms_sent_list))
        self.assertEqual("0745129578", sms_sent_list[0].email)
        self.assertEqual("", sms_sent_list[0].error)
        self.assertEqual("0675315946", sms_sent_list[1].email)
        self.assertEqual("", sms_sent_list[1].error)
        self.assertEqual("0689674523", sms_sent_list[2].email)
        self.assertEqual("", sms_sent_list[2].error)
        self.assertEqual("0767452301", sms_sent_list[3].email)
        self.assertEqual("File '/tmp/sms.txt' too long !", sms_sent_list[3].error)
        self.assertEqual("0795175364", sms_sent_list[4].email)
        self.assertEqual("File '/tmp/sms.txt' too long !", sms_sent_list[4].error)


class SendMessagingTest(AsychronousLucteriosTest):

    smtp_port = 1325

    def setUp(self):
        AsychronousLucteriosTest.setUp(self)
        change_ourdetail(tel2="07-45-12-95-78")
        create_jack(firstname="jack", lastname='Dalton', tel1="0689-6745 23")
        create_jack(firstname="joe", lastname='Dalton', tel1="07-67-89-23-45")
        create_jack(firstname="wiliam", lastname='Dalton', tel1="06 89 67 45 23")
        create_jack(firstname="avrel", lastname='Dalton', tel1="02-45-23-89-67")
        contact_luke = create_jack(firstname="lucky", lastname='Luke', tel1="07-69-87-43-25")
        contact_luke.email += ';lucky@luke.org,luke@usmarchal.gov'
        contact_luke.save()
        create_jack(firstname="timothé", lastname='Doux', tel1="07.012.345.78")
        create_jack(firstname="jean", lastname="Valjean", with_email=False, tel1="04-67-89-23-45")
        create_jack(firstname="joe", lastname='Lindien', tel1="06-98-01-42-53")
        create_doc(LucteriosUser.objects.get(username='admin'), with_folder=False)
        SendMessagingTest.smtp_port += 1
        logging.getLogger("lucterios.mailing.test").setLevel(logging.DEBUG)

    def tearDown(self):
        logging.getLogger("lucterios.mailing.test").setLevel(logging.NOTSET)
        LucteriosTest.tearDown(self)

    def _test_email1(self):
        def _check_msg(msg_txt, msg, msg_file1, msg_file3, index):
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("<html><body><b><font color=\"blue\">All</font></b><br/>Small message to give a big <u>kiss</u> ;)<br/><br/>Bye<img src='http://testserver/lucterios.mailing/emailSentAddForStatistic?emailsent=%d' alt=''/></body></html>" % index, decode_b64(msg.get_payload()))
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual("**All**  \nSmall message to give a big _kiss_ ;)  \n  \nBye\n\n", decode_b64(msg_txt.get_payload()))
            self.assertTrue('doc1.png' in msg_file1.get('Content-Type', ''), msg_file1.get('Content-Type', ''))
            content_msg1 = b64decode(msg_file1.get_payload())
            self.assertEqual(b"\x89PNG", content_msg1[:4])
            self.assertEqual(42023, len(content_msg1))
            self.assertTrue('doc3.png' in msg_file3.get('Content-Type', ''), msg_file3.get('Content-Type', ''))
            content_msg3 = b64decode(msg_file3.get_payload())
            self.assertEqual(b"\x89PNG", content_msg3[:4])
            self.assertEqual(51845, len(content_msg3))

        configSMTP('localhost', SendMessagingTest.smtp_port, batchtime=0.1, batchsize=4)
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'doc_in_link': 0, 'subject': 'new message', 'body': '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Small message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'})
        self.assert_action_equal('GET', self.response_json['action'], ('Editer', 'mdi:mdi-text-box-outline', 'lucterios.mailing', 'messageShow', 1, 1, 1, {'message': '1'}))
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'})
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '1', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '1'})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '1', 'document': '3'})
        self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'valid', 'CONFIRME': 'YES'})
        server = TestReceiver()
        server.start(SendMessagingTest.smtp_port)
        try:
            self.assertEqual(0, server.count())
            self.calljson('/lucterios.mailing/messageTransition', {'message': '1', 'TRANSITION': 'sending', 'CONFIRME': 'YES'})
            self.assertEqual(0, server.count())
            sleep(10)
            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            sleep(40)
            self.assertEqual(8, server.count())
            self.assertEqual([['mr-sylvestre@worldcompany.com'], ['jack@worldcompany.com'], ['joe@worldcompany.com'], ['wiliam@worldcompany.com'], ['avrel@worldcompany.com'],
                              ['lucky@luke.org'], ['lucky@worldcompany.com'], ['luke@usmarchal.gov']], server.email_list())
            self.assertEqual(0, len(LucteriosScheduler.get_list()))
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg_txt, msg, msg_file1, msg_file3 = server.check_first_message('new message', 4)
            _check_msg(msg_txt, msg, msg_file1, msg_file3, 1)
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(-1)[1])
            self.assertEqual(['luke@usmarchal.gov'], server.get(-1)[2])
            msg_txt, msg, msg_file1, msg_file3 = server.check_last_message('new message', 4)
            _check_msg(msg_txt, msg, msg_file1, msg_file3, 8)
        finally:
            server.stop()

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': False}, 'get')
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 7)
        self.assert_grid_equal('emailsent', {"contact": "contact", "sended_item": "ref. d'envoi", "date": "date", "success": "succès",
                                             "last_open_date": "date de dernière ouverture", "nb_open": "nombre de messages ouverts"}, 9)
        self.assert_json_equal('', "emailsent/@0/sended_item", "mr-sylvestre@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 1)
        self.assert_json_equal('', "emailsent/@0/nb_open", 0)
        self.assert_json_equal('', "emailsent/@0/id", 1)
        self.assert_json_equal('', "emailsent/@1/sended_item", "jack@worldcompany.com")
        self.assert_json_equal('', "emailsent/@1/success", 1)
        self.assert_json_equal('', "emailsent/@1/nb_open", 0)
        self.assert_json_equal('', "emailsent/@1/id", 2)
        self.assert_json_equal('', "emailsent/@2/sended_item", "joe@worldcompany.com")
        self.assert_json_equal('', "emailsent/@2/success", 1)
        self.assert_json_equal('', "emailsent/@2/nb_open", 0)
        self.assert_json_equal('', "emailsent/@2/id", 3)
        self.assert_json_equal('', "emailsent/@3/sended_item", "wiliam@worldcompany.com")
        self.assert_json_equal('', "emailsent/@3/success", 1)
        self.assert_json_equal('', "emailsent/@3/nb_open", 0)
        self.assert_json_equal('', "emailsent/@3/id", 4)
        self.assert_json_equal('', "emailsent/@4/sended_item", "avrel@worldcompany.com")
        self.assert_json_equal('', "emailsent/@4/success", 1)
        self.assert_json_equal('', "emailsent/@4/nb_open", 0)
        self.assert_json_equal('', "emailsent/@4/id", 5)
        self.assert_json_equal('', "emailsent/@5/sended_item", "luke@usmarchal.gov")
        self.assert_json_equal('', "emailsent/@5/success", 1)
        self.assert_json_equal('', "emailsent/@5/nb_open", 0)
        self.assert_json_equal('', "emailsent/@5/id", 8)
        self.assert_json_equal('', "emailsent/@6/sended_item", "lucky@worldcompany.com")
        self.assert_json_equal('', "emailsent/@6/success", 1)
        self.assert_json_equal('', "emailsent/@6/nb_open", 0)
        self.assert_json_equal('', "emailsent/@6/id", 7)
        self.assert_json_equal('', "emailsent/@7/sended_item", "lucky@luke.org")
        self.assert_json_equal('', "emailsent/@7/success", 1)
        self.assert_json_equal('', "emailsent/@7/nb_open", 0)
        self.assert_json_equal('', "emailsent/@7/id", 6)
        self.assert_json_equal('', "emailsent/@8/sended_item", "timothé@worldcompany.com")
        self.assert_json_equal('', "emailsent/@8/success", 0)
        self.assert_json_equal('', "emailsent/@8/nb_open", 0)
        self.assert_json_equal('', "emailsent/@8/id", 9)
        self.assertEqual(len(self.json_actions), 1)
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '1'}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '2'}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '3'}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '2'}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '2'}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '20'}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {}, "get")
        self.call_ex('/lucterios.mailing/emailSentAddForStatistic', {'emailsent': '3'}, "get")
        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': False}, "get")
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_json_equal('', "emailsent/@0/sended_item", "joe@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 1)
        self.assert_json_equal('', "emailsent/@0/nb_open", 2)
        self.assert_json_equal('', "emailsent/@0/id", 3)
        self.assert_json_equal('', "emailsent/@1/sended_item", "jack@worldcompany.com")
        self.assert_json_equal('', "emailsent/@1/success", 1)
        self.assert_json_equal('', "emailsent/@1/nb_open", 3)
        self.assert_json_equal('', "emailsent/@1/id", 2)
        self.assert_json_equal('', "emailsent/@2/sended_item", "mr-sylvestre@worldcompany.com")
        self.assert_json_equal('', "emailsent/@2/success", 1)
        self.assert_json_equal('', "emailsent/@2/nb_open", 1)
        self.assert_json_equal('', "emailsent/@2/id", 1)
        self.assert_json_equal('', "emailsent/@3/sended_item", "wiliam@worldcompany.com")
        self.assert_json_equal('', "emailsent/@3/success", 1)
        self.assert_json_equal('', "emailsent/@3/nb_open", 0)
        self.assert_json_equal('', "emailsent/@3/id", 4)
        self.assert_json_equal('', "emailsent/@4/sended_item", "avrel@worldcompany.com")
        self.assert_json_equal('', "emailsent/@4/success", 1)
        self.assert_json_equal('', "emailsent/@4/nb_open", 0)
        self.assert_json_equal('', "emailsent/@4/id", 5)
        self.assert_json_equal('', "emailsent/@5/sended_item", "luke@usmarchal.gov")
        self.assert_json_equal('', "emailsent/@5/success", 1)
        self.assert_json_equal('', "emailsent/@5/nb_open", 0)
        self.assert_json_equal('', "emailsent/@5/id", 8)
        self.assert_json_equal('', "emailsent/@6/sended_item", "lucky@worldcompany.com")
        self.assert_json_equal('', "emailsent/@6/success", 1)
        self.assert_json_equal('', "emailsent/@6/nb_open", 0)
        self.assert_json_equal('', "emailsent/@6/id", 7)
        self.assert_json_equal('', "emailsent/@7/sended_item", "lucky@luke.org")
        self.assert_json_equal('', "emailsent/@7/success", 1)
        self.assert_json_equal('', "emailsent/@7/nb_open", 0)
        self.assert_json_equal('', "emailsent/@7/id", 6)
        self.assert_json_equal('', "emailsent/@8/sended_item", "timothé@worldcompany.com")
        self.assert_json_equal('', "emailsent/@8/success", 0)
        self.assert_json_equal('', "emailsent/@8/nb_open", 0)
        self.assert_json_equal('', "emailsent/@8/id", 9)
        val_stat = self.get_json_path("statistic")
        self.assertIn("9 message(s) envoyé(s) le", val_stat)
        self.assertIn("(dont 1 en erreur)", val_stat)
        self.assertIn("Avec 3 message(s) ouvert(s)", val_stat)
        self.assertIn("taux de 33.3 % d'ouverture.", val_stat)
        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '1', 'show_only_failed': True}, "get")
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 7)
        self.assert_grid_equal('emailsent', {"contact": "contact", "sended_item": "ref. d'envoi", "date": "date", "success": "succès", "error": "erreur"}, 1)
        self.assert_json_equal('', "emailsent/@0/sended_item", "timothé@worldcompany.com")
        self.assert_json_equal('', "emailsent/@0/success", 0)
        self.assert_json_equal('', "emailsent/@0/error", "Destinataires non valides !", True)

    def _test_email2(self):
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 0, 'SAVE': 'YES', 'doc_in_link': 1, 'subject': 'new message', 'body': '{[b]}{[font color="blue"]}All{[/font]}{[/b]}{[newline]}Other message to give a big {[u]}kiss{[/u]} ;){[newline]}{[newline]}Bye'})
        self.assert_action_equal('GET', self.response_json['action'], ('Editer', 'mdi:mdi-text-box-outline', 'lucterios.mailing', 'messageShow', 1, 1, 1, {'message': '2'}))
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '2', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '2', 'document': '1'})
        self.calljson('/lucterios.mailing/messageValidInsertDoc', {'message': '2', 'document': '3'})
        self.calljson('/lucterios.mailing/messageTransition', {'message': '2', 'TRANSITION': 'valid', 'CONFIRME': 'YES'})
        self.calljson('/lucterios.mailing/messageShow', {'message': '2'}, 'get')
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageShow')
        self.assert_json_equal('LABELFORM', "status", 1)
        self.assert_count_equal("recipient_list", 1)
        self.assert_json_equal('LABELFORM', "contact_nb", '1')
        server = TestReceiver()
        server.start(SendMessagingTest.smtp_port)
        try:
            self.assertEqual(0, server.count())
            self.calljson('/lucterios.mailing/messageTransition', {'message': '2', 'TRANSITION': 'sending', 'CONFIRME': 'YES'})
            self.assertEqual(0, server.count())
            sleep(10)
            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            sleep(10)
            self.assertEqual(0, len(LucteriosScheduler.get_list()))
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg_txt, msg = server.check_first_message('new message', 2)
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            content = decode_b64(msg.get_payload())
            self.assertEqual('<html><body><b><font color="blue">All</font></b><br/>Other message to give a big <u>kiss</u> ;)<br/><br/>Bye', content[:108])
            self.assertEqual(content[108:].count('http://testserver/lucterios.documents/downloadFile?shared='), 2)
            self.assertEqual(content[108:].count('filename=doc1.png'), 1)
            self.assertEqual(content[108:].count('filename=doc3.png'), 1)
        finally:
            server.stop()

    def _test_sms1(self):
        self.calljson('/lucterios.mailing/messageAddModify', {'message_type': 1, 'SAVE': 'YES', 'subject': 'test message', 'body': 'Small message to give a big kiss ;){[br/]}Bye',
                                                              "sms_field_names": 'tel1;tel2'})
        self.assert_action_equal('GET', self.response_json['action'], ('Editer', 'mdi:mdi-text-box-outline', 'lucterios.mailing', 'messageShow', 1, 1, 1, {'message': '3'}))

        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '3', 'modelname': 'contacts.Individual', 'CRITERIA': 'genre||8||1'})
        self.calljson('/lucterios.mailing/messageValidRecipient', {'message': '3', 'modelname': 'contacts.LegalEntity', 'CRITERIA': ''})
        self.calljson('/lucterios.mailing/messageTransition', {'message': '3', 'TRANSITION': 'valid', 'CONFIRME': 'YES'})

        self.assertEqual(read_sms(), [])
        self.calljson('/lucterios.mailing/messageTransition', {'message': '3', 'TRANSITION': 'sending', 'CONFIRME': 'YES'})
        self.assertEqual(read_sms(), [])
        sleep(10)
        self.assertEqual(1, len(LucteriosScheduler.get_list()))
        sleep(20)
        self.assertEqual(0, len(LucteriosScheduler.get_list()))
        self.assertEqual(read_sms(), ["WoldCompany : +33745129578 => 'Small message to give a big kiss ;)|Bye'\n",
                                      "WoldCompany : +33689674523 => 'Small message to give a big kiss ;)|Bye'\n",
                                      "WoldCompany : +33767892345 => 'Small message to give a big kiss ;)|Bye'\n",
                                      "WoldCompany : +33769874325 => 'Small message to give a big kiss ;)|Bye'\n"])

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '3', 'show_only_failed': False}, 'get')
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 7)
        self.assert_grid_equal('emailsent', {"contact": "contact", "sended_item": "ref. d'envoi", "date": "date", "success": "succès"}, 6)
        self.assert_json_equal('', "emailsent/@0/sended_item", "0745129578")
        self.assert_json_equal('', "emailsent/@0/contact", "WoldCompany")
        self.assert_json_equal('', "emailsent/@0/success", True)
        self.assert_json_equal('', "emailsent/@1/sended_item", "0689674523")
        self.assert_json_equal('', "emailsent/@1/contact", "Dalton jack")
        self.assert_json_equal('', "emailsent/@1/success", True)
        self.assert_json_equal('', "emailsent/@2/sended_item", "0767892345")
        self.assert_json_equal('', "emailsent/@2/contact", "Dalton joe")
        self.assert_json_equal('', "emailsent/@2/success", True)
        self.assert_json_equal('', "emailsent/@3/sended_item", "0769874325")
        self.assert_json_equal('', "emailsent/@3/contact", "Luke lucky")
        self.assert_json_equal('', "emailsent/@3/success", True)
        self.assert_json_equal('', "emailsent/@4/sended_item", "0701234578")
        self.assert_json_equal('', "emailsent/@4/contact", "Doux timothé")
        self.assert_json_equal('', "emailsent/@4/success", False)
        self.assert_json_equal('', "emailsent/@5/sended_item", "0698014253")
        self.assert_json_equal('', "emailsent/@5/contact", "Lindien joe")
        self.assert_json_equal('', "emailsent/@5/success", False)
        val_stat = self.get_json_path("statistic")
        self.assertIn("6 message(s) envoyé(s) le", val_stat)
        self.assertIn("(dont 2 en erreur)", val_stat)
        self.assertNotIn(" message(s) ouvert(s)", val_stat)
        self.assertNotIn(" % d'ouverture.", val_stat)

        self.calljson('/lucterios.mailing/messageSentInfo', {'message': '3', 'show_only_failed': True}, 'get')
        self.assert_observer('core.custom', 'lucterios.mailing', 'messageSentInfo')
        self.assert_count_equal('', 7)
        self.assert_grid_equal('emailsent', {"contact": "contact", "sended_item": "ref. d'envoi", "date": "date", "success": "succès", "error": "erreur"}, 2)
        self.assert_json_equal('', "emailsent/@0/sended_item", "0701234578")
        self.assert_json_equal('', "emailsent/@0/success", False)
        self.assert_json_equal('', "emailsent/@0/error", "File '/tmp/sms.txt' too long !")
        self.assert_json_equal('', "emailsent/@1/sended_item", "0698014253")
        self.assert_json_equal('', "emailsent/@1/success", False)
        self.assert_json_equal('', "emailsent/@1/error", "File '/tmp/sms.txt' too long !")

        # List phone valid:
        # +33745129578
        # +33689674523
        # +33767892345
        # +33769874325
        # +33701234578
        # +33698014253

    def test(self):
        self.calljson('/CORE/authentification', {'login': 'admin', 'password': 'admin'})
        self.assert_observer('core.auth', 'CORE', 'authentification')
        self.assert_json_equal('', '', 'OK')

        self._test_email1()
        self._test_email2()

        configSMS(max_sms=4)
        clean_sms_testfile(create_new=True)
        self._test_sms1()
