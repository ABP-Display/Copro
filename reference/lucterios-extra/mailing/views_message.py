# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.http.response import HttpResponse
from base64 import b64decode
from logging import getLogger

from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q

from lucterios.framework.xferadvance import XferListEditor, TITLE_EDIT, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_CLONE, \
    XferTransition, TITLE_OK, TITLE_CANCEL, TITLE_CREATE, TITLE_CLOSE
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, SELECT_SINGLE, CLOSE_YES, SELECT_MULTI, \
    FORMTYPE_REFRESH, WrapAction, CLOSE_NO, get_url_from_request
from lucterios.framework.xferbasic import XferContainerAbstract
from lucterios.framework.error import LucteriosException, MINOR
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XferContainerCustom, XFER_DBOX_ERROR
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompCheck, XferCompEdit
from lucterios.CORE.xferprint import XferPrintReporting

from lucterios.contacts.tools import ContactSelection
from lucterios.contacts.models import LegalEntity
from lucterios.documents.models import DocumentContainer
from lucterios.documents.views import DocumentSearch, DocumentShow
from lucterios.mailing.models import Message, add_messaging_in_scheduler, EmailSent
from lucterios.mailing.email_functions import will_mail_send
from lucterios.mailing.sms_functions import AbstractProvider
from lucterios.CORE.parameters import Params


MenuManage.add_sub("mailing.actions", "office", short_icon='mdi:mdi-email-arrow-right-outline', caption=_("Messaging"), desc=_("Create and send mailing to contacts."), pos=60)


class MessageList(XferListEditor):
    model = Message
    field_id = 'message'

    def fillresponse_header(self):
        message_type = self.getparam('message_type', 0)
        self.filter = Q(message_type=message_type)

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        root_url = get_url_from_request(self.request).split('/')
        add_messaging_in_scheduler(check_nb=True, http_root_address=root_url)


@MenuManage.describ('mailing.change_message', FORMTYPE_NOMODAL, 'mailing.actions', _('Manage list of message for mailing.'))
class MessageEmailList(MessageList):
    short_icon = "mdi:mdi-email-outline"
    caption = _("Messages EMail")

    def fillresponse_header(self):
        self.params['message_type'] = 0
        MessageList.fillresponse_header(self)

    def fillresponse(self):
        MessageList.fillresponse(self)
        if not will_mail_send():
            lbl_err = XferCompLabelForm('error_email')
            lbl_err.set_color('red')
            lbl_err.set_value_center(_('Email not configure!'))
            lbl_err.set_location(0, self.get_max_row() + 1, 5)
            self.add_component(lbl_err)


@MenuManage.describ('mailing.change_message', FORMTYPE_NOMODAL, 'mailing.actions', _('Manage list of message for SMS.'))
class MessageSMSList(MessageList):
    short_icon = "mdi:mdi-message-reply-text-outline"
    caption = _("Messages SMS")

    def fillresponse_header(self):
        self.params['message_type'] = 1
        MessageList.fillresponse_header(self)

    def fillresponse(self):
        MessageList.fillresponse(self)
        grid = self.get_components(self.field_id)
        grid.get_header('subject').descript = _('title')

        provider = AbstractProvider.get_current_instance()
        if (provider is None) or not provider.is_active:
            last_error = _("SMS bad configured : %s") % provider.last_error if (provider is not None) else _('SMS not configure!')
            lbl_err = XferCompLabelForm('error_sms')
            lbl_err.set_color('red')
            lbl_err.set_value_center(last_error)
            lbl_err.set_location(0, self.get_max_row() + 1, 5)
            self.add_component(lbl_err)


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus')
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', close=CLOSE_YES, condition=lambda xfer: xfer.item.status == 0)
@MenuManage.describ('mailing.add_message')
class MessageAddModify(XferAddEditor):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption_add = _("Add message")
    caption_modify = _("Modify message")

    def fillresponse(self):
        XferAddEditor.fillresponse(self)
        img = self.get_components('img')
        if self.getparam('message_type', int(self.item.message_type)) == 0:
            img.set_value("mdi:mdi-email-outline", '#')
        else:
            img.set_value("mdi:mdi-message-outline", '#')


@ActionsManage.affect_grid(TITLE_CLONE, short_icon='mdi:mdi-content-copy', unique=SELECT_SINGLE)
@MenuManage.describ('mailing.add_message')
class MessageClone(XferContainerAcknowledge):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Add message")

    def fillresponse(self):
        if self.item.is_dynamic:
            raise LucteriosException(MINOR, _('This message can not be clone!'))
        new_item = Message()
        new_item.date = None
        new_item.status = 0
        new_item.message_type = self.item.message_type
        new_item.subject = self.item.subject
        new_item.body = self.item.body
        new_item.recipients = self.item.recipients
        new_item.email_to_send = ""
        new_item.doc_in_link = self.item.doc_in_link
        new_item.save()
        for doc in self.item.attachments.all():
            new_item.attachments.add(doc)
        self.params[self.field_id] = new_item.id
        self.redirect_action(MessageShow.get_action('', ''))


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('mailing.change_message')
class MessageShow(XferShowEditor):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Show message")

    def fillresponse(self):
        XferShowEditor.fillresponse(self)
        if self.item.message_type == 0:
            short_icon = 'mdi:mdi-email-outline'
            action_caption = _("Emails")
        else:
            short_icon = 'mdi:mdi-message-outline'
            action_caption = _("SMS")
        img = self.get_components('img')
        img.set_value(short_icon, '#')
        for action, _modal, _close, _select, params in self.actions:
            if (action.url_text == 'lucterios.mailing/messageTransition') and ('TRANSITION' in params) and (params['TRANSITION'] == 'sending'):
                action.caption = action_caption
                action.short_icon = short_icon


@ActionsManage.affect_show(_("EMail try"), short_icon="mdi:mdi-email-outline", condition=lambda xfer: (xfer.item.message_type == 0) and will_mail_send() and (xfer.item.status == 0))
@MenuManage.describ('mailing.add_message')
class MessageSendEmailTry(XferContainerAcknowledge):
    short_icon = "mdi:mdi-email-outline"
    model = Message
    field_id = 'message'
    caption = _("Show message")
    caption = _("EMail try")

    def fillresponse(self):
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
            email_sent = EmailSent.objects.create(message=self.item, contact=None, email=self.getparam('recipient'), date=timezone.now())
            try:
                email_sent.send_email(get_url_from_request(self.request))
                if email_sent.success:
                    self.message(_("EMail send, check it."))
                else:
                    self.message(email_sent.error, XFER_DBOX_ERROR)
            finally:
                email_sent.delete()


@ActionsManage.affect_show(_("SMS try"), short_icon="mdi:mdi-message-reply-text-outline", condition=lambda xfer: (xfer.item.message_type == 1) and AbstractProvider.is_current_active() and (xfer.item.status == 0))
@MenuManage.describ('mailing.add_message')
class MessageSendSMSTry(XferContainerAcknowledge):
    short_icon = "mdi:mdi-message-reply-text-outline"
    model = Message
    field_id = 'message'
    caption = _("Show message")
    caption = _("SMS try")

    def fillresponse(self):
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
            provider = AbstractProvider.get_current_instance()
            provider.send_sms(self.getparam('phone'), self.item.body.replace('{[br/]}', '\n'))
            self.message(_("SMS send, check it."))


@ActionsManage.affect_transition("status")
@MenuManage.describ('mailing.add_message')
class MessageTransition(XferTransition):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'

    def fill_confirm(self, transition, trans):
        if transition == 'sending':
            if self.confirme(_("Do you want to sent this message to %(nb_contact)d contacts?") % {'nb_contact': self.item.contact_nb - len(self.item.contact_noemail) - len(self.item.contact_nosms)}):
                self._confirmed(transition)
                self.message(_("This message is being transmitted"))
        else:
            XferTransition.fill_confirm(self, transition, trans)


@ActionsManage.affect_show(_("Info"), short_icon="mdi:mdi-information-slab-circle-outline", modal=FORMTYPE_NOMODAL, condition=lambda xfer: xfer.item.emailsent_set.count() > 0)
@MenuManage.describ('mailing.change_message')
class MessageSentInfo(XferContainerCustom):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Transmission report")
    methods_allowed = ('GET', )

    def fillresponse(self, show_only_failed=False):
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        begin = XferCompLabelForm('title')
        begin.set_location(1, 0, 2)
        begin.set_value_as_title(_('Transmission report'))
        self.add_component(begin)

        fields = [((_('date begin of send'), 'date_begin'), (_('date end of send'), 'date_end')),
                  ((_('statistic'), 'statistic'), ),
                  ('emailsent_set',)]
        self.filltab_from_model(1, 1, True, fields)
        grid = self.get_components('emailsent')
        if not show_only_failed:
            grid.delete_header('error')
        if show_only_failed or (self.item.message_type != 0):
            grid.delete_header('last_open_date')
            grid.delete_header('nb_open')

        check = XferCompCheck('show_only_failed')
        check.set_value(show_only_failed)
        check.description = _('Show only failed')
        check.set_location(1, 4, 2)
        check.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(check)

        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@ActionsManage.affect_show(_("Letters"), short_icon="mdi:mdi-file-sign", condition=lambda xfer: (xfer.item.message_type == 0) and (xfer.item.status == 1) and not xfer.item.is_dynamic)
@MenuManage.describ('mailing.change_message')
class MessageLetter(XferPrintReporting):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Write message")
    methods_allowed = ('GET', )

    def items_callback(self):
        items = []
        for current_contact in self.item.get_email_contacts():
            new_item = Message.objects.get(id=self.item.id)
            new_item.contact = current_contact
            items.append(new_item)
        return items


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('mailing.delete_message')
class MessageDel(XferDelete):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Delete message")


@MenuManage.describ('mailing.add_message')
class MessageValidRecipient(XferContainerAcknowledge):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Add recipient to message")
    methods_allowed = ('POST', 'PUT')

    def fillresponse(self, modelname='', CRITERIA=''):
        self.item.add_recipient(modelname, CRITERIA)


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', model_name='recipient_list', condition=lambda xfer, gridname: xfer.item.status == 0)
@MenuManage.describ('mailing.add_message')
class MessageAddRecipient(ContactSelection):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Add recipient to message")
    final_class = MessageValidRecipient
    methods_allowed = ('POST', 'PUT')


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_SINGLE, model_name='recipient_list', condition=lambda xfer, gridname: xfer.item.status == 0)
@MenuManage.describ('mailing.add_message')
class MessageDelRecipient(XferContainerAcknowledge):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Delete recipient")
    methods_allowed = ('DELETE', )

    def fillresponse(self, recipient_list=-1):
        if self.confirme(_("Do you want to delete this recipient?")):
            self.item.del_recipient(recipient_list)


@MenuManage.describ('mailing.add_message')
class MessageValidInsertDoc(XferContainerAcknowledge):
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    caption = _("Insert document to message")

    def fillresponse(self, document=0):
        self.item.attachments.add(DocumentContainer.objects.get(id=document))


@MenuManage.describ('mailing.add_message')
class MessageInsertDoc(DocumentSearch):
    caption = _("Insert document to message")
    mode_select = SELECT_SINGLE
    select_class = MessageValidInsertDoc
    methods_allowed = ('POST', 'PUT')


@MenuManage.describ('mailing.add_message')
class MessageRemoveDoc(XferContainerAcknowledge):
    caption = _("Remove document to message")
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    methods_allowed = ('DELETE', )

    def fillresponse(self, attachment=[]):
        if self.confirme(_('Do you want to remove those documents ?')):
            for doc in DocumentContainer.objects.filter(id__in=attachment):
                self.item.attachments.remove(doc)


@MenuManage.describ('mailing.add_message')
class MessageShowDoc(XferContainerAcknowledge):
    caption = _("Remove document to message")
    short_icon = "mdi:mdi-text-box-edit-outline"
    model = Message
    field_id = 'message'
    methods_allowed = ('GET', )

    def fillresponse(self, attachment=0):
        self.redirect_action(DocumentShow.get_action(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline'), params={'document': attachment})


@MenuManage.describ('')
class EmailSentAddForStatistic(XferContainerAbstract):
    short_icon = "mdi:mdi-check"
    observer_name = 'Statistic'
    caption = 'EmailSentAddForStatistic'
    model = EmailSent
    field_id = 'emailsent'
    methods_allowed = ('GET', )

    def fillresponse(self, emailsent=0):
        try:
            email_sent = EmailSent.objects.get(id=emailsent)
            email_sent.last_open_date = timezone.now()
            email_sent.nb_open += 1
            email_sent.save()
        except Exception as exp:
            getLogger("lucterios.mailing").debug("EmailSentAddForStatistic - error=%s" % exp)

    def get_response(self):
        SMALL_IMAGE = "/9j/4AAQSkZJRgABAQEASABIAAD//gATQ3JlYXRlZCB3aXRoIEdJTVD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wgARCAABAAEDAREAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQBAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhADEAAAAVSf/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABCf/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPxB//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPxB//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxB//9k="
        return HttpResponse(b64decode(SMALL_IMAGE), content_type='image/jpg')
