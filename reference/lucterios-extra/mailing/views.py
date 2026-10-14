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

from django.utils.translation import gettext_lazy as _
from django.conf import settings

from lucterios.framework.tools import FORMTYPE_MODAL, MenuManage, CLOSE_NO, CLOSE_YES, WrapAction
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompButton, XferCompImage, XferCompLabelForm, XferCompEdit
from lucterios.framework.xferadvance import TITLE_MODIFY, TITLE_OK, TITLE_CANCEL, XferListEditor
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework import signal_and_lock

from lucterios.CORE.parameters import Params
from lucterios.CORE.views import ParamEdit

from lucterios.contacts.models import LegalEntity
from lucterios.mailing.email_functions import will_mail_send, send_email, send_connection_by_email, EmailException
from lucterios.mailing.sms_functions import AbstractProvider


@MenuManage.describ('CORE.change_parameter', FORMTYPE_MODAL, 'contact.conf', _('Change mailing and SMS parameters'))
class Configuration(XferListEditor):
    short_icon = "mdi:mdi-email-variant"
    caption = _("Mailing & SMS parameters")

    def fillreponse_email(self):
        self.new_tab(_('EMail configuration'))
        img = XferCompImage('img_conf')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        conf_email_params = ['mailing-smtpserver', 'mailing-smtpport',
                             'mailing-smtpsecurity', 'mailing-smtpuser', 'mailing-smtppass',
                             'mailing-dkim-private-path', 'mailing-dkim-selector',
                             'mailing-delay-batch', 'mailing-nb-by-batch']
        Params.fill(self, conf_email_params, 1, 1)
        btn = XferCompButton('editparam-email')
        btn.set_location(3, 1, 1, 5)
        btn.set_is_mini(True)
        btn.set_action(self.request, ParamEdit.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO, params={'params': conf_email_params})
        self.add_component(btn)
        if will_mail_send():
            btn = XferCompButton('tryemail')
            btn.set_location(1, 10, 2)
            btn.set_action(self.request, SendEmailTry.get_action(_('Send'), ''), close=CLOSE_NO)
            self.add_component(btn)

    def fillreponse_message(self):
        self.new_tab(_('Default message'))
        img = XferCompImage('img_msg')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        msg_params = ['mailing-msg-connection']
        Params.fill(self, msg_params, 1, 1)
        btn = XferCompButton('editmsg')
        btn.set_location(1, 10, 2)
        btn.set_action(self.request, ParamEdit.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO, params={'params': msg_params})
        self.add_component(btn)

    def fillreponse_sms(self):
        self.new_tab(_('SMS configuration'))
        img = XferCompImage('img_sms_conf')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        conf_sms_params1 = ['mailing-sms-provider']
        Params.fill(self, conf_sms_params1, 1, 1)
        btn = XferCompButton('editparam-sms1')
        btn.set_location(1, 3)
        btn.set_is_mini(False)
        btn.set_action(self.request, ParamEdit.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO, params={'params': conf_sms_params1})
        self.add_component(btn)
        provider = AbstractProvider.get_current_instance()
        if provider is not None:
            lbl = XferCompLabelForm('img_sms_sep')
            lbl.set_value("{[hr/]}")
            lbl.set_location(1, 4, 2)
            self.add_component(lbl)
            conf_sms_params2 = ['mailing-sms-phone-parse', 'mailing-sms-option']
            Params.fill(self, conf_sms_params2, 1, 5)
            btn = XferCompButton('editparam-sms2')
            btn.set_location(3, 5, 1, 2)
            btn.set_is_mini(True)
            btn.set_action(self.request, ParamEdit.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO, params={'params': conf_sms_params2})
            self.add_component(btn)
            if provider.is_active:
                btn = XferCompButton('trysms')
                btn.set_location(1, 7, 2)
                btn.set_action(self.request, SendSmsTry.get_action(_('Send'), ''), close=CLOSE_NO)
                self.add_component(btn)
            else:
                lbl_err = XferCompLabelForm('error_sms')
                lbl_err.set_color('red')
                lbl_err.set_value_center(provider.last_error)
                lbl_err.set_location(1, 7, 2)
                self.add_component(lbl_err)

    def fillresponse(self):
        XferContainerCustom.fillresponse(self)
        self.fillreponse_email()
        self.fillreponse_message()
        self.fillreponse_sms()


@MenuManage.describ('CORE.add_parameter')
class SendEmailTry(XferContainerAcknowledge):
    short_icon = "mdi:mdi-email-variant"
    caption = _("EMail try")

    def fillresponse(self):
        if not will_mail_send():
            raise LucteriosException(IMPORTANT, _('Bad email parameter!'))
        legal = LegalEntity.objects.get(id=1)
        if self.getparam('CONFIRME') is None:
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 3)
            dlg.add_component(img)
            lbl = XferCompLabelForm('lbl_title')
            lbl.set_location(1, 0, 2)
            lbl.set_value_as_header(self.caption)
            dlg.add_component(lbl)
            email = XferCompEdit('recipient')
            email.set_location(1, 1)
            email.set_value(legal.email)
            email.mask = r"[^@]+@[^@]+\.[^@]+"
            email.description = _("email")
            dlg.add_component(email)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), close=CLOSE_YES, params={'CONFIRME': 'YES'})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            address = []
            address.append("")
            address.append("")
            address.append(str(legal))
            address.append(legal.address)
            address.append("%s %s" % (legal.postal_code, legal.city))
            message = _('EMail sent to check configuration')
            message += "{[br/]}".join(address).replace('{[newline]}', "{[br/]}").replace("\n", '{[br/]}')
            bad_sended = send_email(self.getparam('recipient'), _("EMail try"), "<html><body>%s</body></html>" % message.replace('{[', '<').replace(']}', '>'))
            if len(bad_sended) != 0:
                raise EmailException(bad_sended)
            self.message(_("EMail send, check it."))


@MenuManage.describ('CORE.add_parameter')
class SendSmsTry(XferContainerAcknowledge):
    short_icon = "mdi:mdi-email-variant"
    caption = _("SMS try")

    def fillresponse(self):
        provider = AbstractProvider.get_current_instance()
        if (provider is None) or not provider.is_active:
            raise LucteriosException(IMPORTANT, _('Bad SMS parameter!'))
        legal = LegalEntity.objects.get(id=1)
        if self.getparam('CONFIRME') is None:
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 3)
            dlg.add_component(img)
            lbl = XferCompLabelForm('lbl_title')
            lbl.set_location(1, 0, 2)
            lbl.set_value_as_header(self.caption)
            dlg.add_component(lbl)
            phone = XferCompEdit('phone')
            phone.set_location(1, 1)
            phone.set_value(AbstractProvider.simple_phone(legal.tel1))
            phone.mask = Params.getvalue('mailing-sms-phone-parse').strip().split('|')[0]
            phone.description = _("phone")
            dlg.add_component(phone)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), close=CLOSE_YES, params={'CONFIRME': 'YES'})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            provider.send_sms(self.getparam('phone'), _('SMS sent to check configuration'))
            self.message(_("SMS send, check it."))


@signal_and_lock.Signal.decorate('send_connection')
def send_connection_email(email_adress, username, passwd):
    if will_mail_send():
        if email_adress and username and passwd:
            send_connection_by_email(email_adress, email_adress if settings.ASK_LOGIN_EMAIL else username, passwd)
        return True
    else:
        return False


@signal_and_lock.Signal.decorate('conf_wizard')
def conf_wizard_mailing(wizard_ident, xfer):
    if isinstance(wizard_ident, list) and (xfer is None):
        wizard_ident.append(("mailing_params", 52))
    elif (xfer is not None) and (wizard_ident == "mailing_params"):
        xfer.add_title(_("Lucterios mailing"), _("Mailing parameters"))
        lbl = XferCompLabelForm("nb_mail_send")
        lbl.set_location(1, xfer.get_max_row() + 1)
        xfer.add_component(lbl)
        if will_mail_send():
            lbl.set_value(_('email properly configured'))
        else:
            lbl.set_value(_('email not configured'))
        btn = XferCompButton("btnconf")
        btn.set_location(3, xfer.get_max_row())
        btn.set_action(xfer.request, Configuration.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO)
        xfer.add_component(btn)


@signal_and_lock.Signal.decorate('param_change')
def paramchange_mailing(params):
    if ('mailing-sms-provider' in params) or ('mailing-sms-option' in params):
        provider = AbstractProvider.get_current_instance()
        if provider is not None:
            Params.setvalue('mailing-sms-option', provider.options_text)
