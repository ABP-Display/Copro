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
from os.path import exists, join, dirname
from datetime import datetime
from unicodedata import normalize, category
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db.models.aggregates import Max
from django.db import models

from lucterios.framework.models import LucteriosModel
from lucterios.framework.model_fields import PrintFieldsPlugIn, get_value_if_choices, LucteriosVirtualField
from lucterios.framework.filetools import get_user_path, readimage_to_base64
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.tools import get_format_value
from lucterios.framework.auditlog import auditlog
from lucterios.CORE.models import Parameter, LucteriosGroup, LucteriosUser
from lucterios.mailing.email_functions import split_doubled_email


class CustomField(LucteriosModel):
    KIND_STRING = 0
    KIND_INTEGER = 1
    KIND_REAL = 2
    KIND_BOOLEAN = 3
    KIND_SELECT = 4
    KIND_DATE = 5

    PREFIX_CUSTOM = "custom_"

    modelname = models.CharField(_('model'), max_length=100)
    name = models.CharField(_('name'), max_length=200, unique=False)
    kind = models.IntegerField(_('kind'), choices=((KIND_STRING, _('String')),
                                                   (KIND_INTEGER, _('Integer')),
                                                   (KIND_REAL, _('Real')),
                                                   (KIND_BOOLEAN, _('Boolean')),
                                                   (KIND_SELECT, _('Select')),
                                                   (KIND_DATE, _('Date'))))
    args = models.TextField(_('arguments'), default="{}")
    model_title = LucteriosVirtualField(verbose_name=_('model'), compute_from='get_model_title')
    kind_txt = LucteriosVirtualField(verbose_name=_('kind'), compute_from='get_kind_txt')
    order_key = models.IntegerField(verbose_name=_('order key'), null=True, default=None)

    def __str__(self):
        return self.name

    @classmethod
    def get_show_fields(cls):
        return ['modelname', 'name', 'kind']

    @classmethod
    def get_edit_fields(cls):
        return ['modelname', 'name', 'kind']

    @classmethod
    def get_default_fields(cls):
        return ['name', 'model_title', 'kind_txt']

    def model_associated(self):
        from django.apps import apps
        return apps.get_model(self.modelname)

    def get_fieldname(self):
        return self.PREFIX_CUSTOM + "%d" % self.id

    def get_model_title(self):
        return str(self.model_associated()._meta.verbose_name)

    def get_kind_txt(self):
        dep_field = self.get_field_by_name('kind')
        args = self.get_args()
        params_txt = ""
        if self.kind == self.KIND_STRING:
            if args['multi']:
                params_txt = "(%s)" % _('multi-line')
        elif self.kind == self.KIND_INTEGER:
            params_txt = "[%d;%d]" % (int(args['min']), int(args['max']))
        elif self.kind == self.KIND_REAL:
            prec = ".%df" % int(args['prec'])
            floatformat = "[%" + prec + ";%" + prec + "]"
            params_txt = floatformat % (float(args['min']), float(args['max']))
        elif self.kind == self.KIND_SELECT:
            params_txt = "(%s)" % ",".join(args['list'])
        elif self.kind == self.KIND_DATE:
            if args['today']:
                params_txt = "(%s)" % _('today by default')
        value = "%s %s" % (get_value_if_choices(self.kind, dep_field), params_txt)
        return value.strip()

    def get_args(self):
        default_args = {'min': 0, 'max': 0, 'prec': 0, 'list': [], 'multi': False, 'today': False}
        try:
            args = eval(self.args)
        except Exception:
            args = {}
        for name, val in default_args.items():
            if name not in args.keys():
                args[name] = val
        args['list'] = list(args['list'])
        return args

    def get_field(self):
        from django.db.models.fields import IntegerField, DecimalField, BooleanField, TextField, DateField
        from django.core.validators import MaxValueValidator, MinValueValidator
        args = self.get_args()
        if self.kind == self.KIND_STRING:
            dbfield = TextField(self.name)
        if self.kind == self.KIND_INTEGER:
            dbfield = IntegerField(self.name, validators=[MinValueValidator(float(args['min'])), MaxValueValidator(float(args['max']))])
        if self.kind == self.KIND_REAL:
            dbfield = DecimalField(self.name, decimal_places=int(args['prec']), validators=[MinValueValidator(float(args['min'])), MaxValueValidator(float(args['max']))])
        if self.kind == self.KIND_BOOLEAN:
            dbfield = BooleanField(self.name)
        if self.kind == self.KIND_SELECT:
            choices = []
            for item in args['list']:
                choices.append((len(choices), item))
            choices.sort(key=lambda item: item[1].lower())
            dbfield = IntegerField(self.name, choices=tuple(choices))
        if self.kind == self.KIND_DATE:
            dbfield = DateField(self.name)
        return dbfield

    @classmethod
    def get_filter(cls, model):
        model_list = []
        for sub_class in model.get_select_contact_type():
            model_list.append(sub_class[0])
        return cls.objects.filter(modelname__in=model_list)

    @classmethod
    def get_fields(cls, model):
        fields = []
        import inspect
        model_list = []
        for sub_class in inspect.getmro(model):
            if hasattr(sub_class, "get_long_name"):
                model_list.append(sub_class.get_long_name())
        for cf_model in cls.objects.filter(modelname__in=model_list):
            fields.append((cf_model.get_fieldname(), cf_model))
        return fields

    @classmethod
    def edit_fields(cls, xfer, init_col, nb_col=2):
        col = init_col
        col_offset = 0
        colspan = 1
        row = xfer.get_max_row() + 5
        for cf_name, cf_model in cls.get_fields(xfer.item.__class__):
            comp = cf_model.editor.get_comp(getattr(xfer.item, cf_name))
            comp.set_location(col + col_offset, row, colspan, 1)
            comp.description = cf_model.name
            xfer.add_component(comp)
            col_offset += 1
            if col_offset == nb_col:
                col_offset = 0
                colspan = 1
                row += 1
            else:
                colspan = 2

    def convert_data(self, value):
        data = None
        if self.kind == CustomField.KIND_STRING:
            data = str(value)
        else:
            data = value
        if data == '':
            data = '0'
        if self.kind == CustomField.KIND_INTEGER:
            data = int(data)
        if self.kind == CustomField.KIND_REAL:
            data = float(data)
        if self.kind == CustomField.KIND_BOOLEAN:
            data = (data != 'False') and (data != '0') and (data != '') and (data != 'n')
        if self.kind == CustomField.KIND_SELECT:
            data = int(data)
        if self.kind == CustomField.KIND_DATE:
            try:
                data = datetime.strptime(data, "%Y-%m-%d").date().isoformat()
            except (TypeError, ValueError):
                if self.get_args()['today']:
                    data = datetime.today().date().isoformat()
                else:
                    data = datetime.strptime("1900-01-01", "%Y-%m-%d").date().isoformat()
        dep_field = CustomizeObject.get_virtualfield(self.get_fieldname())
        return get_format_value(dep_field, data)

    def up_order(self):
        prec_custom = CustomField.objects.filter(order_key__lt=self.order_key).order_by('-order_key').first()
        if prec_custom is not None:
            order_key = prec_custom.order_key
            prec_custom.order_key = self.order_key
            self.order_key = order_key
            prec_custom.save()
            self.save()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.order_key is None:
            val = CustomField.objects.all().aggregate(Max('order_key'))
            if val['order_key__max'] is None:
                self.order_key = 1
            else:
                self.order_key = val['order_key__max'] + 1
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def check_associated(self):
        sub_model_class = self.model_associated()
        customize_field_class = sub_model_class.CustomFieldClass
        customize_fieldname = "%s__field" % customize_field_class.__name__.lower()
        fieldname = self.get_fieldname()
        for sub_model_item in sub_model_class.objects.exclude(**{customize_fieldname: self}):
            sub_model_item.set_custom_values({fieldname: getattr(sub_model_item, fieldname)})

    class Meta(object):
        verbose_name = _('custom field')
        verbose_name_plural = _('custom fields')
        default_permissions = []
        ordering = ['order_key']


class CustomizeObject(object):

    CustomFieldClass = None
    FieldName = ''

    @classmethod
    def get_fields_to_show(cls):
        fields_desc = []
        cust_fields = CustomField.get_fields(cls)
        if len(cust_fields) > 0:
            cust_item = []
            for cf_name, _model in cust_fields:
                cust_item.append(cf_name)
                if len(cust_item) == 2:
                    fields_desc.append(tuple(cust_item))
                    cust_item = []
            if len(cust_item) != 0:
                fields_desc.append(tuple(cust_item))
        return fields_desc

    def _convert_model_for_attr(self, cf_model, ccf_model):
        return self._convert_value_for_attr(cf_model, ccf_model.value)

    def _convert_value_for_attr(self, cf_model, ccf_value, args_list=[]):
        if ccf_value == '':
            ccf_value = '0'
        if cf_model.kind == CustomField.KIND_INTEGER:
            ccf_value = int(ccf_value)
        elif cf_model.kind == CustomField.KIND_REAL:
            ccf_value = float(ccf_value)
        elif cf_model.kind == CustomField.KIND_BOOLEAN:
            ccf_value = str(ccf_value) != 'False' and str(ccf_value) != '0' and ccf_value != '' and ccf_value != 'n'
        elif cf_model.kind == CustomField.KIND_SELECT:
            if args_list.count(ccf_value) > 0:
                ccf_value = args_list.index(ccf_value)
            else:
                ccf_value = int(ccf_value)
        elif cf_model.kind == CustomField.KIND_DATE:
            try:
                ccf_value = datetime.strptime(ccf_value, "%Y-%m-%d").date().isoformat()
            except (TypeError, ValueError):
                if cf_model.get_args()['today']:
                    ccf_value = datetime.today().date().isoformat()
                else:
                    ccf_value = datetime.strptime("1900-01-01", "%Y-%m-%d").date().isoformat()
        return ccf_value

    def set_custom_values(self, params):
        for cf_name, cf_model in CustomField.get_fields(self.__class__):
            if cf_name in params.keys():
                cf_value = params[cf_name]
                cf_id = int(cf_name[len(CustomField.PREFIX_CUSTOM):])
                cf_model = CustomField.objects.get(id=cf_id)
                args = cf_model.get_args()['list']
                try:
                    cf_value = self._convert_value_for_attr(cf_model, cf_value, args)
                except Exception:
                    cf_value = self._convert_value_for_attr(cf_model, '', args)
                args = {self.FieldName: self, 'field': cf_model}
                ccf_model = self.CustomFieldClass.objects.get_or_create(**args)
                ccf_model[0].value = str(cf_value)
                ccf_model[0].save()

    def get_custom_by_name(self, custom_name):
        fields = CustomField.objects.filter(modelname=self.__class__.get_long_name(), name=custom_name)
        if len(fields) == 1:
            return getattr(self, fields[0].get_fieldname())
        else:
            return None

    @classmethod
    def get_virtualfield(cls, name):
        format_num = None
        field_title = None
        if name == "str":
            field_title = ''
        elif name[:len(CustomField.PREFIX_CUSTOM)] == CustomField.PREFIX_CUSTOM:
            cf_id = int(name[len(CustomField.PREFIX_CUSTOM):])
            cf_model = CustomField.objects.get(id=cf_id)
            field_title = cf_model.name
            if cf_model.kind == CustomField.KIND_STRING:
                format_num = None
            elif cf_model.kind == CustomField.KIND_INTEGER:
                format_num = 'N0'
            elif cf_model.kind == CustomField.KIND_REAL:
                format_num = 'N%d' % cf_model.get_args()['prec']
            elif cf_model.kind == CustomField.KIND_BOOLEAN:
                format_num = 'B'
            elif cf_model.kind == CustomField.KIND_SELECT:
                format_num = {}
                args_list = cf_model.get_args()['list']
                for list_index in range(len(args_list)):
                    format_num[str(list_index)] = args_list[list_index]
            elif cf_model.kind == CustomField.KIND_DATE:
                format_num = 'D'
        if field_title is not None:
            return LucteriosVirtualField(verbose_name=field_title, name=name, compute_from=name, format_string=lambda: format_num)
        return None

    def _get_custom_for_attr(self, cf_model):
        args = {self.FieldName: self, 'field': cf_model}
        ccf_models = self.CustomFieldClass.objects.filter(**args)
        if len(ccf_models) == 0:
            ccf_model = self.CustomFieldClass.objects.create(**args)
        elif len(ccf_models) == 1:
            ccf_model = ccf_models[0]
        else:
            ccf_model = ccf_models[0]
            for old_model in ccf_models[1:]:
                old_model.delete()
        return ccf_model

    def __getattr__(self, name):
        if name == "str":
            return str(self.get_final_child())
        elif name[:len(CustomField.PREFIX_CUSTOM)] == CustomField.PREFIX_CUSTOM:
            cf_id = int(name[len(CustomField.PREFIX_CUSTOM):])
            cf_model = CustomField.objects.get(id=cf_id)
            if self.id is None:
                ccf_value = ""
                if cf_model.kind != CustomField.KIND_STRING:
                    ccf_value = self._convert_value_for_attr(cf_model, ccf_value)
            else:
                ccf_model = self._get_custom_for_attr(cf_model)
                if cf_model.kind == CustomField.KIND_STRING:
                    ccf_value = str(ccf_model.value)
                else:
                    ccf_value = self._convert_model_for_attr(cf_model, ccf_model)
            return ccf_value
        raise AttributeError(name)


class PostalCode(LucteriosModel):
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=False)

    postalcode__editfields = ['postal_code', 'city', 'country']
    postalcode__searchfields = ['postal_code', 'city', 'country']

    @classmethod
    def get_default_fields(cls):
        return ['postal_code', 'city', 'country']

    def __str__(self):
        return '[%s] %s %s' % (self.country, self.postal_code, self.city)

    class Meta(object):

        verbose_name = _('postal code')
        verbose_name_plural = _('postal codes')
        default_permissions = ['add', 'change']
        ordering = ['postal_code', 'city']
        unique_together = (('postal_code', 'city', 'country'),)


class Function(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_default_fields(cls):
        return ["name"]

    class Meta(object):

        verbose_name = _('individual function')
        verbose_name_plural = _('individual functions')
        default_permissions = []


class StructureType(LucteriosModel):
    name = models.CharField(_('name'), max_length=50, unique=True)

    @classmethod
    def get_default_fields(cls):
        return ["name"]

    def __str__(self):
        return self.name

    class Meta(object):

        verbose_name = _('structure type')
        verbose_name_plural = _('structure types')
        default_permissions = []


class ContactCustomField(LucteriosModel):
    contact = models.ForeignKey('AbstractContact', verbose_name=_('contact'), null=False, on_delete=models.CASCADE)
    field = models.ForeignKey('CustomField', verbose_name=_('field'), null=False, on_delete=models.CASCADE)
    value = models.TextField(_('value'), default="")

    data = LucteriosVirtualField(verbose_name=_('value'), compute_from=lambda item: item.field.convert_data(item.value))

    def get_auditlog_object(self):
        return self.contact.get_final_child()

    class Meta(object):
        verbose_name = _('custom field value')
        verbose_name_plural = _('custom field values')
        default_permissions = []


class AbstractContact(LucteriosModel, CustomizeObject):

    CustomFieldClass = ContactCustomField
    FieldName = 'contact'

    address = models.TextField(_('address'), blank=False)
    postal_code = models.CharField(_('postal code'), max_length=10, blank=False)
    city = models.CharField(_('city'), max_length=100, blank=False)
    country = models.CharField(_('country'), max_length=100, blank=True)
    tel1 = models.CharField(_('tel1'), max_length=20, blank=True)
    tel2 = models.CharField(_('tel2'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    comment = models.TextField(_('comment'), blank=True)

    def __str__(self):
        final_child = self.get_final_child(1)
        if final_child != self:
            return str(final_child)
        else:
            return "contact#%d" % self.id

    @classmethod
    def get_field_by_name(cls, fieldname):
        dep_field = CustomizeObject.get_virtualfield(fieldname)
        if dep_field is None:
            dep_field = super(AbstractContact, cls).get_field_by_name(fieldname)
        return dep_field

    @classmethod
    def get_default_fields(cls):
        return [(_('contact'), 'str'), 'tel1', 'tel2', 'email']

    @classmethod
    def get_show_fields(cls):
        fields_desc = ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email']
        fields_desc.extend(cls.get_fields_to_show())
        fields_desc.append('comment')
        return fields_desc

    @classmethod
    def get_edit_fields(cls):
        return ['address', ('postal_code', 'city'), 'country', ('tel1', 'tel2'), 'email', 'comment']

    @classmethod
    def get_search_fields(cls, with_addon=True):
        fieldnames = []
        fieldnames.extend(['address', 'postal_code', 'city', 'country', 'tel1', 'tel2', 'email', 'comment'])
        from django.db.models import Q
        for cf_name, cf_model in CustomField.get_fields(cls):
            fieldnames.append((cf_name, cf_model.get_field(), 'contactcustomfield__value', Q(contactcustomfield__field__id=cf_model.id)))
        if with_addon:
            Signal.call_signal("addon_search", cls, fieldnames)
        return fieldnames

    @classmethod
    def get_print_fields(cls):
        return [(_('contact'), 'str'), 'address', 'postal_code', 'city', 'country', 'tel1', 'tel2', 'email']

    @classmethod
    def get_import_fields(cls):
        fields = super(AbstractContact, cls).get_import_fields()
        for field in CustomField.get_fields(cls):
            fields.append((field[0], field[1].name))
        return fields

    @classmethod
    def import_data(cls, rowdata, dateformat):
        try:
            new_item = super(AbstractContact, cls).import_data(rowdata, dateformat)
            if new_item is not None:
                new_item.set_custom_values(rowdata)
            return new_item
        except Exception as import_error:
            cls.import_logs.append(str(import_error))
            logging.getLogger('lucterios.contacts').exception("import_data")
            return None

    @property
    def country_id(self):
        import pycountry
        country = pycountry.countries.get(name=self.country)
        if country is None:
            return self.country[:2].upper().strip()
        else:
            return country.alpha_2

    @country_id.setter
    def country_id(self, country_id):
        import pycountry
        country = pycountry.countries.get(alpha_2=country_id)
        if country is None:
            self.country = country_id
        else:
            self.country = country.name

    @property
    def address_list(self):
        return self.address.replace('{[newline/]}', '\n').replace('{[br/]}', '\n').split('\n')

    def get_presentation(self):
        return ""

    def get_email(self, only_main=None):
        email_list = []
        contact = self.get_final_child()
        if contact != self:
            return contact.get_email(only_main)
        if (only_main is not False) and (self.email != ''):
            email_list.append(self.email)
        return email_list

    @classmethod
    def get_all_print_fields(cls, with_plugin=True):
        fields = super(AbstractContact, cls).get_all_print_fields(with_plugin)
        for cf_name, cf_model in CustomField.get_fields(cls):
            fields.append((cf_model.name, cf_name))
        return fields

    @property
    def image(self):
        img_path = get_user_path("contacts", "Image_%s.jpg" % self.abstractcontact_ptr_id)
        if exists(img_path):
            img = readimage_to_base64(img_path)
        else:
            img = readimage_to_base64(join(dirname(__file__), "static", 'lucterios.contacts', "images", "NoImage.png"))
        return img.decode('ascii')

    def get_ref_contact(self):
        return self

    class Meta(object):
        verbose_name = _('generic contact')
        verbose_name_plural = _('generic contacts')


class LegalEntity(AbstractContact):
    name = models.CharField(_('denomination'), max_length=100, blank=False)
    structure_type = models.ForeignKey('StructureType', verbose_name=_('structure type'), null=True, on_delete=models.SET_NULL)

    legal_identification = models.CharField(_('legal identification'), max_length=30, blank=True)
    vat_identification = models.CharField(_('VAT identification number'), max_length=20, blank=True)

    identify_number = models.TextField(_('other identify information'), blank=True)

    @classmethod
    def get_show_fields(cls):
        ident_field = ['name', 'structure_type']
        ident_field.extend(super(LegalEntity, cls).get_show_fields())
        ident_field.extend(['legal_identification', 'vat_identification', 'identify_number'])
        res_fields = {_('001@Identity'): ident_field, _('002@Members'): ['responsability_set']}
        return res_fields

    @classmethod
    def get_edit_fields(cls):
        res_fields = ['name', 'structure_type']
        res_fields.extend(super(LegalEntity, cls).get_edit_fields())
        res_fields.extend(['legal_identification', 'vat_identification', 'identify_number'])
        return res_fields

    @classmethod
    def get_search_fields(cls, with_addon=True):
        res_fields = ['name', 'structure_type']
        res_fields.extend(super(LegalEntity, cls).get_search_fields(with_addon=False))
        res_fields.extend(['legal_identification', 'vat_identification', 'identify_number',
                           'responsability_set.individual.firstname',
                           'responsability_set.individual.lastname',
                           'responsability_set.functions'])
        if with_addon:
            Signal.call_signal("addon_search", cls, res_fields)
        return res_fields

    @classmethod
    def get_default_fields(cls):
        return ["name", 'tel1', 'tel2', 'email']

    @classmethod
    def get_print_fields(cls):
        ident_field = ["image", "name", 'structure_type',
                       'address', 'postal_code', 'city', 'country',
                       'tel1', 'tel2', 'email']
        ident_field.extend(['comment', 'legal_identification', 'vat_identification', 'identify_number', 'OUR_DETAIL'])
        return ident_field

    def __str__(self):
        return self.name

    def get_presentation(self):
        sub_contact = []
        for indiv in Individual.objects.filter(responsability__legal_entity=self):
            if len(split_doubled_email([indiv.email])) != 0:
                sub_contact.append(indiv.get_presentation())
        if len(sub_contact) == 0:
            return self.name
        else:
            return "%s (%s)" % (", ".join(sub_contact), self.name)

    def get_legal_identification(self):
        import re
        return re.sub('[^0-9_]+', '', self.legal_identification)

    def get_email(self, only_main=None):
        email_list = AbstractContact.get_email(self, only_main)
        if only_main is not True:
            for indiv in Individual.objects.filter(responsability__legal_entity=self).distinct():
                if indiv.email != '':
                    email_list.append(indiv.email)
        return email_list

    def can_delete(self):
        msg = AbstractContact.can_delete(self)
        if msg == '':
            if self.id == 1:
                msg = _("You cannot delete this legal entity!")
        return msg

    class Meta(object):
        verbose_name = _('legal entity')
        verbose_name_plural = _('legal entities')
        default_permissions = []
        ordering = ['name']


class Individual(AbstractContact):
    GENRE_ALL = 0
    GENRE_MAN = 1
    GENRE_WOMAN = 2
    LIST_GENRE = ((GENRE_MAN, _('Man')), (GENRE_WOMAN, _('Woman')))
    SELECT_GENRE = ((GENRE_ALL, None),) + LIST_GENRE

    genre = models.IntegerField(choices=LIST_GENRE, default=GENRE_MAN, null=False)
    firstname = models.CharField(_('firstname'), max_length=100, blank=False)
    lastname = models.CharField(_('lastname'), max_length=100, blank=False)
    user = models.ForeignKey('CORE.LucteriosUser', verbose_name=_('user'), null=True, on_delete=models.SET_NULL)

    @classmethod
    def get_show_fields(cls):
        ident_field = ['genre', ('firstname', 'lastname')]
        ident_field.extend(super(Individual, cls).get_show_fields())
        ident_field.append('user')
        res_fields = {_('001@Identity'): ident_field}
        return res_fields

    @classmethod
    def get_edit_fields(cls):
        ident_field = ['genre', ('firstname', 'lastname')]
        ident_field.extend(super(Individual, cls).get_edit_fields())
        return ident_field

    @classmethod
    def get_search_fields(cls, with_addon=True):
        ident_field = ['lastname', 'firstname', 'genre']
        ident_field.extend(super(Individual, cls).get_search_fields(with_addon=False))
        ident_field.extend(['user.username', 'user.is_active', 'responsability_set.legal_entity.name', 'responsability_set.functions'])
        if with_addon:
            Signal.call_signal("addon_search", cls, ident_field)
        return ident_field

    @classmethod
    def get_default_fields(cls):
        return ["firstname", "lastname", 'tel1', 'tel2', 'email']

    @classmethod
    def get_print_fields(cls):
        ident_field = ["image", "firstname", "lastname",
                       'address', 'postal_code', 'city', 'country',
                       'tel1', 'tel2', 'email']
        ident_field.extend(['comment', 'user', 'responsability_set', 'OUR_DETAIL'])
        return ident_field

    def __str__(self):
        return '%s %s' % (self.lastname, self.firstname)

    def get_presentation(self):
        return '%s %s' % (self.firstname, self.lastname)

    def create_username(self, usernamebase=None):
        username_temp = self.firstname.lower() + self.lastname.upper()[0] if usernamebase is None else usernamebase
        username_temp = ''.join(letter for letter in normalize('NFD', username_temp) if category(letter) != 'Mn')
        username = None
        inc = ""
        while username is None:
            username = "%s%s" % (username_temp, inc)
            users = LucteriosUser.objects.filter(username=username)
            if users.count() > 0:
                username = None
                if inc == "":
                    inc = 1
                else:
                    inc += 1
        return username

    class Meta(object):
        verbose_name = _('individual')
        verbose_name_plural = _('individuals')
        default_permissions = []
        ordering = ['lastname', 'firstname']


class Responsability(LucteriosModel):
    individual = models.ForeignKey(Individual, verbose_name=_('individual'), null=False, on_delete=models.CASCADE)
    legal_entity = models.ForeignKey(LegalEntity, verbose_name=_('legal entity'), null=False, on_delete=models.CASCADE)
    functions = models.ManyToManyField(Function, verbose_name=_('functions'), blank=True)
    functions__titles = [_("Available functions"), _("Chosen functions")]

    def __str__(self):
        return str(self.individual)

    def get_auditlog_object(self):
        return self.legal_entity.get_final_child()

    @classmethod
    def get_edit_fields(cls):
        return ["legal_entity", "individual", "functions"]

    @classmethod
    def get_search_fields(cls):
        return ["legal_entity", "individual", "functions"]

    @classmethod
    def get_default_fields(cls):
        return ["individual", "functions"]

    @classmethod
    def get_print_fields(cls):
        return ["legal_entity", "functions"]

    class Meta(object):
        verbose_name = _('associate')
        verbose_name_plural = _('associates')


class CategoryPossession(LucteriosModel):
    name = models.CharField(_('name'), max_length=100, blank=False)
    description = models.TextField(_('description'), blank=True)

    def __str__(self):
        return str(self.name)

    @classmethod
    def get_default_fields(cls):
        return ["name", "description"]

    class Meta(object):
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        default_permissions = []


class PossessionCustomField(LucteriosModel):
    possession = models.ForeignKey('Possession', verbose_name=_('possession'), null=False, on_delete=models.CASCADE)
    field = models.ForeignKey('CustomField', verbose_name=_('field'), null=False, on_delete=models.CASCADE)
    value = models.TextField(_('value'), default="")

    data = LucteriosVirtualField(verbose_name=_('value'), compute_from=lambda item: item.field.convert_data(item.value))

    def get_auditlog_object(self):
        return self.possession.get_final_child()

    class Meta(object):
        verbose_name = _('custom field value')
        verbose_name_plural = _('custom field values')
        default_permissions = []


class Possession(LucteriosModel, CustomizeObject):
    CustomFieldClass = PossessionCustomField
    FieldName = 'possession'

    category_possession = models.ForeignKey(CategoryPossession, verbose_name=_('category'), null=False, on_delete=models.PROTECT)
    name = models.CharField(_('name'), max_length=100, blank=False)
    owner = models.ForeignKey('AbstractContact', verbose_name=_('owner'), null=True, default=None, on_delete=models.PROTECT)
    comment = models.TextField(_('comment'), blank=True)

    def __str__(self):
        return str(self.name)

    @classmethod
    def get_field_by_name(cls, fieldname):
        dep_field = CustomizeObject.get_virtualfield(fieldname)
        if dep_field is None:
            dep_field = super(Possession, cls).get_field_by_name(fieldname)
        return dep_field

    def __getattr__(self, name):
        if name == "category_possession":
            if self.category_possession_id is None:
                return None
            else:
                return Possession.objects.get(id=self.category_possession_id)
        else:
            return CustomizeObject.__getattr__(self, name)

    @classmethod
    def get_default_fields(cls):
        return [("image", "image"), "category_possession", "owner", "name"]

    @classmethod
    def get_other_fields(cls):
        return [("image", "image"), "category_possession", "name"]

    @classmethod
    def get_show_fields(cls):
        fields_desc = [("category_possession", )]
        fields_desc.extend(cls.get_fields_to_show())
        fields_desc.append(("comment",))
        res_fields = {'': ["name", "owner"], _('001@Description'): fields_desc}
        return res_fields

    @classmethod
    def get_edit_fields(cls):
        return [("name", "category_possession"), "comment"]

    @classmethod
    def get_search_fields(cls, with_addon=True):
        fieldnames = ["category_possession", "name"]
        for cf_name, cf_model in CustomField.get_fields(cls):
            fieldnames.append((cf_name, cf_model.get_field(), 'possessioncustomfield__value', models.Q(possessioncustomfield__field__id=cf_model.id)))
        fieldnames.extend(["comment"])
        fieldnames.append(cls.convert_field_for_search('owner', ('name', LegalEntity._meta.get_field('name'), 'legalentity__name', models.Q())))
        fieldnames.append(cls.convert_field_for_search('owner', ('firstname', Individual._meta.get_field('firstname'), 'individual__firstname', models.Q())))
        fieldnames.append(cls.convert_field_for_search('owner', ('lastname', Individual._meta.get_field('lastname'), 'individual__lastname', models.Q())))
        for field_name in AbstractContact.get_search_fields(with_addon=False):
            fieldnames.append(cls.convert_field_for_search('owner', field_name))
        if with_addon:
            Signal.call_signal("addon_search", cls, fieldnames)
        return fieldnames

    @property
    def image(self):
        img_path = get_user_path("contacts", "Possession_%s.jpg" % self.id)
        if exists(img_path):
            img = readimage_to_base64(img_path)
        else:
            img = readimage_to_base64(join(dirname(__file__), "static", 'lucterios.contacts', "images", "NoImage.png"))
        return img.decode('ascii')

    @classmethod
    def import_data(cls, rowdata, dateformat):
        try:
            new_item = super(Possession, cls).import_data(rowdata, dateformat)
            if new_item is not None:
                new_item.set_custom_values(rowdata)
            return new_item
        except Exception as import_error:
            cls.import_logs.append(str(import_error))
            logging.getLogger('lucterios.contacts').exception("import_data")
            return None

    def delete(self, using=None):
        for custom in self.possessioncustomfield_set.all():
            custom.delete()
        LucteriosModel.delete(self, using=using)

    class Meta(object):
        verbose_name = _('possession')
        verbose_name_plural = _('possessions')


class OurDetailPrintPlugin(PrintFieldsPlugIn):

    name = "OUR_DETAIL"
    title = _('our detail')

    def get_all_print_fields(self):
        fields = []
        for title, name in LegalEntity.get_all_print_fields(False):
            if (name[:14] != 'structure_type') and (name[:len(self.name)] != self.name):
                fields.append(("%s > %s" % (self.title, title), "%s.%s" % (self.name, name)))
        return fields

    def evaluate(self, text_to_evaluate):
        our_details = LegalEntity.objects.get(id=1)
        return our_details.evaluate(text_to_evaluate)


PrintFieldsPlugIn.add_plugin(OurDetailPrintPlugin)


@Signal.decorate('addon_search')
def possession_addon_search(model, search_result):
    res = False
    if issubclass(model, AbstractContact) and (CategoryPossession.objects.all().count() > 0):
        for field_name in ["category_possession", "name", "comment"]:
            search_result.append(model.convert_field_for_search('possession_set', (field_name, Possession._meta.get_field(field_name), field_name, models.Q())))
        for cf_name, cf_model in CustomField.get_fields(Possession):
            field = (cf_name, cf_model.get_field(), 'possessioncustomfield__value', models.Q(possessioncustomfield__field__id=cf_model.id))
            search_result.append(model.convert_field_for_search('possession_set', field))
        res = True
    return res


@Signal.decorate('convertdata')
def contacts_convertdata():
    for custom in CustomField.objects.filter(order_key__isnull=True).order_by('id'):
        custom.save()
    for custom in CustomField.objects.all():
        print("convert contact customize field", custom)
        custom.check_associated()


@Signal.decorate('checkparam')
def contacts_checkparam():
    from django.apps import apps
    from django.conf import settings
    Parameter.check_and_create(name='contacts-mailtoconfig', typeparam=4, title=_("contacts-mailtoconfig"), args="{'Enum':3}", value='0',
                               param_titles=(_("contacts-mailtoconfig.0"), _("contacts-mailtoconfig.1"), _("contacts-mailtoconfig.2")))
    Parameter.check_and_create(name='contacts-createaccount', typeparam=4, title=_("contacts-createaccount"), args="{'Enum':3}", value='0',
                               param_titles=(_("contacts-createaccount.0"), _("contacts-createaccount.1"), _("contacts-createaccount.2")))
    Parameter.check_and_create(name="contacts-defaultgroup", typeparam=0, title=_("contacts-defaultgroup"),
                               args="{'Multi':False}", value='',
                               meta='("CORE","LucteriosGroup","django.db.models.Q()", "id", False)')
    Parameter.check_and_create(name="contacts-size-page", typeparam=1, title=_("contacts-size-page"), args="{}", value='25', meta='("","", "[(25,\'25\'),(50,\'50\'),(100,\'100\'),(250,\'250\'),(500,\'500\'),]", "", True)')

    if 'diacamma.event' in settings.INSTALLED_APPS:
        DegreeType = apps.get_model('event', "DegreeType")
        Event = apps.get_model('event', "Event")
        Degree = apps.get_model('event', "Degree")
        LucteriosGroup.redefine_generic(_("# contacts (administrator)"), PostalCode.get_permission(True, True, True), AbstractContact.get_permission(True, True, True), Responsability.get_permission(True, True, True),
                                        DegreeType.get_permission(True, True, True), Event.get_permission(True, True, True), Degree.get_permission(True, True, True))
        LucteriosGroup.redefine_generic(_("# contacts (editor)"), AbstractContact.get_permission(True, True, False), Responsability.get_permission(True, True, False),
                                        Event.get_permission(True, True, False), Degree.get_permission(True, True, False))
        LucteriosGroup.redefine_generic(_("# contacts (shower)"), AbstractContact.get_permission(True, False, False), Responsability.get_permission(True, False, False),
                                        Event.get_permission(True, False, False), Degree.get_permission(True, False, False))
    else:
        LucteriosGroup.redefine_generic(_("# contacts (administrator)"), PostalCode.get_permission(True, True, True), AbstractContact.get_permission(True, True, True), Responsability.get_permission(True, True, True))
        LucteriosGroup.redefine_generic(_("# contacts (editor)"), AbstractContact.get_permission(True, True, False), Responsability.get_permission(True, True, False))
        LucteriosGroup.redefine_generic(_("# contacts (shower)"), AbstractContact.get_permission(True, False, False), Responsability.get_permission(True, False, False))


@Signal.decorate('auditlog_register')
def contacts_auditlog_register():
    auditlog.register(LegalEntity)
    auditlog.register(Individual)
    auditlog.register(Responsability, include_fields=['individual', 'functions'])
    auditlog.register(PostalCode)
    auditlog.register(Function)
    auditlog.register(StructureType)
    auditlog.register(CustomField, include_fields=['name', 'model_title', 'kind_txt'])
    auditlog.register(ContactCustomField, include_fields=['field', 'data'], mapping_fields=['field'])
    auditlog.register(Possession)
    auditlog.register(PossessionCustomField, include_fields=['field', 'data'], mapping_fields=['field'])
