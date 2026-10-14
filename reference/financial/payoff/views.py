# -*- coding: utf-8 -*-
'''
diacamma.payoff views package

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
from django.db.models.functions import Concat
from django.db.models import Q, Value
from django.apps.registry import apps

from lucterios.framework.xferadvance import XferAddEditor, XferListEditor, \
    XferSave, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_OK, TITLE_CANCEL, TITLE_CLOSE
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import ActionsManage, MenuManage, \
    FORMTYPE_REFRESH, CLOSE_NO, FORMTYPE_MODAL, CLOSE_YES, SELECT_SINGLE, WrapAction, SELECT_MULTI, \
    get_url_from_request
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XferContainerCustom
from lucterios.framework.xfercomponents import XferCompLabelForm, \
    XferCompEdit, XferCompImage, XferCompMemo, XferCompSelect
from lucterios.framework.error import LucteriosException, MINOR, IMPORTANT
from lucterios.framework.models import LucteriosQuerySet
from lucterios.CORE.models import PrintModel
from lucterios.CORE.xferprint import XferPrintReporting
from lucterios.framework.xferprinting import XferContainerPrint

from diacamma.payoff.models import Payoff, Supporting, BankAccount
from diacamma.accounting.models import Third


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', condition=lambda xfer, gridname='': xfer.item.can_add_pay())
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('payoff.add_payoff')
class PayoffAddModify(XferAddEditor):
    short_icon = 'mdi:mdi-cash-register'
    model = Payoff
    field_id = 'payoff'
    caption_add = _("Add payoff")
    caption_modify = _("Modify payoff")

    def fillresponse_multisave(self, supportings=(), amount=0.0,
                               mode=Payoff.MODE_CASH, payer='', reference='',
                               bank_account=BankAccount.NO_BANK, date=None, fee_bank=0.0, repartition=Payoff.REPARTITION_BYRATIO):
        if self.item.id is not None:
            self.item.delete()
        Payoff.multi_save(supportings, amount, mode, payer, reference, bank_account, date, fee_bank, repartition)

    def run_save(self, request, *args, **kwargs):
        supportings = self.getparam('supportings', ())
        kwargs['supporting'] = int(supportings[0]) if len(supportings) > 0 else 0
        if len(supportings) > 1:
            multisave = XferContainerAcknowledge()
            multisave.is_view_right = self.is_view_right
            multisave.locked = self.locked
            multisave.model = self.model
            multisave.field_id = self.field_id
            multisave.caption = self.caption
            multisave.closeaction = self.closeaction
            multisave.fillresponse = self.fillresponse_multisave
            return multisave.request_handling(request, *args, **kwargs)
        else:
            return XferAddEditor.run_save(self, request, *args, **kwargs)

    def fillresponse(self):
        delete_msg = self.item.can_delete()
        if delete_msg != '':
            raise LucteriosException(IMPORTANT, delete_msg)
        if (self.item.mode == Payoff.MODE_INTERNAL) and (self.getparam('supportings', None) is None):
            raise LucteriosException(IMPORTANT, _('Internal payoff not editable !'))
        if self.item.id is not None:
            self.items = Payoff.objects.filter(entry=self.item.entry)
            amount = 0
            supportings = []
            for item in self.items:
                supportings.append(str(item.supporting.id))
                amount += item.amount
            self.params['supportings'] = ";".join(supportings)
            self.params['amount'] = amount
        XferAddEditor.fillresponse(self)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('payoff.delete_payoff')
class PayoffDel(XferDelete):
    short_icon = 'mdi:mdi-cash-register'
    model = Payoff
    field_id = 'payoff'
    caption = _("Delete payoff")


@ActionsManage.affect_other(_('change'), short_icon='mdi:mdi-pencil-outline')
@MenuManage.describ('')
class SupportingThird(XferListEditor):
    short_icon = "mdi:mdi-account-cash-outline"
    model = Supporting
    field_id = 'supporting'
    caption = _("Select third")

    def __init__(self, **kwargs):
        self.model = Third
        self.field_id = 'third'
        XferListEditor.__init__(self, **kwargs)
        self.action_list = []
        self.code_mask = ''

    def get_items_from_filter(self):
        items = self.model.objects.annotate(completename=Concat('contact__individual__lastname', Value(' '), 'contact__individual__firstname')).filter(self.filter)
        sort_third = self.getparam('GRID_ORDER%third', '')
        sort_thirdbis = self.getparam('GRID_ORDER%third+', '')
        self.params['GRID_ORDER%third'] = ""
        if sort_third != '':
            if sort_thirdbis.startswith('-'):
                sort_thirdbis = "+"
            else:
                sort_thirdbis = "-"
            self.params['GRID_ORDER%third+'] = sort_thirdbis
        items = sorted(items, key=lambda t: str(t).lower(), reverse=sort_thirdbis.startswith('-'))
        if self.getparam('show_filter', 0) == 2:
            items = [item for item in items if abs(item.get_total()) > 0.0001]
        return LucteriosQuerySet(model=Third, initial=items)

    def fillresponse_header(self):
        if 'status_filter' in self.params:
            del self.params['status_filter']
        contact_filter = self.getparam('filter', '')
        comp = XferCompEdit('filter')
        comp.set_value(contact_filter)
        comp.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        comp.set_location(0, 2, 2)
        comp.is_default = True
        comp.description = _('Filtrer by contact')
        self.add_component(comp)
        self.filter = Q(status=0)
        if self.code_mask != '':
            self.filter &= Q(accountthird__code__regex=self.code_mask)
        if contact_filter != "":
            q_legalentity = Q(contact__legalentity__name__icontains=contact_filter)
            q_individual = (Q(contact__individual__firstname__icontains=contact_filter) | Q(contact__individual__lastname__icontains=contact_filter))
            self.filter &= (q_legalentity | q_individual)

    def fillresponse(self, code_mask=''):
        self.code_mask = code_mask
        XferListEditor.fillresponse(self)
        grid = self.get_components(self.field_id)
        for action_idx in range(0, len(grid.actions)):
            if grid.actions[action_idx][0].short_icon.endswith('mdi:mdi-pencil-plus'):
                params = grid.actions[action_idx][4]
                if params is None:
                    params = {}
                params['REDIRECT_AFTER_SAVE'] = SupportingThirdValid.url_text
                grid.actions[action_idx] = (grid.actions[action_idx][0], grid.actions[action_idx][1], CLOSE_YES, grid.actions[action_idx][3], params)
        grid.add_action(self.request, SupportingThirdValid.get_action(_('select'), short_icon='mdi:mdi-check'),
                        modal=FORMTYPE_MODAL, close=CLOSE_YES, unique=SELECT_SINGLE, pos_act=0)
        self.actions = []
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@MenuManage.describ('')
class SupportingThirdValid(XferSave):
    redirect_to_show = False
    short_icon = "mdi:mdi-account-cash-outline"
    model = Supporting
    field_id = 'supporting'
    caption = _("Select third")


def can_send_email(xfer):
    from django.utils.module_loading import import_module
    if apps.is_installed("lucterios.mailing"):
        fct_mailing_mod = import_module('lucterios.mailing.email_functions')
        return fct_mailing_mod.will_mail_send()
    else:
        return False


class SupportingPrint(XferPrintReporting):

    def __init__(self):
        XferPrintReporting.__init__(self)
        self.default_model = self.params['MODEL']
        del self.params['MODEL']

    def _get_persistent_pdfreport(self, recreate):
        if len(self.items) == 1:
            doc = self.item.get_final_child().get_saved_pdfreport(recreate)
            if doc is not None:
                return doc.content.read()
        else:
            docs = []
            for item in self.items:
                doc = item.get_final_child().get_saved_pdfreport(recreate)
                if doc is not None:
                    docs.append((doc.name, doc.content))
            if len(docs) > 0:
                return docs
        return None

    def get_persistent_renew(self):
        return self.item.get_final_child().get_saved_renew()

    def fillresponse(self):
        if (self.item is None) and (len(self.items) > 0):
            self.item = self.items[0]
        self.params['MODEL'] = self.getparam('MODEL', self.item.get_default_print_model() if self.item is not None else self.default_model)
        XferPrintReporting.fillresponse(self)


@ActionsManage.affect_show(_("Send"), short_icon="mdi:mdi-email-outline", condition=can_send_email)
@MenuManage.describ('')
class PayableEmail(XferContainerAcknowledge):
    caption = _("Send by email")
    short_icon = "mdi:mdi-account-cash-outline"
    model = Supporting
    field_id = 'supporting'

    def fillresponse_send1message(self, subject, message, model):
        html_message = "<html>"
        html_message += message.replace('{[newline]}', '<br/>\n').replace('{[', '<').replace(']}', '>')
        html_message += self.item.get_email_footer(self.request)
        html_message += "</html>"
        self.item.set_context(self)
        self.item.send_email(subject, html_message, model)

    def fillresponse_sendmultimessages(self, subject, message, model):
        from lucterios.mailing.models import Message
        model_obj = self.item.__class__
        email_msg = Message.objects.create(subject=subject, body=message + "#footer", email_to_send="%s:0:%s" % (model_obj.get_long_name(), model))
        email_msg.add_recipient(model_obj.get_long_name(), 'id||8||%s' % ';'.join([str(item.id) for item in self.items]))
        email_msg.save()
        email_msg.valid()
        email_msg.set_context(self)
        email_msg.sending()

    def get_persistent_renew(self):
        for item in self.items:
            if not item.get_saved_renew():
                return False
        return True

    def fillresponse(self, item_name='', subject='', message='', model=0, modelname=""):
        def replace_tag(contact, text):
            text = text.replace('#name', contact.get_final_child().get_presentation() if contact is not None else '???')
            text = text.replace('#doc', str(self.item.get_docname()))
            text = text.replace('#reference', str(self.item.reference))
            return text

        if item_name != '':
            if modelname != '':
                self.model = apps.get_model(modelname)
            self.items = self.model.objects.filter(id__in=self.getparam(item_name, ()))
        self.items = [item.get_final_child() for item in self.items if item.can_send_email()]
        if len(self.items) == 0:
            raise LucteriosException(MINOR, _('No send item !'))
        if len(self.items) > 0:
            self.item = self.items[0]
            self.model = self.item.__class__
        if self.getparam("OK") is None:
            items_with_doc = [item for item in self.items if item.get_saved_pdfreport(False) is not None]
            dlg = self.create_custom()
            icon = XferCompImage('img')
            icon.set_location(0, 0, 1, 6)
            icon.set_value(self.short_icon, '#')
            dlg.add_component(icon)

            subject = self.item.get_email_subject()
            message = self.item.get_email_message()
            if len(self.items) > 1:
                edt = XferCompLabelForm('nb_item')
                edt.set_value(len(self.items))
                edt.set_location(1, 1)
                edt.description = _('nb of sending')
                dlg.add_component(edt)
            else:
                contact = self.item.contact.get_final_child()
                subject = replace_tag(contact, subject)
                message = replace_tag(contact, message)
            edt = XferCompEdit('subject')
            edt.set_value(subject)
            edt.set_location(1, 2)
            edt.description = _('subject')
            dlg.add_component(edt)
            memo = XferCompMemo('message')
            memo.description = _('message')
            memo.set_value(message)
            memo.with_hypertext = True
            memo.set_height(150)
            memo.set_location(1, 3)
            dlg.add_component(memo)
            if len(items_with_doc) == len(self.items):
                report_mode_list = [(XferContainerPrint.PRINT_PERSITENT_CODE, _('Get saved report')),
                                    (XferContainerPrint.PRINT_REGENERATE_CODE, XferContainerPrint.PRINT_REGENERATE_MSG)]
                if self.get_persistent_renew():
                    report_mode_list.append((XferContainerPrint.PRINT_RENEW_CODE, XferContainerPrint.PRINT_RENEW_MSG))
                presitent_report_mode = XferCompSelect('PRINT_PERSITENT_MODE')
                presitent_report_mode.set_location(1, 4)
                presitent_report_mode.set_select(report_mode_list)
                presitent_report_mode.set_value(XferContainerPrint.PRINT_PERSITENT_CODE)
                presitent_report_mode.java_script = """
var persitent_mode=current.getValue();
parent.get('model').setEnabled(persitent_mode==%d);
""" % XferContainerPrint.PRINT_REGENERATE_CODE
                dlg.add_component(presitent_report_mode)
            elif len(self.items) > 1:
                sep = XferCompLabelForm('print_sep')
                sep.set_value_center(XferContainerPrint.PRINT_WARNING_SAVING_MSG)
                sep.set_location(1, 5)
                dlg.add_component(sep)
            selectors = PrintModel.get_print_selector(PrintModel.KIND_REPORT, self.model)[0]
            sel = XferCompSelect('model')
            sel.set_select(selectors[2])
            sel.set_location(1, 6)
            sel.set_value(self.item.get_default_print_model())
            sel.description = selectors[1]
            dlg.add_component(sel)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), params={"OK": "YES"})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            persitent_mode = self.getparam("PRINT_PERSITENT_MODE", XferContainerPrint.PRINT_REGENERATE_CODE)
            if (persitent_mode != XferContainerPrint.PRINT_REGENERATE_CODE):
                model = 0
            if (persitent_mode == XferContainerPrint.PRINT_RENEW_CODE):
                for item in self.items:
                    item.get_saved_pdfreport(True)
            if len(self.items) == 1:
                self.fillresponse_send1message(subject, message, model)
            else:
                self.fillresponse_sendmultimessages(subject, message, model)


def add_payment_methods(xfer, supporting, payments):
    if not supporting.payoff_have_payment() or (len(payments) == 0):
        return
    max_row = xfer.get_max_row() + 1
    lbl = XferCompLabelForm('lb_sep')
    lbl.set_value("{[hr/]}")
    lbl.set_location(1, max_row, 4)
    xfer.add_component(lbl)
    lbl = XferCompLabelForm('lb_title')
    lbl.set_value_as_infocenter(_("Payement methods"))
    lbl.set_location(1, max_row + 1, 4)
    xfer.add_component(lbl)
    for paymeth in payments:
        max_row = xfer.get_max_row() + 1
        lbl = XferCompLabelForm('paymeth_%d' % paymeth.id)
        lbl.description = paymeth.paytypetext
        lbl.set_value(paymeth.show_pay(get_url_from_request(xfer.request), xfer.language, supporting))
        lbl.set_location(1, max_row, 3)
        xfer.add_component(lbl)
        lbl = XferCompLabelForm('sep_paymeth_%d' % paymeth.id)
        lbl.set_value("{[br/]}")
        lbl.set_location(2, max_row + 1)
        xfer.add_component(lbl)


@ActionsManage.affect_show(_("Payment"), short_icon="mdi:mdi-account-cash-outline", condition=lambda xfer: xfer.item.payoff_have_payment() and (len(xfer.item.get_payment_method()) > 0))
@MenuManage.describ('')
class PayableShow(XferContainerCustom):
    caption = _("Payment")
    short_icon = "mdi:mdi-account-cash-outline"
    model = Supporting
    field_id = 'supporting'
    readonly = True
    methods_allowed = ('GET', )

    def fillresponse(self, item_name=''):
        if item_name != '':
            self.item = Supporting.objects.get(id=self.getparam(item_name, 0))
        self.item = self.item.get_final_child()
        payments = self.item.get_payment_method()
        if not self.item.payoff_have_payment() or (len(payments) == 0):
            raise LucteriosException(MINOR, _('No payment for this document.'))
        max_row = self.get_max_row() + 1
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 6)
        self.add_component(img)
        self.fill_from_model(1, max_row, True, self.item.get_payment_fields())
        add_payment_methods(self, self.item, payments)
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))
