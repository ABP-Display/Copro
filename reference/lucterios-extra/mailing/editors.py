# -*- coding: utf-8 -*-
'''
Describe database model for Django

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

from django.utils.translation import gettext as _

from lucterios.framework.editors import LucteriosEditor
from lucterios.framework.xfercomponents import XferCompGrid, XferCompCheckList
from lucterios.mailing.email_functions import will_mail_send
from lucterios.framework.tools import FORMTYPE_MODAL, CLOSE_NO, SELECT_SINGLE, SELECT_NONE, SELECT_MULTI
from lucterios.framework.xferadvance import TITLE_EDIT
from lucterios.mailing.views_message import MessageRemoveDoc, MessageInsertDoc, \
    MessageShowDoc
from lucterios.mailing.sms_functions import AbstractProvider


class MessageEditor(LucteriosEditor):

    def before_save(self, xfer):
        field_names = xfer.getparam('sms_field_names')
        if field_names is not None:
            xfer.item.set_sms_field_names(field_names)
        return

    def edit(self, xfer):
        obj_body = xfer.get_components('body')
        if xfer.getparam('message_type', int(xfer.item.message_type)) == 0:
            obj_body.with_hypertext = True
        else:
            xfer.remove_component('doc_in_link')
            xfer.get_components('subject').description = _('title')
            chk = XferCompCheckList('sms_field_names')
            chk.set_location(1, xfer.get_max_row() + 1)
            chk.description = _('phone fields')
            chk.set_select(xfer.item.get_all_phone_field_names())
            chk.set_value(xfer.item.get_sms_field_names(translate=False))
            chk.simple = 2
            xfer.add_component(chk)
        return LucteriosEditor.edit(self, xfer)

    def _manage_documents(self, xfer):
        old_documents = xfer.get_components('attachments')
        xfer.remove_component('attachments')
        if (xfer.item.message_type == 1) or xfer.item.is_dynamic:
            xfer.remove_component('__tab_3')
            xfer.remove_component('doc_in_link')
            xfer.remove_component('empty')
        else:
            new_documents = XferCompGrid('attachment')
            new_documents.tab = old_documents.tab
            new_documents.set_location(old_documents.col, old_documents.row, old_documents.colspan)
            new_documents.set_model(self.item.attachments.all(), ["name", "description", "date_modification"], xfer)
            new_documents.add_action(xfer.request, MessageShowDoc.get_action(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline'),
                                     modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE)
            if self.item.status == 0:
                new_documents.add_action(xfer.request, MessageRemoveDoc.get_action(_("Remove"), short_icon='mdi:mdi-delete-outline'),
                                         modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_MULTI)
                new_documents.add_action(xfer.request, MessageInsertDoc.get_action(_("Insert"), short_icon='mdi:mdi-pencil-plus-outline'),
                                         modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_NONE)
            xfer.tab = new_documents.tab
            xfer.add_component(new_documents)

    def _remove_cmp(self, xfer, compid):
        if compid == 0:
            xfer.remove_component('contact_nb')
        if (xfer.item.message_type == 1) or (len(self.item.get_email_contacts(False)) == 0) or not will_mail_send():
            xfer.remove_component('contact_noemail')
        if (xfer.item.message_type == 0) or (len(self.item.get_sms_contacts(False)) == 0) or not AbstractProvider.is_current_active():
            xfer.remove_component('contact_nosms')
        xfer.remove_component('recipients')

    def _manage_recipients(self, xfer):
        obj_recipients = xfer.get_components('recipients')
        new_recipients = XferCompGrid('recipient_list')
        new_recipients.tab = obj_recipients.tab
        new_recipients.set_location(obj_recipients.col, obj_recipients.row, obj_recipients.colspan)
        new_recipients.add_header("model", _('model'))
        new_recipients.add_header("filter", _('filter'))
        compid = 0
        for model_title, filter_desc in self.item.recipients_description:
            new_recipients.set_value(compid, "model", model_title)
            new_recipients.set_value(compid, "filter", filter_desc)
            compid += 1
        self._remove_cmp(xfer, compid)
        new_recipients.add_action_notified(xfer, 'recipient_list')
        xfer.tab = new_recipients.tab
        xfer.add_component(new_recipients)
        contact_nb = xfer.get_components('contact_nb')
        if (contact_nb is not None) and (self.item.nb_total > 0):
            xfer.tab = contact_nb.tab
            xfer.fill_from_model(contact_nb.col, contact_nb.row + 1, True, [((_('statistic'), 'statistic'), )])

    def show(self, xfer):
        if xfer.item.message_type == 0:
            xfer.remove_component('size_sms')
            xfer.remove_component('sms_field_names')
            obj_body = xfer.get_components('body')
            obj_body.value = "{[div style='border:1px solid black;background-color:#EEE;padding:5px;']}%s{[div]}" % obj_body.value
            xfer.move_components('body', 0, 2)
        else:
            xfer.get_components('subject').description = _('title')

        self._manage_recipients(xfer)
        self._manage_documents(xfer)
        return LucteriosEditor.show(self, xfer)
