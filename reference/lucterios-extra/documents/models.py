# -*- coding: utf-8 -*-
'''
lucterios.documents package

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
from os import unlink, listdir, makedirs
from os.path import isfile, isdir, join, dirname
from zipfile import ZipFile
from lucterios.CORE.parameters import notfree_mode_connect, Params
from datetime import datetime
from zipfile import BadZipFile
from logging import getLogger
import sys

from django.db import models
from django.db.models.aggregates import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from lucterios.framework.models import LucteriosModel, LucteriosVirtualField, PrintFieldsPlugIn, LucteriosQuerySet
from lucterios.framework.filetools import get_user_path, remove_accent, BASE64_PREFIX, readimage_to_base64
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.auditlog import auditlog
from lucterios.framework.tools import get_binay, get_url_from_request, get_date_formating, toHtml

from lucterios.CORE.models import LucteriosGroup, LucteriosUser, Parameter

from lucterios.documents.models_legacy import Folder, Document
from lucterios.documents.doc_editors import DocEditor


class AbstractContainer(LucteriosModel):

    parent = models.ForeignKey('FolderContainer', verbose_name=_('parent'), null=True, on_delete=models.CASCADE)
    name = models.CharField(_('name'), max_length=250, blank=False)
    description = models.TextField(_('description'), blank=True)
    image = LucteriosVirtualField(verbose_name='', compute_from='get_image', format_string='icon')
    modif = LucteriosVirtualField(verbose_name=_('modifier'), compute_from='get_modif', )
    date_modif = LucteriosVirtualField(verbose_name=_('date modification'), compute_from='get_date_modif', format_string='H')

    indentification = LucteriosVirtualField(verbose_name=_('indentification'), compute_from='get_indentification')
    html_info = LucteriosVirtualField(verbose_name=_('info'), compute_from='get_info')
    group = LucteriosVirtualField(verbose_name=_('group'), compute_from='get_group')

    @classmethod
    def get_default_fields(cls):
        return ['image', "name", "description", "modif", "date_modif"]

    def get_image(self):
        if isinstance(self.get_final_child(), FolderContainer):
            return "mdi:mdi-folder-outline"
        else:
            return "mdi:mdi-file-outline"

    def get_modif(self):
        final_container = self.get_final_child()
        if isinstance(final_container, DocumentContainer):
            return final_container.modifier
        return None

    def get_indentification(self):
        return self.name

    def get_info(self):
        return ""

    def get_group(self):
        return self.__class__.__name__

    def get_date_modif(self):
        final_container = self.get_final_child()
        if isinstance(final_container, DocumentContainer):
            return final_container.date_modification
        return None

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.name = self.name[:250]
        return LucteriosModel.save(self, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta(object):
        verbose_name = _('container')
        verbose_name_plural = _('containers')
        default_permissions = []
        ordering = ['-foldercontainer', 'parent__name', 'name']


class FolderContainer(AbstractContainer):
    viewer = models.ManyToManyField(LucteriosGroup, related_name="foldercontainer_viewer", verbose_name=_('viewer'), blank=True)
    modifier = models.ManyToManyField(LucteriosGroup, related_name="foldercontainer_modifier", verbose_name=_('modifier'), blank=True)

    BAD_RECURSIVE = " !! "
    MAX_RECURSIVE = 10

    def get_indentification(self):
        return self.name

    def get_info(self):
        return """<b>%(title_name)s</b> %(name)s<br/>
<b>%(title_description)s</b> %(description)s<br/>
""" % {
            'title_name': _('name'),
            'title_description': _('description'),
            'name': self.name,
            'description': toHtml(self.description)
        }

    @classmethod
    def get_show_fields(cls):
        return {_('001@Info'): ["name", "description", "parent"],
                _('001@Permission'): ["viewer", "modifier"]}

    @classmethod
    def get_edit_fields(cls):
        return {_('001@Info'): ["name", "description", "parent"],
                _('001@Permission'): ["viewer", "modifier"]}

    @classmethod
    def get_search_fields(cls):
        return ["name", "description", "parent.name"]

    @classmethod
    def get_default_fields(cls):
        return ["name", "description", "parent"]

    def get_title(self, num=0):
        try:
            title = ">" + self.name
            if self.parent_id is not None:
                if num < self.MAX_RECURSIVE:
                    title = self.parent.get_title(num + 1) + title
                else:
                    title = self.BAD_RECURSIVE
            return title
        except FolderContainer.DoesNotExist:
            return "---"

    def __str__(self):
        return self.get_title()

    def is_readonly(self, user):
        if user.is_superuser:
            return False
        readonly = True
        for modifier_item in self.modifier.all():
            if modifier_item in user.groups.all():
                readonly = False
        return readonly

    def cannot_view(self, user):
        if user.is_superuser:
            return False
        cannotview = True
        for viewer_item in self.viewer.all():
            if viewer_item in user.groups.all():
                cannotview = False
        return cannotview

    def get_subfiles(self):
        file_paths = []
        if self.id is not None:
            for container in self.abstractcontainer_set.all():
                container = container.get_final_child()
                if isinstance(container, DocumentContainer):
                    file_paths.append(container.file_path)
                else:
                    file_paths.extend(container.get_subfiles())
        return file_paths

    def get_subfolders(self, user, wantmodify):
        items = FolderContainer.objects.filter(models.Q(parent=self if self.id is not None else None))
        if notfree_mode_connect() and not user.is_superuser:
            new_items = []
            for item in items:
                if not item.cannot_view(user):
                    if wantmodify and not item.is_readonly(user):
                        new_items.append(item)
                    elif not wantmodify:
                        new_items.append(item)
            items = LucteriosQuerySet(model=FolderContainer, initial=new_items)
        return items

    def delete(self):
        sub_containers = list(self.abstractcontainer_set.all())
        for sub_container in sub_containers:
            sub_container = sub_container.get_final_child()
            sub_container.delete()
        LucteriosModel.delete(self)

    def import_files(self, dir_to_import, viewers, modifiers, user):
        for filename in listdir(dir_to_import):
            complet_path = join(dir_to_import, filename)
            if isfile(complet_path):
                new_doc = DocumentContainer(name=filename, description=filename, parent_id=self.id)
                if user.is_authenticated:
                    new_doc.creator = LucteriosUser.objects.get(pk=user.id)
                    new_doc.modifier = new_doc.creator
                new_doc.date_modification = timezone.now()
                new_doc.date_creation = new_doc.date_modification
                new_doc.save()
                with open(complet_path, 'rb') as file_content:
                    new_doc.content = file_content.read()
            elif isdir(complet_path):
                new_folder = FolderContainer.objects.create(name=filename, description=filename, parent_id=self.id)
                new_folder.viewer = viewers
                new_folder.modifier = modifiers
                new_folder.save()
                new_folder.import_files(complet_path, viewers, modifiers, user)

    def extract_files(self, dir_to_extract):
        for doc in DocumentContainer.objects.filter(parent_id=self.id):
            if isfile(doc.file_path):
                try:
                    with ZipFile(doc.file_path, 'r') as zip_ref:
                        zip_ref.extractall(dir_to_extract)
                except BadZipFile:
                    pass
        for folder in FolderContainer.objects.filter(parent_id=self.id):
            new_dir_to_extract = join(dir_to_extract, folder.name)
            if not isdir(new_dir_to_extract):
                makedirs(new_dir_to_extract)
            folder.extract_files(new_dir_to_extract)

    def add_pdf_document(self, title, user, metadata, pdf_content):
        new_doc = DocumentContainer.objects.create(name=remove_accent('%s.pdf' % title), description=title.replace('_', ' '), parent=self,
                                                   creator=user, modifier=user, metadata=metadata,
                                                   date_creation=timezone.now(), date_modification=timezone.now())
        new_doc.content = pdf_content
        return new_doc

    class Meta(object):
        verbose_name = _('folder')
        verbose_name_plural = _('folders')
        default_permissions = []
        ordering = ['parent__name', 'name']


class DocumentContainer(AbstractContainer):

    MINIATURE_HEIGHT = 200

    modifier = models.ForeignKey(LucteriosUser, related_name="documentcontainer_modifier",
                                 verbose_name=_('modifier'), null=True, on_delete=models.CASCADE)
    date_modification = models.DateTimeField(verbose_name=_('date modification'), null=False)
    creator = models.ForeignKey(LucteriosUser, related_name="documentcontainer_creator",
                                verbose_name=_('creator'), null=True, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(verbose_name=_('date creation'), null=False)
    sharekey = models.CharField('sharekey', max_length=100, null=True)
    metadata = models.CharField('metadata', max_length=200, null=True)

    @classmethod
    def get_popper_path(cls):
        if not hasattr(cls, "popper_path"):
            cls.popper_path = join(dirname(sys.executable), 'popper')
            if not isdir(cls.popper_path):
                cls.popper_path = None
        return cls.popper_path

    def get_indentification(self):
        if self.description == '':
            return self.name
        else:
            value = self.description
            for item in ('br', 'br/', 'newline', 'newline/'):
                value = value.replace('{[%s]}' % item, '\n')
            return value.split('\n')[0].strip()

    def get_info(self):
        return """<b>%(title_name)s</b> %(name)s<br/>
<b>%(title_description)s</b> %(description)s<br/>
<b>%(title_modif)s</b> %(modif)s<br/>
<b>%(title_date_modif)s</b> %(date_modif)s<br/>
""" % {
            'title_name': _('name'),
            'title_description': _('description'),
            'title_modif': _('modifier'),
            'title_date_modif': _('date modification'),
            'name': self.name,
            'description': toHtml(self.description),
            'modif': self.modif if self.modif is not None else '---',
            'date_modif': get_date_formating(self.date_modif) if self.date_modif is not None else '---'
        }

    @classmethod
    def get_show_fields(cls):
        return ["name", "parent", "description", ("modifier", "date_modification"), ("creator", "date_creation")]

    @classmethod
    def get_edit_fields(cls):
        return ["parent", "name", "description"]

    @classmethod
    def get_search_fields(cls):
        return ["name", "description", "parent.name", "date_modification", "date_creation"]

    @classmethod
    def get_default_fields(cls):
        return ["image", "name", "description", "date_modification", "modifier"]

    def __init__(self, *args, **kwargs):
        AbstractContainer.__init__(self, *args, **kwargs)
        self.filter = models.Q()
        self.shared_link = None
        self.root_url = None

    def __str__(self):
        return '[%s] %s' % (self.parent, self.name)

    @property
    def file_path(self):
        return get_user_path("documents", "container_%s" % str(self.id))

    @property
    def miniature_path(self):
        return get_user_path("documents", "miniature_%s.png" % str(self.id))

    @property
    def mimetypevalue(self):
        import magic
        if not hasattr(self, '_mimetypevalue'):
            self._mimetypevalue = magic.from_buffer(self.content.read(2048))
        return self._mimetypevalue

    def _resize_miniature(self, image):
        original_width, original_height = image.size
        miniature_width = original_width * self.MINIATURE_HEIGHT / original_height
        image = image.resize((int(miniature_width), self.MINIATURE_HEIGHT))
        image = image.convert("RGB")
        with open(self.miniature_path, "wb") as image_file:
            image.save(image_file, 'PNG', quality=90)

    def _create_miniature_image_outline(self):
        from PIL import Image
        image = Image.open(self.content)
        self._resize_miniature(image)
        return isfile(self.miniature_path)

    def _create_miniature_file_chart_outline(self):
        from cairosvg import svg2png
        with open(self.miniature_path, 'wb') as png_file:
            svg2png(file_obj=self.content, write_to=png_file, output_height=self.MINIATURE_HEIGHT)
        return isfile(self.miniature_path)

    def _create_miniature_file_pdf_box(self):
        # Download "pdfinfo" : https://www.xpdfreader.com/download.html (Xpdf command line tools)
        from pdf2image import convert_from_bytes
        images_list = convert_from_bytes(self.content.read(), first_page=0, last_page=1, poppler_path=self.get_popper_path())
        if len(images_list) > 0:
            self._resize_miniature(images_list[0])
        return isfile(self.miniature_path)

    def get_image(self):
        if isfile(self.miniature_path):
            return readimage_to_base64(self.miniature_path).decode()
        image_to_show = None
        if 'image' in self.mimetypevalue:
            image_to_show = "mdi:mdi-image-outline"
        if 'text' in self.mimetypevalue:
            image_to_show = "mdi:mdi-text-box-outline"
        if self.mimetypevalue.startswith('SVG'):
            image_to_show = "mdi:mdi-file-chart-outline"
        if self.mimetypevalue.startswith('PDF document'):
            image_to_show = "mdi:mdi-file-pdf-box"
        if self.mimetypevalue.startswith('Microsoft Excel'):
            image_to_show = "mdi:mdi-file-excel-outline"
        if self.mimetypevalue.startswith('Microsoft Word'):
            image_to_show = "mdi:mdi-file-word-outline"
        if self.mimetypevalue.startswith('Microsoft PowerPoint'):
            image_to_show = "mdi:mdi-file-powerpoint-outline"
        if self.mimetypevalue.startswith('OpenDocument'):
            image_to_show = "mdi:mdi-file-document"
        if image_to_show is not None:
            convert_function = getattr(self, "_create_miniature_" + image_to_show[8:].replace('-', '_'), None)
            if (convert_function is not None) and convert_function():
                return readimage_to_base64(self.miniature_path).decode()
            return image_to_show
        return AbstractContainer.get_image(self)

    def delete(self):
        file_path = self.file_path
        miniature_file_path = self.miniature_path
        LucteriosModel.delete(self)
        if isfile(file_path):
            unlink(file_path)
        if isfile(miniature_file_path):
            unlink(miniature_file_path)

    def set_context(self, xfer):
        if notfree_mode_connect() and not isinstance(xfer, str) and not xfer.request.user.is_superuser:
            self.filter = models.Q(parent=None) | models.Q(parent__viewer__in=xfer.request.user.groups.all())
        if isinstance(xfer, str):
            self.root_url = xfer
        else:
            self.root_url = get_url_from_request(xfer.request)
        if self.sharekey is not None:
            import urllib.parse
            self.shared_link = "%s/%s?shared=%s&filename=%s" % (self.root_url, 'lucterios.documents/downloadFile', self.sharekey, urllib.parse.quote(self.name))
        else:
            self.shared_link = None

    @property
    def folder_query(self):
        return FolderContainer.objects.filter(self.filter)

    @property
    def isempty(self):
        return not isfile(self.file_path)

    @property
    def content(self):
        from _io import BytesIO
        if isfile(self.file_path):
            with ZipFile(self.file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                if len(file_list) > 0:
                    doc_file = zip_ref.open(file_list[0])
                    return BytesIO(doc_file.read())
        return BytesIO(b'')

    @content.setter
    def content(self, content):
        from _io import BytesIO
        if (content == "") or (content == b""):
            if isfile(self.file_path):
                unlink(self.file_path)
        elif not isinstance(content, BytesIO) and hasattr(content, 'read'):
            with open(self.file_path, "wb") as file_tmp:
                file_tmp.write(content.read())
        else:
            with ZipFile(self.file_path, 'w') as zip_ref:
                if isinstance(content, BytesIO):
                    content = content.read()
                if isinstance(content, str):
                    content = content.encode()
                if isinstance(content, bytes):
                    zip_ref.writestr(zinfo_or_arcname=self.name, data=content)
        if isfile(self.miniature_path):
            unlink(self.miniature_path)

    def change_sharekey(self, clear):
        if clear:
            self.sharekey = None
        else:
            from hashlib import md5
            phrase = "%s %s %s" % (self.name, self.date_creation, datetime.now())
            md5res = md5()
            md5res.update(phrase.encode())
            self.sharekey = md5res.hexdigest()

    def get_doc_editors(self, user=None, wantWrite=True):
        readonly = not wantWrite or (self.parent.is_readonly(user) if (user is not None) and (self.parent is not None) else False)
        for editor_class in DocEditor.get_all_editor():
            editor_obj = editor_class(self.root_url, self, readonly, user)
            if editor_obj.is_manage():
                return editor_obj
        return None

    class Meta(object):
        verbose_name = _('document')
        verbose_name_plural = _('documents')
        default_permissions = []
        ordering = ['parent__name', 'name']


def migrate_containers(old_parent, new_parent):
    nb_folder = 0
    nb_doc = 0
    for old_document in Document.objects.filter(folder=old_parent):
        new_doc = DocumentContainer(parent=new_parent, name=old_document.name, description=old_document.description)
        new_doc.modifier = old_document.modifier
        new_doc.date_modification = old_document.date_modification
        new_doc.creator = old_document.creator
        new_doc.date_creation = old_document.date_creation
        new_doc.save()
        new_doc.content = old_document.content
        nb_doc += 1

    for old_folder in Folder.objects.filter(parent=old_parent):
        new_folder = FolderContainer.objects.create(parent=new_parent, name=old_folder.name, description=old_folder.description)
        new_folder.viewer.set(old_folder.viewer.all())
        new_folder.modifier.set(old_folder.modifier.all())
        sub_nb_folder, sub_nb_doc = migrate_containers(old_folder, new_folder)
        old_folder.delete()
        nb_folder += sub_nb_folder
        nb_doc += sub_nb_doc
        nb_folder += 1
    if (old_parent is None) and (nb_folder > 0):
        getLogger("lucterios.documents").info('Convert containers: folder=%d - documents=%d', nb_folder, nb_doc)
    return nb_folder, nb_doc


def merge_multicontainers():
    nb_folder = 0
    nb_doc = 0
    for multi_data in FolderContainer.objects.values("name", "description", "parent").annotate(Count('id')).values("name", "description", "parent").order_by().filter(id__count__gt=1):
        multi_folders = FolderContainer.objects.filter(**multi_data).order_by('id')
        if len(multi_folders) > 1:
            try:
                first_folder = multi_folders.first()
                first_folder.get_final_child().merge_objects(list(multi_folders)[1:])
                nb_folder += 1
            except Exception as err:
                getLogger("lucterios.documents").error('merge_multicontainers Folder error %s -> %s', multi_folders, err)
    for multi_data in DocumentContainer.objects.values("name", "description", "parent", "date_modification", "modifier").annotate(Count('id')).values("name", "description", "parent", "date_modification", "modifier").order_by().filter(id__count__gt=1):
        multi_documents = DocumentContainer.objects.filter(**multi_data).order_by('id')
        if len(multi_documents) > 1:
            try:
                first_document = multi_documents.first()
                first_document.get_final_child().merge_objects(list(multi_documents)[1:])
                nb_doc += 1
            except Exception as err:
                getLogger("lucterios.documents").error('merge_multicontainers Document error %s -> %s', multi_documents, err)
    if (nb_doc > 0) or (nb_folder > 0):
        getLogger("lucterios.documents").info('Merge multi-containers: folder=%d - documents=%d', nb_folder, nb_doc)


class DefaultDocumentsPrintPlugin(PrintFieldsPlugIn):

    name = "DEFAULT_DOCUMENTS"
    title = _('default documents')

    doc_list = {'signature': "documents-signature"}

    def get_all_print_fields(self):
        fields = []
        for doc_key, doc_value in self.doc_list.items():
            fields.append(("%s > %s" % (self.title, _(doc_value)), "%s.%s" % (self.name, doc_key)))
        return fields

    def evaluate(self, text_to_evaluate):
        from base64 import b64encode
        value = text_to_evaluate
        for doc_key, doc_value in self.doc_list.items():
            if "#%s" % doc_key in value:
                image_file = Params.getobject(doc_value)
                if image_file is None:
                    image_base64 = b''
                else:
                    image_base64 = get_binay(BASE64_PREFIX) + b64encode(image_file.content.read())
                value = value.replace("#%s" % doc_key, image_base64.decode())
        return value


PrintFieldsPlugIn.add_plugin(DefaultDocumentsPrintPlugin)


def check_parent_folder():
    for folder in FolderContainer.objects.all():
        if folder.get_title().startswith(FolderContainer.BAD_RECURSIVE):
            folder.parent = None
            folder.save()


@Signal.decorate('convertdata')
def documents_convertdata():
    migrate_containers(None, None)
    merge_multicontainers()
    check_parent_folder()


@Signal.decorate('checkparam')
def documents_checkparam():
    Parameter.check_and_create(name="documents-signature", typeparam=0, title=_("documents-signature"),
                               args="{'Multi':False}", value='',
                               meta='("documents","DocumentContainer","django.db.models.Q(name__regex=\'.*\\.jpg|.*\\.png\')", "id", False)')

    LucteriosGroup.redefine_generic(_("# documents (administrator)"), Folder.get_permission(True, True, True), Document.get_permission(True, True, True))
    LucteriosGroup.redefine_generic(_("# documents (editor)"), Document.get_permission(True, True, True))


@Signal.decorate('config')
def config_documents(setting_list):
    setting_list['60@%s' % _("Document")] = ["documents-signature"]
    return True


@Signal.decorate('auditlog_register')
def documents_auditlog_register():
    auditlog.register(FolderContainer, include_fields=["name", "description", "viewer", "modifier"])
    auditlog.register(DocumentContainer, include_fields=["name", "description", "modif", "date_modif", "sharekey"])
