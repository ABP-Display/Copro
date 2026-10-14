# -*- coding: utf-8 -*-
'''
lucterios.contacts package

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2020 sd-libre.fr
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
from os.path import isfile
from re import compile
from logging import getLogger

from django.utils.translation import gettext_lazy as _

from lucterios.framework.error import LucteriosException, IMPORTANT


class SMSException(LucteriosException):

    def __init__(self, msg):
        LucteriosException.__init__(self, IMPORTANT, msg)


class AbstractProvider(object):

    title = ''
    default_options = {}

    def __init__(self, phone_parse, sender, options):
        self.sender = sender
        self.set_options(options)
        self.phone_check = compile(phone_parse[0])
        self.phone_replace = phone_parse[1] if len(phone_parse) > 0 else ""
        self.last_error = None

    def set_options(self, options):
        self.options = {opt_line.split('=')[0].strip(): opt_line.split('=')[1].strip() for opt_line in options.split('{[br/]}') if opt_line.count('=') == 1}
        for opt_key, opt_val in self.default_options.items():
            if opt_key not in self.options:
                self.options[opt_key] = opt_val

    @property
    def is_active(self):
        self.last_error = _('No implemented')
        return False

    @classmethod
    def simple_phone(cls, phone):
        return "".join([digit for digit in phone if digit in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')])

    def convert_sms_phone(self, phone, return_simple=False):
        new_phone = None
        simple_phone = self.simple_phone(phone)
        regex_phone = self.phone_check.match(simple_phone)
        if regex_phone:
            new_phone = self.phone_replace.format(*regex_phone.groups())
            if return_simple:
                return simple_phone
            else:
                return new_phone
        return None

    def has_valid_phone(self, contact, fields):
        valid = False
        for field_name in fields:
            try:
                valid = valid or (self.convert_sms_phone(getattr(contact, field_name, '')) is not None)
            except ValueError:
                pass
        return valid

    @property
    def options_text(self):
        return "{[br/]}".join(["%s = %s" % (opt_key, opt_val) for opt_key, opt_val in self.options.items() if opt_key in self.default_options])

    def send_sms(self, phone, text):
        self.last_error = None
        new_phone = self.convert_sms_phone(phone)
        if new_phone is None:
            self.last_error = _("Bad phone number '%s' !") % phone
            raise SMSException(self.last_error)
        else:
            self.send_sms_ex(new_phone, text)

    def send_sms_ex(self, phone, text):
        self.last_error = _('No implemented')
        return

    @classmethod
    def get_provider_list(cls):
        from django.conf import settings
        return [('', None)] + [(sub_provider.__name__, sub_provider.title) for sub_provider in cls.__subclasses__()
                               if hasattr(settings, "MAILING_TESTSMS") or (sub_provider is not TestProvider)]

    @classmethod
    def get_current_instance(cls):
        from lucterios.CORE.parameters import Params
        from lucterios.contacts.models import LegalEntity
        provider = None
        phone_parse = Params.getvalue('mailing-sms-phone-parse').strip()
        provider_name = Params.getvalue('mailing-sms-provider').strip()
        if provider_name != '':
            for sub_provider in cls.__subclasses__():
                if provider_name == sub_provider.__name__:
                    provider = sub_provider(phone_parse.split('|'), LegalEntity.objects.get(id=1).name, Params.getvalue('mailing-sms-option'))
        return provider

    @classmethod
    def is_current_active(cls):
        provider = cls.get_current_instance()
        return (provider is not None) and provider.is_active


class TestProvider(AbstractProvider):

    title = 'Test provider'
    default_options = {'file name': '/tmp/sms.txt', 'max': 10}

    def set_options(self, options):
        AbstractProvider.set_options(self, options)
        self.options['max'] = int(self.options['max'])

    @property
    def is_active(self):
        if not isfile(self.options['file name']):
            self.last_error = "File '%s' not found !" % self.options['file name']
        else:
            self.last_error = None
        return (self.last_error is None)

    def send_sms_ex(self, phone, text):
        sms_file_name = self.options['file name']
        if not isfile(sms_file_name):
            self.last_error = "File '%s' not found !" % sms_file_name
            raise SMSException(self.last_error)
        with open(sms_file_name, 'r') as sms_file:
            nb_line = len(sms_file.readlines())
        if nb_line >= self.options['max']:
            self.last_error = "File '%s' too long !" % sms_file_name
            raise SMSException(self.last_error)
        with open(sms_file_name, 'a') as sms_file:
            sms_file.write("%s : %s => '%s'\n" % (self.sender, phone, text.replace('\n', '|')))
        return


class MailjetProvider(AbstractProvider):

    ERROR_CODE = {
        'mj-0002': _('Malformed JSON, please review the syntax and properties types.'),
        'mj-0003': _('Missing mandatory property.'),
        'mj-0004': _('Type mismatch. Expected type "[t]".'),
        'mj-0005': _('Value "[value]" is invalid. Allowed values are: [allowedValues].'),
        'mj-0006': _('Characters limit exceeded for the property. Max allowed - [number].'),
        'mj-0009': _('The datetime value "[date]" is not a valid RFC3339 datetime format.'),
        'mj-0011': _('Input payload must be less than [size]MB.'),
        'mj-0020': _('Characters limit below the minimum for the property. Min allowed - [number].'),
        'mj-0025': _('Value limit exceeded. Max allowed - [number].'),
        'sms-0001': _('Insufficient funds.'),
        'sms-0002': _('Unsupported country code.'),
        'sms-0003': _('SMS per day limit reached.'),
        'sms-0004': _('No account.'),
    }

    title = 'Mailjet SMS'
    default_options = {'api token': '', 'alias': ''}

    def set_options(self, options):
        AbstractProvider.set_options(self, options)
        if self.options['alias'] == '':
            self.options['alias'] = self.sender
        self.options['alias'] = self.options['alias'][:11]

    def _mailjet_requet(self, service, method_post, data=None):
        import requests
        from json import loads
        url = "https://api.mailjet.com/v4/%s" % service
        headers = {"Authorization": "Bearer %s" % self.options['api token']}
        if method_post is True:
            headers["Content-Type"] = "application/json"
            response = requests.post(url, json=data, headers=headers, verify=True)
        else:
            response = requests.get(url, data=data, headers=headers, verify=True)
        if 400 < response.status_code < 600:
            try:
                json_res = loads(response.content.decode())
            except Exception:
                json_res = {'StatusCode': response.status_code, 'ErrorMessage': response.content.decode()}
        else:
            json_res = response.json()
        if ('StatusCode' in json_res) and (json_res['StatusCode'] != 400):
            getLogger('lucterios.mailing').error("_mailjet_requet(self, '%s', %s, %s) [%s, %s] => %s", service, method_post, data, url, headers, json_res)
        return json_res

    def _check_error(self, json_res):
        if ('StatusCode' in json_res) and (json_res['StatusCode'] == 401):
            return _('Not authorised.')
        if ('StatusCode' in json_res) and (json_res['StatusCode'] == 403):
            return _('You do not have access to this resource.')
        if ('ErrorCode' in json_res) and (json_res['ErrorCode'] in self.ERROR_CODE):
            return self.ERROR_CODE[json_res['ErrorCode']]
        if ('ErrorMessage' in json_res):
            return json_res['ErrorMessage']
        return None

    @property
    def is_active(self):
        if self.options['api token'].strip() == '':
            self.last_error = _('API token empty')
        else:
            json_res = self._mailjet_requet("sms/count", method_post=False)
            self.last_error = self._check_error(json_res)
        return (self.last_error is None)

    def send_sms_ex(self, phone, text):
        data_sms = {"From": self.options['alias'], "To": str(phone), "Text": str(text)}
        json_res = self._mailjet_requet("sms-send", method_post=True, data=data_sms)
        self.last_error = self._check_error(json_res)
        if self.last_error is not None:
            getLogger('lucterios.mailing').error("send_sms_ex(%s)", data_sms)
            raise SMSException(self.last_error)
