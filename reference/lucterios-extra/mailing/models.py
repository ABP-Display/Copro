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
from datetime import date
from html2text import HTML2Text
from logging import getLogger, DEBUG
from _io import BytesIO
import json

from django.utils.translation import gettext_lazy as _
from django.db import models
from django.db.models.query import QuerySet
from django.apps import apps
from django.utils import timezone

from lucterios.framework.models import LucteriosModel
from lucterios.framework.model_fields import FSMIntegerField, transition
from lucterios.framework.model_fields import LucteriosVirtualField, \
    LucteriosScheduler
from lucterios.framework.xfersearch import get_search_query_from_criteria
from lucterios.framework.printgenerators import ReportingGenerator
from lucterios.framework.tools import toHtml, get_date_formating, get_url_from_request
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.error import LucteriosException, GRAVE
from lucterios.framework.filetools import remove_accent
from lucterios.framework.auditlog import auditlog
from lucterios.framework.xferprinting import PRINT_EXT_FILE, PRINT_PDF_FILE
from lucterios.CORE.models import Parameter, PrintModel, LucteriosGroup
from lucterios.CORE.parameters import Params

from lucterios.contacts.models import AbstractContact, CustomField
from lucterios.documents.models import DocumentContainer
from lucterios.documents.models_legacy import Document
from lucterios.mailing.email_functions import will_mail_send, send_email, split_doubled_email
from lucterios.mailing.sms_functions import AbstractProvider


class MessageLine(LucteriosModel):
    line = models.TextField(_('line'), null=False, default="")

    @classmethod
    def get_default_fields(cls, status=-1):
        return ['line']

    class Meta(object):
        default_permissions = []
        verbose_name = _('body')
        verbose_name_plural = _('bodies')


class MessageLineSet(QuerySet):

    def __init__(self, model=None, query=None, using=None, hints=None):
        QuerySet.__init__(self, model=MessageLine, query=query, using=using, hints=hints)
        self._result_cache = None
        self.pt_id = 0
        self.model._meta.pk = Message()._meta.pk
        body = self._hints['body']
        body = body.replace('\n', '')
        body = body.replace('{[br]}', '{[br/]}')
        body = body.replace('{[p]}', '')
        body = body.replace('{[/p]}', '\n')
        self.lines = body.split('\n')

    def _fetch_all(self):
        if self._result_cache is None:
            self._result_cache = []
            line_id = 1
            for line in self.lines:
                self._result_cache.append(MessageLine(id=line_id, line=line))
                line_id += 1


class Message(LucteriosModel):
    MESSAGE_TYPE_EMAIL = 0
    MESSAGE_TYPE_SMS = 1
    MESSAGE_TYPE_LIST = ((MESSAGE_TYPE_EMAIL, _('email')), (MESSAGE_TYPE_SMS, _('sms')))

    STATUS_OPEN = 0
    STATUS_VALIDATED = 1
    STATUS_SENDING = 2
    STATUS_LIST = ((STATUS_OPEN, _('open')), (STATUS_VALIDATED, _('valided')), (STATUS_SENDING, _('sending')))

    subject = models.CharField(_('subject'), max_length=50, blank=False)
    body = models.TextField(_('body'), default="")
    message_type = FSMIntegerField(verbose_name=_('type'), default=0, choices=MESSAGE_TYPE_LIST)
    status = FSMIntegerField(verbose_name=_('status'), default=0, choices=STATUS_LIST)
    recipients = models.TextField(_('recipients'), default="", null=False)
    date = models.DateField(verbose_name=_('date'), null=True)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=True, on_delete=models.SET_NULL)
    email_to_send = models.TextField(_('email to send'), default="")

    documents = models.ManyToManyField(Document, verbose_name=_('documents'), blank=True)
    attachments = models.ManyToManyField(DocumentContainer, verbose_name=_('documents'), blank=True)
    doc_in_link = models.BooleanField(_('documents in link'), null=False, default=False)

    size_sms = LucteriosVirtualField(verbose_name=_('sms size'), compute_from='get_size_sms')
    sender_nb = LucteriosVirtualField(verbose_name=_('number of sender'), compute_from='get_sender_nb', format_string='N')
    contact_nb = LucteriosVirtualField(verbose_name=_('number of recipients'), compute_from='get_contact_nb', format_string='N')
    contact_noemail = LucteriosVirtualField(verbose_name=_('without email address'), compute_from='get_contact_noemail')
    contact_nosms = LucteriosVirtualField(verbose_name=_('without sms/phone'), compute_from='get_contact_nosms')
    sms_field_names = LucteriosVirtualField(verbose_name=_('phone fields'), compute_from=lambda this: list(this.get_sms_field_names()))

    def __init__(self, *args, **kwargs):
        LucteriosModel.__init__(self, *args, **kwargs)
        self._show_only_failed = False
        self._last_xfer = None

    def set_context(self, xfer):
        self._show_only_failed = xfer.getparam('show_only_failed', False)
        self._last_xfer = xfer

    @property
    def emailsent_query(self):
        if self._show_only_failed:
            return ~models.Q(error='')
        else:
            return models.Q()

    @classmethod
    def get_default_fields(cls):
        return ['status', 'date', 'subject', 'sender_nb']

    @classmethod
    def get_show_fields(cls):
        return {'': [('status', 'date')],
                _('001@Message'): ['subject', 'body', 'size_sms', 'sms_field_names'],
                _('002@Recipients'): ['recipients', ('contact_nb', 'contact_noemail', 'contact_nosms')],
                _('003@Documents'): ['attachments', (('', 'empty'),), 'doc_in_link']
                }

    @classmethod
    def get_edit_fields(cls):
        return ['subject', 'body', 'doc_in_link']

    @classmethod
    def get_print_fields(cls):
        return ['status', 'date', 'subject', 'body', 'line_set', 'line_set.line', 'contact', 'OUR_DETAIL']

    @property
    def empty(self):
        return ""

    def get_sender_nb(self):
        if self.nb_total > 0:
            return self.nb_total
        else:
            return self.get_contact_nb()

    def get_contact_nb(self):
        if self.message_type == self.MESSAGE_TYPE_EMAIL:
            return len(self.get_email_contacts())
        elif self.message_type == self.MESSAGE_TYPE_SMS:
            return len(self.get_sms_contacts())
        return 0

    @property
    def line_set(self):
        return MessageLineSet(hints={'body': self.body})

    def get_size_sms(self):
        return len(self.body.replace('{[br/]}', '\n'))

    def get_contact_noemail(self):
        no_emails = self.get_email_contacts(False)
        return [str(no_email) for no_email in no_emails]

    def get_contact_nosms(self):
        def show_phones(contact):
            return " ".join([getattr(contact, field_name, '') for field_name in self.get_sms_field_names(translate=False)])
        no_sms_list = self.get_sms_contacts(False)
        return ["%s : %s" % (no_sms, show_phones(no_sms).strip()) for no_sms in no_sms_list]

    def get_email_contacts(self, email=None):
        def append_contact(new_contact):
            if new_contact not in contact_list:
                contact_list.append(new_contact)
        contact_list = []
        if self.message_type == self.MESSAGE_TYPE_EMAIL:
            for modelname, item in self.get_recipients():
                model = apps.get_model(modelname)
                contact_filter = item[0]
                if (email is not None) and (model.get_field_by_name('email') is None):
                    for contact in model.objects.filter(contact_filter).distinct():
                        if (email is True) and hasattr(contact, 'get_email') and (contact.get_email() != []):
                            append_contact(contact)
                        elif (email is False) and (not hasattr(contact, 'get_email') or (contact.get_email() == [])):
                            append_contact(contact)
                else:
                    if (email is not None) and (model.get_field_by_name('email') is not None):
                        contact_filter &= ~models.Q(email='') if email else models.Q(email='')
                    for contact in model.objects.filter(contact_filter).distinct():
                        append_contact(contact)
        return contact_list

    def get_sms_contacts(self, sms=None):
        contact_list = []
        if self.message_type == self.MESSAGE_TYPE_SMS:
            provider = AbstractProvider.get_current_instance()
            if (sms is None) or (provider is not None):
                field_names = list(self.get_sms_field_names(translate=False))
                for modelname, item in self.get_recipients():
                    model = apps.get_model(modelname)
                    contact_filter = item[0]
                    for contact in model.objects.filter(contact_filter).distinct():
                        if (sms is None) or \
                            ((sms is True) and provider.has_valid_phone(contact, field_names)) or \
                                ((sms is False) and not provider.has_valid_phone(contact, field_names)):
                            if contact not in contact_list:
                                contact_list.append(contact)
        return contact_list

    @property
    def recipients_description(self):
        for modelname, item in self.get_recipients():
            model = apps.get_model(modelname)
            yield (model._meta.verbose_name.title(), " {[br/]}".join(item[1].values()))

    def get_all_phone_field_names(self):
        field_names = []
        field_names.append(('tel1', AbstractContact.get_field_by_name('tel1').verbose_name))
        field_names.append(('tel2', AbstractContact.get_field_by_name('tel2').verbose_name))
        for cf_model in CustomField.objects.filter(kind=0):
            if (cf_model.get_args()['multi'] is False) and issubclass(cf_model.model_associated(), AbstractContact):
                field_names.append((cf_model.get_fieldname(), cf_model.name))
        return field_names

    def get_sms_field_names(self, translate=True):
        for item in self.recipients.split('\n'):
            if item.startswith('# fieldnames: '):
                for field_name in item[14:].split(';'):
                    if translate:
                        dep_field = AbstractContact.get_field_by_name(field_name)
                        if dep_field is not None:
                            field_name = dep_field.verbose_name
                    yield field_name
                break

    def set_sms_field_names(self, fieldnames):
        recipient_list = self.recipients.split('\n')
        self.recipients = '# fieldnames: %s\n' % fieldnames
        for item in recipient_list:
            if (item != '') and not item.startswith('# fieldnames: '):
                self.recipients += item + "\n"
        self.save()

    def get_recipients(self):
        for item in self.recipients.split('\n'):
            if (item != '') and not item.startswith('# '):
                item_splited = item.split(' ')
                modelname = item_splited[0]
                criteria = " ".join(item_splited[1:])
                yield modelname, get_search_query_from_criteria(criteria, apps.get_model(modelname))

    def add_recipient(self, modelname, criteria):
        if self.status == self.STATUS_OPEN:
            self.recipients += modelname + ' ' + criteria + "\n"
            self.save()

    def del_recipient(self, recipients):
        if (self.status == self.STATUS_OPEN) and (recipients >= 0):
            recipient_list = self.recipients.split('\n')
            self.recipients = ""
            list_idx = 0
            while list_idx < len(recipient_list):
                if recipient_list[list_idx].startswith('# '):
                    self.recipients += recipient_list[list_idx] + "\n"
                    del recipient_list[list_idx]
                else:
                    list_idx += 1
            if recipients < len(recipient_list):
                del recipient_list[recipients]
                self.recipients += "\n".join(recipient_list)
                self.save()

    transitionname__valid = _("Valid")

    @transition(field=status, source=STATUS_OPEN, target=STATUS_VALIDATED, conditions=[lambda item:len(list(item.get_recipients())) > 0])
    def valid(self):
        self.date = date.today()

    def get_printmodel_names(self):
        printmodel_name = {}
        for last_sending_item in self.email_to_send.split('\n'):
            if len(last_sending_item.split(':')) == 3:
                printmodel_name[last_sending_item.split(':')[0]] = last_sending_item.split(':')[2]
        for old_emailsent in self.emailsent_set.all():
            last_sending_item = old_emailsent.email
            if len(last_sending_item.split(':')) == 3:
                printmodel_name[last_sending_item.split(':')[0]] = last_sending_item.split(':')[2]
        return printmodel_name

    @property
    def is_dynamic(self):
        return len(self.get_printmodel_names()) > 0

    def prep_sending(self):
        if self.message_type == self.MESSAGE_TYPE_EMAIL:
            item_list = self._prep_sending_email()
        elif self.message_type == self.MESSAGE_TYPE_SMS:
            item_list = self._prep_sending_sms()
        else:
            item_list = []
        item_list.sort()
        self.email_to_send = "\n".join(item_list)
        self.save()
        self.emailsent_set.all().delete()
        return len(item_list)

    def _prep_sending_email(self):
        printmodel_name = self.get_printmodel_names()
        if len(printmodel_name) == 0:
            email_list = {}
            for contact in self.get_email_contacts(True):
                for email1 in contact.email.split(';'):
                    for email2 in email1.split(','):
                        if email2 not in email_list:
                            email_list[email2] = contact.id
            return ["%d:%s" % (contact_id, email) for email, contact_id in email_list.items()]
        else:
            email_list = []
            for contact in self.get_email_contacts(True):
                model_name = contact.__class__.get_long_name()
                email_list.append("%s:%d:%s" % (model_name, contact.id, printmodel_name[model_name] if model_name in printmodel_name.keys() else "0"))
            return email_list

    def _prep_sending_sms(self):
        sms_list = {}
        provider = AbstractProvider.get_current_instance()
        if (provider is not None) and provider.is_active:
            field_names = list(self.get_sms_field_names(translate=False))
            for contact in self.get_sms_contacts(True):
                for field_name in field_names:
                    new_phone = provider.convert_sms_phone(getattr(contact, field_name, ''), return_simple=True)
                    if (new_phone is not None) and (new_phone not in sms_list):
                        sms_list[new_phone] = contact.id
        return ["%d:%s" % (contact_id, new_phone) for new_phone, contact_id in sms_list.items()]

    transitionname__sending = _("Emails")

    def can_be_send(self):
        return ((self.message_type == self.MESSAGE_TYPE_EMAIL) and will_mail_send()) or ((self.message_type == self.MESSAGE_TYPE_SMS) and AbstractProvider.is_current_active())

    @transition(field=status, source=1, target=2, conditions=[lambda item: item.can_be_send()])
    def sending(self):
        if self.can_be_send():
            self.prep_sending()
            if (self._last_xfer is not None) and hasattr(self._last_xfer, "request"):
                root_url = get_url_from_request(self._last_xfer.request)
            else:
                root_url = ''
            getLogger('lucterios.mailing').debug('Message.sending() -> add_messaging_in_scheduler(http_root_address=%s)', root_url)
            add_messaging_in_scheduler(check_nb=False, http_root_address=root_url)
        return

    def define_email_message(self):
        self._attache_files = []
        self._email_content = ""
        if self.message_type == self.MESSAGE_TYPE_EMAIL:
            if not hasattr(self, 'http_root_address'):
                raise LucteriosException(GRAVE, "No http_root_address")
            link_html = ""
            for doc in self.attachments.all():
                if self.doc_in_link:
                    if doc.sharekey is None:
                        doc.change_sharekey(False)
                        doc.save()
                    doc.set_context(self.http_root_address)
                    link_html += "<li><a href='%s'>%s</a></li>" % (doc.shared_link, doc.name)
                else:
                    self._attache_files.append((doc.name, doc.content))
            if self.doc_in_link and (link_html != ''):
                link_html = "<hr/><h3>%s</h3><ul>%s</ul>" % (_('Shared documents'), link_html)
            self._email_content = "<html><body>%s%s</body></html>" % (toHtml(self.body), link_html)
        elif self.message_type == 1:
            self._email_content = self.body.replace('{[br/]}', '\n')

    @property
    def email_content(self):
        if not hasattr(self, '_email_content'):
            self.define_email_message()
        return self._email_content

    @property
    def attach_files(self):
        if not hasattr(self, '_attache_files'):
            self.define_email_message()
        return self._attache_files

    def sendSMS(self):
        getLogger('lucterios.mailing').debug('Message.sendsms()')
        provider = AbstractProvider.get_current_instance()
        if (self.message_type == self.MESSAGE_TYPE_SMS) and (provider is not None) and provider.is_active and (self.status == self.STATUS_SENDING):
            sms_list = self.email_to_send.split("\n")
            for contact_sms in sms_list:
                contact_sms_det = contact_sms.split(':')
                if len(contact_sms_det) == 2:
                    contact_id, sms = contact_sms_det
                    try:
                        contact = AbstractContact.objects.get(id=contact_id)
                    except AbstractContact.DoesNotExist:
                        contact = None
                email_sent = EmailSent.objects.create(message=self, contact=contact, email=sms, date=timezone.now())
                email_sent.send_sms(provider)
            self.email_to_send = ""
            self.status = self.STATUS_VALIDATED
            self.save()
        return

    def sendemail(self, nb_to_send, http_root_address):
        getLogger('lucterios.mailing').debug('Message.sendemail(nb_to_send=%s, http_root_address=%s)', nb_to_send, http_root_address)
        self.http_root_address = http_root_address
        if (self.message_type == self.MESSAGE_TYPE_EMAIL) and will_mail_send() and (self.status == self.STATUS_SENDING):
            email_list = self.email_to_send.split("\n")
            for contact_email in email_list[:nb_to_send]:
                contact_email_det = contact_email.split(':')
                if len(contact_email_det) == 2:
                    contact_id, email = contact_email_det
                    try:
                        contact = AbstractContact.objects.get(id=contact_id)
                    except AbstractContact.DoesNotExist:
                        contact = None
                elif len(contact_email_det) == 3:
                    modelname, object_id, _printmodel = contact_email_det
                    model = apps.get_model(modelname)
                    item = model.objects.get(id=object_id)
                    if hasattr(item, 'contact'):
                        contact = item.contact
                    elif isinstance(item, AbstractContact):
                        contact = item
                    else:
                        contact = None
                    email = contact_email
                else:
                    continue
                email_sent = EmailSent.objects.create(message=self, contact=contact, email=email, date=timezone.now())
                email_sent.send_email(http_root_address)
            self.email_to_send = "\n".join(email_list[nb_to_send:])
            if self.email_to_send == '':
                self.status = self.STATUS_VALIDATED
            self.save()
        return

    def get_email_status(self):
        if not hasattr(self, '_email_status'):
            self._email_status = json.loads(self.email_sent)
        return self._email_status

    @property
    def date_begin(self):
        emails_sent = self.emailsent_set.order_by('date')
        if len(emails_sent) > 0:
            return get_date_formating(emails_sent[0].date)
        return '---'

    @property
    def date_end(self):
        emails_sent = self.emailsent_set.order_by('-date')
        if len(emails_sent) > 0:
            return get_date_formating(emails_sent[0].date)
        return '---'

    @property
    def nb_total(self):
        return self.emailsent_set.all().count() if self.id is not None else 0

    @property
    def nb_errors(self):
        return self.emailsent_set.filter(success=False).count()

    @property
    def nb_open(self):
        return self.emailsent_set.filter(last_open_date__isnull=False).count()

    @property
    def statistic(self):
        if self.message_type == self.MESSAGE_TYPE_EMAIL:
            return _('Send = %(send)d at %(date)s - Error = %(error)d - Open = %(open)d => %(ratio).1f %%') % {
                'send': self.nb_total,
                'date': self.date_end,
                'error': self.nb_errors,
                'open': self.nb_open,
                'ratio': (100.0 * self.nb_open) / self.nb_total
            }
        elif self.message_type == self.MESSAGE_TYPE_SMS:
            return _('Send = %(send)d at %(date)s - Error = %(error)d') % {
                'send': self.nb_total,
                'date': self.date_end,
                'error': self.nb_errors
            }
        else:
            return ""

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.body = self.body.replace('{[/h1]}{[br/]}', '{[/h1]}')
        self.body = self.body.replace('{[/h2]}{[br/]}', '{[/h2]}')
        self.body = self.body.replace('{[/h3]}{[br/]}', '{[/h3]}')
        self.body = self.body.replace('{[/h4]}{[br/]}', '{[/h4]}')
        self.body = self.body.replace('{[/h5]}{[br/]}', '{[/h5]}')
        self.body = self.body.replace('{[p]}', '')
        self.body = self.body.replace('{[/p]}{[br/]}', '{[br]}')
        self.body = self.body.replace('{[/p]}', '{[br]}')
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['-date']


class EmailSent(LucteriosModel):
    message = models.ForeignKey(Message, verbose_name=_('message'), null=False, on_delete=models.CASCADE)
    contact = models.ForeignKey('contacts.AbstractContact', verbose_name=_('contact'), null=True, on_delete=models.SET_NULL)
    email = models.CharField(_('email'), max_length=50, blank=False)
    date = models.DateTimeField(verbose_name=_('date'), null=True)
    success = models.BooleanField(verbose_name=_('success'), default=False)
    error = models.TextField(_('error'), default="")
    last_open_date = models.DateTimeField(verbose_name=_('last open date'), null=True, default=None)
    nb_open = models.IntegerField(verbose_name=_('number open'), null=False, default=0)
    sended_item = LucteriosVirtualField(verbose_name=_('sended item'), compute_from='get_sended_item')

    @classmethod
    def get_default_fields(cls):
        return ['contact', 'sended_item', 'date', 'success', 'error', 'last_open_date', 'nb_open']

    def get_send_email_objects(self):
        return [self.item]

    def get_sended_item(self):
        if len(self.email.split(':')) == 3:
            modelname, object_id, _printmodel = self.email.split(':')
            model = apps.get_model(modelname)
            return str(model.objects.get(id=object_id))
        else:
            return self.email

    def _extract_obj(self):
        if len(self.email.split(':')) == 3:
            modelname, object_id, printmodel = self.email.split(':')
            model = apps.get_model(modelname)
            self.item = model.objects.get(id=object_id)
            if hasattr(self.item, "get_pdfreport"):
                self.print_file = [self.item.get_pdfreport(int(printmodel))]
            else:
                printmodel_obj = PrintModel.objects.get(id=printmodel)
                if hasattr(self.item, "get_document_filename"):
                    pdf_name = "%s.pdf" % self.item.get_document_filename()
                else:
                    pdf_name = "%s.pdf" % remove_accent(printmodel_obj.name)
                gen = ReportingGenerator()
                gen.items = self.get_send_email_objects()
                gen.model_text = printmodel_obj.value
                pdf_file = BytesIO(gen.generate_report(None, PRINT_EXT_FILE[PRINT_PDF_FILE]))
                self.print_file = [(pdf_name, pdf_file)]
        else:
            self.print_file = None
            self.item = None

    def get_emails(self):
        if not hasattr(self, 'item'):
            self._extract_obj()
        if self.item is not None:
            cclist = self.item.get_email(False)
            return self.item.get_email(True), cclist if len(cclist) > 0 else None
        else:
            return [self.email], None

    def get_attach_files(self):
        if not hasattr(self, 'print_file'):
            self._extract_obj()
        if self.print_file is not None:
            return self.print_file
        else:
            return self.message.attach_files

    def replace_tag(self, text):
        if not hasattr(self, 'item'):
            self._extract_obj()
        contact = None
        doc_reference = ''
        if self.item is not None:
            if hasattr(self.item, 'contact'):
                contact = self.item.contact
            elif isinstance(self.item, AbstractContact):
                contact = self.item
            if hasattr(self.item, 'reference'):
                doc_reference = self.item.reference
            else:
                doc_reference = str(self.item.id)
        first_doc_name = ''
        if (first_doc_name == '') and (len(self.get_attach_files()) > 0):
            first_doc_name = self.get_attach_files()[0][0]
        if contact is None:
            contact = self.contact
        text = text.replace('#name', contact.get_final_child().get_presentation() if contact is not None else '???')
        text = text.replace('#doc', first_doc_name)
        text = text.replace('#reference', doc_reference)
        if "#footer" in text:
            footer_contain = ""
            if hasattr(self.item, 'get_email_footer'):
                footer_contain = self.item.get_email_footer()
            text = text.replace('#footer', footer_contain)
        return text

    def send_email(self, http_root_address):
        getLogger('lucterios.mailing').debug('EmailSent.send_email(http_root_address=%s)', http_root_address)
        try:
            if http_root_address != '':
                self.message.http_root_address = http_root_address
                img_html = "<img src='%s/lucterios.mailing/emailSentAddForStatistic?emailsent=%d' alt=''/>" % (http_root_address, self.id)
            else:
                img_html = ""
            body = self.replace_tag(self.message.email_content)
            h2txt = HTML2Text()
            h2txt.ignore_links = False
            body_txt = h2txt.handle(body)
            if img_html != "":
                body = body.replace('</body>', img_html + '</body>')
            email, ccemail = self.get_emails()
            getLogger('lucterios.mailing').debug('send email %s : %s' % (self.message.subject, email))
            no_send_list = send_email(split_doubled_email(email), self.replace_tag(self.message.subject), body, files=self.get_attach_files(), cclist=split_doubled_email(ccemail), withcopy=self.item is not None, body_txt=body_txt)
            if (self.item is not None) and hasattr(self.item, 'email_sended'):
                self.item.email_sended()
            self.success = True
            if len(no_send_list) > 0:
                email_list = email
                if ccemail is not None:
                    email_list.extend(ccemail)
                for email_item in split_doubled_email(email_list):
                    if email_item not in no_send_list:
                        no_send_list[email_item] = 'OK'
                self.error = str(no_send_list)
        except Exception as error:
            if getLogger('lucterios.mailing').isEnabledFor(DEBUG):
                getLogger('lucterios.mailing').exception('send_email')
            self.success = False
            self.error = str(error)
        self.save()

    def send_sms(self, provider):
        getLogger('lucterios.mailing').debug('EmailSent.send_sms()')
        try:
            body = self.replace_tag(self.message.email_content)
            getLogger('lucterios.mailing').debug('send sms %s : %s' % (self.message.subject, self.email))
            provider.send_sms(self.email, body)
            self.success = True
        except Exception as error:
            if getLogger('lucterios.mailing').isEnabledFor(DEBUG):
                getLogger('lucterios.mailing').exception('send_email')
            self.success = False
            self.error = str(error)
        self.save()

    class Meta(object):
        verbose_name = _('email sent info')
        verbose_name_plural = _('email sent info')
        default_permissions = []
        ordering = ['-last_open_date', 'contact', '-date', 'email']


def send_messaging_in_waiting(http_root_address):
    '''Mailing'''
    msg_list = Message.objects.filter(status=Message.STATUS_SENDING)
    if len(msg_list) == 0:
        LucteriosScheduler.remove(send_messaging_in_waiting)
    else:
        for msg_item in msg_list:
            if msg_item.message_type == Message.MESSAGE_TYPE_EMAIL:
                msg_item.sendemail(Params.getvalue('mailing-nb-by-batch'), http_root_address)
            elif msg_item.message_type == Message.MESSAGE_TYPE_SMS:
                msg_item.sendSMS()


@Signal.decorate('scheduler_refresh')
def add_messaging_in_scheduler(check_nb=True, http_root_address=""):
    from django.conf import settings
    if http_root_address == "":
        http_root_address = getattr(settings, 'LUCTERIOS_ROOT_URL', '')
    if not check_nb or (Message.objects.filter(status=Message.STATUS_SENDING).count() > 0):
        LucteriosScheduler.add_task(send_messaging_in_waiting, minutes=Params.getvalue('mailing-delay-batch'), http_root_address=http_root_address)


@Signal.decorate('checkparam')
def mailing_checkparam():
    Parameter.check_and_create(name='mailing-smtpserver', typeparam=0, title=_("mailing-smtpserver"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-smtpport', typeparam=1, title=_("mailing-smtpport"), args="{'Min': 0, 'Max': 99999}", value='25')

    Parameter.check_and_create(name='mailing-smtpsecurity', typeparam=4, title=_("mailing-smtpsecurity"), args="{'Enum':3}", value='0',
                               param_titles=(_("mailing-smtpsecurity.0"), _("mailing-smtpsecurity.1"), _("mailing-smtpsecurity.2")))

    Parameter.check_and_create(name='mailing-smtpuser', typeparam=0, title=_("mailing-smtpuser"), args="{'Multi': False}", value='')

    Parameter.check_and_create(name='mailing-smtppass', typeparam=5, title=_("mailing-smtppass"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-msg-connection', typeparam=0, title=_("mailing-msg-connection"), args="{'Multi': True, 'HyperText': True}",
                               value=_('''Connection confirmation to your application:{[br/]} - Login:%(login)s{[br/]} - Password:%(password)s{[br/]}'''))
    Parameter.check_and_create(name='mailing-delay-batch', typeparam=2, title=_("mailing-delay-batch"), args="{'Min': 0.1, 'Max': 120, 'Prec': 1}", value='15')
    Parameter.check_and_create(name='mailing-nb-by-batch', typeparam=1, title=_("mailing-nb-by-batch"), args="{'Min': 1, 'Max': 100}", value='10')

    Parameter.check_and_create(name='mailing-dkim-private-path', typeparam=0, title=_("mailing-dkim-private-path"), args="{'Multi': False}", value='')
    Parameter.check_and_create(name='mailing-dkim-selector', typeparam=0, title=_("mailing-dkim-selector"), args="{'Multi': False}", value='default')

    Parameter.check_and_create(name='mailing-sms-phone-parse', typeparam=0, title=_("mailing-sms-phone-parse"), args="{'Multi': False}", value='^0([67][0-9]{8})$|+33{0}')
    Parameter.check_and_create(name='mailing-sms-provider', typeparam=4, title=_("mailing-sms-option"), args="{}", value='',
                               meta='("","","lucterios.mailing.sms_functions.AbstractProvider.get_provider_list()", "", False)')
    Parameter.check_and_create(name='mailing-sms-option', typeparam=0, title=_("mailing-sms-provider"), args="{'Multi': True}", value='')

    LucteriosGroup.redefine_generic(_("# mailing (editor)"), Message.get_permission(True, True, True))
    LucteriosGroup.redefine_generic(_("# mailing (shower)"), Message.get_permission(True, False, False))


@Signal.decorate('auditlog_register')
def mailing_auditlog_register():
    auditlog.register(Message, include_fields=['status', 'date', 'subject', 'body', 'recipients', 'attachments'])
