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
from os.path import isfile
from os import remove
from time import sleep
from aiosmtpd.handlers import Message
from aiosmtpd.controller import Controller
import logging
import email

from django.test.testcases import TestCase

from lucterios.CORE.parameters import Params


def decode_b64(data):
    byte_string = data.encode('utf-8')
    decoded = b64decode(byte_string)
    return decoded.decode('utf-8')


def configSMTP(server, port, security=0, user='', passwd='', batchtime=0.1, batchsize=20, dkim_private_file=''):
    Params.setvalue(name='mailing-smtpserver', value=server)
    Params.setvalue(name='mailing-smtpport', value=port)
    Params.setvalue(name='mailing-smtpsecurity', value=security)
    Params.setvalue(name='mailing-smtpuser', value=user)
    Params.setvalue(name='mailing-smtppass', value=passwd)
    Params.setvalue(name='mailing-dkim-private-path', value=dkim_private_file)
    Params.setvalue(name='mailing-delay-batch', value="%.1f" % batchtime)
    Params.setvalue(name='mailing-nb-by-batch', value="%.d" % batchsize)


def configSMS(file_name='/tmp/sms.txt', max_sms=3):
    Params.setvalue('mailing-sms-provider', 'TestProvider')
    Params.setvalue('mailing-sms-option', 'file name = %s{[br/]}max = %d' % (file_name, max_sms))


def clean_sms_testfile(create_new, file_name='/tmp/sms.txt'):
    if isfile(file_name):
        remove(file_name)
    if create_new:
        with open(file_name, "w"):
            pass


def read_sms(file_name='/tmp/sms.txt'):
    if isfile(file_name):
        with open(file_name, 'r') as sms_file:
            sms_content = sms_file.readlines()
        return sms_content
    else:
        return None


class RecordingHandler(Message):
    def __init__(self, controler):
        super().__init__(message_class=email.message.Message)
        self.controler = controler

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if self.controler.wrong_email is not None:
            addresses = [email.strip() for email in address.replace(',', ';').split(';') if email.strip() != '']
            if len(addresses) == 0:
                return '501 Syntax: RCPT TO: <address>'
            if self.controler.wrong_email in addresses:
                return '550 Bad <address> : %s' % self.controler.wrong_email
        envelope.rcpt_tos.append(address)
        return '250 OK'

    def handle_message(self, message):
        peer = message.get('X-Peer', '')
        mailfrom = message.get('X-MailFrom', '')
        rcptTO = [email.strip() for email in message.get('X-RcptTo', '').replace(',', ';').split(';')]
        self.controler.emails.append((peer, mailfrom, rcptTO, message))
        logging.getLogger("lucterios.mailing.test").debug('[email] MESSAGE - PORT=%d - %s\n', self.controler.port, message)


class SMTPDController(Controller):

    def __init__(self, port=8025, wrong_email=None):
        Controller.__init__(self,
                            handler=RecordingHandler(self),
                            hostname='127.0.0.1',
                            port=port)
        self.emails = []
        self.auth_params = None
        self.wrong_email = wrong_email

    def check_is_running(self, sleep_time=1.0):
        sleep(sleep_time)


class TestReceiver(TestCase):

    def __init__(self):
        TestCase.__init__(self, methodName='stop')
        self.smtp = None

    def start(self, port):
        self.smtp = SMTPDController(port)
        self.smtp.start()
        logging.getLogger("lucterios.mailing.test").debug('[email] start reseiver')

    def stop(self):
        if self.smtp is not None:
            self.smtp.stop()
            self.smtp = None

    def assert_count(self, nb_expected):
        self.assertEqual(nb_expected, self.count(1.0 * (nb_expected + 1)))

    def count(self, sleep_time=1.0):
        if self.smtp is not None:
            self.smtp.check_is_running(sleep_time)
            return len(self.smtp.emails)
        else:
            return -1

    def get(self, index):
        return self.smtp.emails[index]

    def email_list(self):
        return [email[2] for email in self.smtp.emails]

    def get_first_msg(self):
        return self.get(0)[3]

    def convert_message(self, msg_list):
        msg_result = []
        for msg_item in msg_list:
            if (msg_item.get_content_type() == 'multipart/alternative'):
                msg_result.extend(msg_item.get_payload())
            else:
                msg_result.append(msg_item)
        return msg_result

    def get_msg_index(self, index, subject=None, params=None):
        def decode_mime_words(text):
            return ''.join(word.decode(encoding or 'utf8') if isinstance(word, bytes) else word for word, encoding in email.header.decode_header(text))
        special_value = {
            "peer": str(self.get(index)[0]),
            "mailfrom": str(self.get(index)[1]),
            "rcpttos": ";".join(self.get(index)[2])
        }
        msg = self.get(index)[3]
        if params is None:
            params = {}
        if isinstance(params, dict):
            if subject is not None:
                params['Subject'] = subject
            for key, val in params.items():
                if key in special_value:
                    self.assertEqual(val, special_value[key])
                else:
                    self.assertEqual(val, decode_mime_words(msg.get(key, '')), msg.get(key, ''))
        return self.convert_message(msg.get_payload())

    def check_first_message(self, subject, nb_multi, params=None):
        msg_result = self.get_msg_index(0, subject, params)
        self.assertEqual(nb_multi, len(msg_result))
        return msg_result

    def check_last_message(self, subject, nb_multi, params=None):
        msg_result = self.get_msg_index(-1, subject, params)
        self.assertEqual(nb_multi, len(msg_result))
        return msg_result
