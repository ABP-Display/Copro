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
from os import unlink
from os.path import exists

from django.utils.translation import gettext_lazy as _

from lucterios.framework.filetools import save_from_base64, get_user_path, open_image_resize, readimage_to_base64
from lucterios.framework.xfercomponents import XferCompEdit, XferCompFloat, XferCompCheck, XferCompSelect, \
    XferCompMemo, XferCompUpLoad, XferCompImage, XferCompButton, XferCompLinkLabel, \
    XferCompDate
from lucterios.framework.tools import FORMTYPE_REFRESH, FORMTYPE_MODAL, CLOSE_NO, CLOSE_YES, get_icon_path, WrapAction
from lucterios.framework.tools import ActionsManage
from lucterios.framework.editors import LucteriosEditor

from lucterios.contacts.models import PostalCode, CustomField
from lucterios.CORE.parameters import Params
from lucterios.framework import signal_and_lock
from lucterios.CORE.views import ObjectPromote
from lucterios.framework.xferadvance import TITLE_MODIFY, TITLE_ADD


class CustomFieldEditor(LucteriosEditor):

    def _edit_add_args(self, xfer, obj_kind):
        args = self.item.get_args()
        arg = XferCompCheck('args_multi')
        arg.set_value(args['multi'])
        arg.set_location(obj_kind.col, obj_kind.row + 1, obj_kind.colspan, 1)
        arg.description = _('multi-line')
        xfer.add_component(arg)
        arg = XferCompFloat('args_min', -10000, 10000, 0)
        arg.set_value(args['min'])
        arg.set_location(obj_kind.col, obj_kind.row + 2, obj_kind.colspan, 1)
        arg.description = _('min')
        xfer.add_component(arg)
        arg = XferCompFloat('args_max', -10000, 10000, 0)
        arg.set_value(args['max'])
        arg.set_location(obj_kind.col, obj_kind.row + 3, obj_kind.colspan, 1)
        arg.description = _('max')
        xfer.add_component(arg)
        arg = XferCompFloat('args_prec', 0, 10, 0)
        arg.set_value(args['prec'])
        arg.set_location(obj_kind.col, obj_kind.row + 4, obj_kind.colspan, 1)
        arg.description = _('precision')
        xfer.add_component(arg)
        arg = XferCompEdit('args_list')
        arg.set_value(','.join(args['list']))
        arg.set_location(obj_kind.col, obj_kind.row + 5, obj_kind.colspan, 1)
        arg.description = _('list')
        xfer.add_component(arg)
        arg = XferCompCheck('args_today')
        arg.set_value(args['today'])
        arg.set_location(obj_kind.col, obj_kind.row + 6, obj_kind.colspan, 1)
        arg.description = _('today by default')
        xfer.add_component(arg)

    def _get_basic_model(self, xfer):
        from django.apps import apps
        return apps.get_model(xfer.getparam('basic_model', 'contacts.AbstractContact'))

    def edit(self, xfer):
        obj_model = xfer.get_components('modelname')
        obj_kind = xfer.get_components('kind')
        xfer.tab = obj_model.tab
        sel_models = self._get_basic_model(xfer).get_select_contact_type()
        model_current = obj_model.value
        xfer.remove_component('modelname')
        model_select = XferCompSelect('modelname')
        model_select.description = obj_model.description
        model_select.set_value(model_current)
        model_select.set_select(sel_models)
        model_select.set_location(obj_model.col, obj_model.row, obj_model.colspan, obj_model.rowspan)
        xfer.add_component(model_select)
        if len(sel_models) == 1:
            xfer.params['modelname'] = sel_models[0][0]
            model_select.set_value(xfer.params['modelname'])
            xfer.change_to_readonly('modelname')
        if xfer.getparam('custom_type') is not None:
            xfer.remove_component('kind')
            xfer.params['kind'] = xfer.getparam('custom_type')
        else:
            self._edit_add_args(xfer, obj_kind)
            obj_kind.java_script = """
var type=current.getValue();
parent.get('args_multi').setVisible(type==0);
parent.get('args_min').setVisible(type==1 || type==2);
parent.get('args_max').setVisible(type==1 || type==2);
parent.get('args_prec').setVisible(type==2);
parent.get('args_list').setVisible(type==4);
parent.get('args_today').setVisible(type==5);
"""

    def saving(self, xfer):
        args = {}
        for arg_name in ['min', 'max', 'prec', 'list', 'multi', 'today']:
            args_val = xfer.getparam('args_' + arg_name)
            if args_val is not None:
                if arg_name == 'list':
                    args[arg_name] = list(args_val.split(","))
                elif (arg_name == 'multi') or (arg_name == 'today'):
                    args[arg_name] = (args_val != 'False') and (args_val != '0') and (args_val != '') and (args_val != 'n')
                else:
                    args[arg_name] = float(args_val)
        self.item.args = str(args)
        LucteriosEditor.saving(self, xfer)
        self.item.save()
        self.item.check_associated()

    def get_comp(self, value):
        comp = None
        args = self.item.get_args()
        if self.item.kind == CustomField.KIND_STRING:
            if args['multi']:
                comp = XferCompMemo(self.item.get_fieldname())
            else:
                comp = XferCompEdit(self.item.get_fieldname())
            comp.set_value(value)
        elif (self.item.kind == CustomField.KIND_INTEGER) or (self.item.kind == CustomField.KIND_REAL):
            comp = XferCompFloat(
                self.item.get_fieldname(), args['min'], args['max'], args['prec'])
            comp.set_value(value)
        elif self.item.kind == CustomField.KIND_BOOLEAN:
            comp = XferCompCheck(self.item.get_fieldname())
            comp.set_value(value)
        elif self.item.kind == CustomField.KIND_SELECT:
            val_selected = value
            try:
                select_id = int(value)
            except ValueError:
                select_id = 0
            select_list = []
            for sel_item in args['list']:
                if sel_item == val_selected:
                    select_id = len(select_list)
                select_list.append((len(select_list), sel_item))
            select_list.sort(key=lambda item: item[1].lower())
            comp = XferCompSelect(self.item.get_fieldname())
            comp.set_select(select_list)
            comp.set_value(select_id)
        elif self.item.kind == CustomField.KIND_DATE:
            comp = XferCompDate(self.item.get_fieldname())
            comp.set_value(value)
            comp.set_needed(True)
        return comp


class AbstractEditorCustomizeWithLogo(LucteriosEditor):

    image_prefix = ""
    component_move = ""

    def edit(self, xfer):
        obj_cmt = xfer.get_components('comment')
        xfer.tab = obj_cmt.tab
        CustomField.edit_fields(xfer, obj_cmt.col)
        row = xfer.get_max_row()
        xfer.move_components('comment', 0, row - obj_cmt.row + 1)
        row = xfer.get_max_row()
        upload = XferCompUpLoad('uploadlogo')
        upload.set_value('')
        upload.description = _('image')
        upload.add_filter('.jpg')
        upload.add_filter('.gif')
        upload.add_filter('.png')
        upload.add_filter('.bmp')
        upload.set_location(obj_cmt.col, row + 1, obj_cmt.colspan, 1)
        xfer.add_component(upload)
        return

    def show(self, xfer):
        LucteriosEditor.show(self, xfer)
        obj_comp = xfer.get_components(self.component_move)
        xfer.tab = obj_comp.tab
        xfer.move(obj_comp.tab, 1, 0)
        img_path = get_user_path("contacts", "%s_%s.jpg" % (self.image_prefix, self.item.id))
        img = XferCompImage('logoimg')
        if exists(img_path):
            img.type = 'jpg'
            img.set_value(readimage_to_base64(img_path))
        else:
            img.set_value(get_icon_path("lucterios.contacts/images/NoImage.png"))
        img.set_location(obj_comp.col - 1, obj_comp.row, 1, 6)
        xfer.add_component(img)

    def saving(self, xfer):
        uploadlogo = xfer.getparam('uploadlogo')
        if uploadlogo is not None:
            tmp_file = save_from_base64(uploadlogo)
            with open(tmp_file, "rb") as image_tmp:
                image = open_image_resize(image_tmp, 100, 100)
                image = image.convert("RGB")
                img_path = get_user_path("contacts", "%s_%s.jpg" % (self.image_prefix, self.item.id))
                with open(img_path, "wb") as image_file:
                    image.save(image_file, 'JPEG', quality=90)
            unlink(tmp_file)
        LucteriosEditor.saving(self, xfer)
        self.item.set_custom_values(xfer.params)


class AbstractContactEditor(AbstractEditorCustomizeWithLogo):

    image_prefix = "Image"
    component_move = 'address'

    def _change_city_select(self, xfer, list_postalcode, obj_city):

        obj_country = xfer.get_components('country')
        city_current = obj_city.value
        city_list = {}
        obj_country.value = ""
        for item_postalcode in list_postalcode:
            city_list[item_postalcode.city] = item_postalcode.city
            if item_postalcode.city == city_current:
                obj_country.value = item_postalcode.country
        if obj_country.value == "":
            obj_country.value = list_postalcode[0].country
            city_current = list_postalcode[0].city
        xfer.remove_component('city')
        xfer.tab = obj_city.tab
        city_select = XferCompSelect('city')
        city_select.set_value(city_current)
        city_select.set_select(city_list)
        city_select.set_location(obj_city.col, obj_city.row, obj_city.colspan, obj_city.rowspan)
        city_select.description = obj_city.description
        city_select.set_action(xfer.request, xfer.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        xfer.add_component(city_select)

    def edit(self, xfer):
        obj_pstcd = xfer.get_components('postal_code')
        obj_pstcd.set_action(xfer.request, xfer.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        obj_city = xfer.get_components('city')
        postalcode_current = obj_pstcd.value
        list_postalcode = PostalCode.objects.filter(
            postal_code=postalcode_current)
        if len(list_postalcode) > 0:
            self._change_city_select(xfer, list_postalcode, obj_city)
        AbstractEditorCustomizeWithLogo.edit(self, xfer)
        return

    def show(self, xfer):
        AbstractEditorCustomizeWithLogo.show(self, xfer)
        obj_addr = xfer.get_components(self.component_move)
        if WrapAction.is_permission(xfer.request, 'contacts.add_abstractcontact'):
            if (len(self.item.__class__.get_select_contact_type(False)) > 0):
                btn = XferCompButton('btn_promote')
                btn.set_location(obj_addr.col + 1, xfer.get_max_row() + 1, 4)
                btn.set_action(xfer.request, ObjectPromote.get_action(_('Promote'), short_icon='mdi:mdi-tune'), modal=FORMTYPE_MODAL,
                               close=CLOSE_YES, params={'modelname': xfer.model.get_long_name(), 'field_id': xfer.field_id})
                xfer.add_component(btn)
        signal_and_lock.Signal.call_signal("show_contact", self.item, xfer)

    def add_email_selector(self, xfer, col, row, colspan):
        contacts_list = xfer.items.exclude(email__isnull=True).exclude(email__exact='')
        if contacts_list.count() < 100:
            mailto_type = Params.getvalue("contacts-mailtoconfig")
            email_list = []
            for item in contacts_list:
                email_list.append(str(item.email))
            if len(email_list) > 0:
                link = XferCompLinkLabel('emailAll')
                link.set_value_center(_('Write to all'))
                if mailto_type == 1:  # CC
                    mailto_prefix = 'mailto:?cc='
                elif mailto_type == 2:  # BCC
                    mailto_prefix = 'mailto:?bcc='
                else:  # TO
                    mailto_prefix = 'mailto:'
                link.set_link(mailto_prefix + ','.join(email_list))
                link.set_location(col, row, colspan)
                xfer.add_component(link)


class LegalEntityEditor(AbstractContactEditor):

    def edit(self, xfer):
        if self.item.id == 1:
            xfer.remove_component('structure_type')
        AbstractContactEditor.edit(self, xfer)
        obj_user = xfer.get_components('vat_identification')
        obj_user.mask = r'(^$|[A-Z]{2}[0-9A-Za-z\+\*\.]{2,12})'

    def show(self, xfer):
        if self.item.id == 1:
            xfer.remove_component('structure_type')
        AbstractContactEditor.show(self, xfer)


class IndividualEditor(AbstractContactEditor):

    def show(self, xfer):
        AbstractContactEditor.show(self, xfer)
        obj_user = xfer.get_components('user')
        obj_user.colspan = 2
        xfer.tab = obj_user.tab
        btn = XferCompButton('userbtn')
        btn.is_mini = True
        btn.set_location(obj_user.col + 2, obj_user.row, 1, 1)
        if self.item.user is None:
            act = ActionsManage.get_action_url('CORE.LucteriosUser', 'UserAdd', xfer)
            act.set_value(TITLE_ADD, 'mdi:mdi-pencil-plus-outline')
            btn.set_action(xfer.request, act, modal=FORMTYPE_MODAL, close=CLOSE_NO)
            xfer.add_component(btn)
        else:
            if not self.item.user.is_active:
                obj_user.set_color('red')
            act = ActionsManage.get_action_url('CORE.LucteriosUser', 'Edit', xfer)
            act.set_value(TITLE_MODIFY, 'mdi:mdi-pencil-outline')
            btn.set_action(xfer.request, act, modal=FORMTYPE_MODAL, close=CLOSE_NO,
                           params={'user_actif': str(self.item.user.id), 'IDENT_READ': 'YES'})
            xfer.add_component(btn)
            btn = XferCompButton('userbtnsupp')
            btn.is_mini = True
            btn.set_location(obj_user.col + 3, obj_user.row, 1, 1)
            btn.set_action(xfer.request, ActionsManage.get_action_url('contacts.Individual', 'UserRemove', xfer), modal=FORMTYPE_MODAL, close=CLOSE_NO)
            xfer.add_component(btn)

    def saving(self, xfer):
        from django.conf import settings
        AbstractContactEditor.saving(self, xfer)
        if (self.item.user is not None) and not settings.USER_READONLY:
            self.item.user.first_name = self.item.firstname
            self.item.user.last_name = self.item.lastname
            self.item.user.email = self.item.email.split(';')[0]
            self.item.user.save()
            if settings.ASK_LOGIN_EMAIL and self.item.user.is_email_already_exists:
                self.item.is_active = False
                self.item.user.save()


class ResponsabilityEditor(LucteriosEditor):

    def edit(self, xfer):
        xfer.change_select_to_label('legal_entity')
        xfer.change_select_to_label('individual')


class PossessionEditor(AbstractEditorCustomizeWithLogo):

    image_prefix = "Possession"
    component_move = 'category_possession'

    def show(self, xfer):
        AbstractEditorCustomizeWithLogo.show(self, xfer)
        if xfer.getparam('mng_owner', True):
            obj_owner = xfer.get_components('owner')
            xfer.tab = obj_owner.tab
            btn = XferCompButton('change_owner')
            btn.set_is_mini(True)
            btn.set_location(obj_owner.col + obj_owner.colspan, obj_owner.row)
            btn.set_action(xfer.request, ActionsManage.get_action_url('contacts.Possession', 'Owner', xfer), modal=FORMTYPE_MODAL, close=CLOSE_NO)
            xfer.add_component(btn)
            if self.item.owner is not None:
                owner_up = self.item.owner.get_final_child()
                btn = XferCompButton('show_owner')
                btn.set_is_mini(True)
                btn.set_location(obj_owner.col + obj_owner.colspan + 1, obj_owner.row)
                btn.set_action(xfer.request, ActionsManage.get_action_url(owner_up.get_long_name(), 'Show', xfer),
                               modal=FORMTYPE_MODAL, close=CLOSE_NO, params={owner_up.__class__.__name__.lower(): self.item.owner.id})
                xfer.add_component(btn)
