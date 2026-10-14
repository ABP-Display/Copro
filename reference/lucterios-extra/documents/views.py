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
from os.path import join, exists
from os import makedirs, walk
from shutil import rmtree
from zipfile import ZipFile
from logging import getLogger

from django.utils.translation import gettext_lazy as _
from django.apps.registry import apps
from django.db.models import Q
from django.db.models.query import QuerySet
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.http import require_GET
from django.views import View

from lucterios.framework.xferadvance import XferListEditor, XferDelete, XferAddEditor, XferShowEditor, \
    TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_EDIT, TITLE_CANCEL, TITLE_OK, \
    TEXT_TOTAL_NUMBER, TITLE_CLOSE, TITLE_SAVE, TITLE_CREATE
from lucterios.framework.xfersearch import XferSearchEditor
from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, ActionsManage, \
    CLOSE_NO, FORMTYPE_REFRESH, SELECT_SINGLE, SELECT_NONE, \
    WrapAction, CLOSE_YES, SELECT_MULTI, get_url_from_request, FORMTYPE_MODAL
from lucterios.framework.xfercomponents import XferCompButton, XferCompLabelForm, \
    XferCompImage, XferCompUpLoad, XferCompDownLoad, XferCompSelect, XferCompMosaic, MOSAIC_ORDER
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework import signal_and_lock
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.filetools import get_tmp_dir, get_user_dir
from lucterios.CORE.parameters import notfree_mode_connect
from lucterios.CORE.models import LucteriosGroup, LucteriosUser
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor

from lucterios.documents.models import FolderContainer, DocumentContainer, AbstractContainer
from lucterios.documents.doc_editors import DocEditor


MenuManage.add_sub("documents.conf", "core.extensions", short_icon='mdi:mdi-folder-cog-outline', caption=_("Document"), pos=10)


@MenuManage.describ('documents.change_folder', FORMTYPE_NOMODAL, 'documents.conf', _("Management of document's folders"))
class FolderList(XferListEditor):
    caption = _("Folders")
    short_icon = 'mdi:mdi-folder-cog'
    model = FolderContainer
    field_id = 'folder'


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline')
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('documents.add_folder')
class FolderAddModify(XferAddEditor):
    short_icon = 'mdi:mdi-folder-cog'
    model = FolderContainer
    field_id = 'folder'
    caption_add = _("Add folder")
    caption_modify = _("Modify folder")

    def _search_model(self):
        current_folder = self.getparam('document', 0)
        if (current_folder != 0) and (current_folder != self.getparam('folder', 0)):
            self.params['parent'] = current_folder
        XferAddEditor._search_model(self)

    def fillresponse(self):
        XferAddEditor.fillresponse(self)
        parentid = self.getparam('parent', 0)
        if (self.item.id is None) and (parentid != 0):
            parent = FolderContainer.objects.get(id=parentid)
            viewer = self.get_components('viewer')
            viewer.set_value([group.id for group in parent.viewer.all()])
            modifier = self.get_components('modifier')
            modifier.set_value([group.id for group in parent.modifier.all()])


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('documents.delete_folder')
class FolderDel(XferDelete):
    caption = _("Delete folder")
    short_icon = 'mdi:mdi-folder-cog'
    model = FolderContainer
    field_id = 'folder'


class FolderImportExport(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-folder-cog'
    model = FolderContainer
    field_id = 'folder'

    def add_components(self, dlg):
        pass

    def run_archive(self):
        pass

    def fillresponse(self):
        if self.getparam('SAVE') is None:
            dlg = self.create_custom()
            dlg.item = self.item
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 3)
            dlg.add_component(img)
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_title(self.caption)
            lbl.set_location(1, 0, 6)
            dlg.add_component(lbl)

            dlg.fill_from_model(1, 1, False, desc_fields=['parent'])
            parent = dlg.get_components('parent')
            parent.colspan = 3

            self.add_components(dlg)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), close=CLOSE_YES, params={'SAVE': 'YES'})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            if self.getparam("parent", 0) != 0:
                self.item = FolderContainer.objects.get(id=self.getparam("parent", 0))
            else:
                self.item = FolderContainer()
            self.run_archive()


@ActionsManage.affect_grid(_("Import"), short_icon='mdi:mdi-folder-zip-outline', unique=SELECT_NONE)
@MenuManage.describ('documents.add_folder')
class FolderImport(FolderImportExport):
    caption = _("Import")

    def add_components(self, dlg):
        dlg.fill_from_model(1, 2, False, desc_fields=['viewer', 'modifier'])
        zipfile = XferCompUpLoad('zipfile')
        zipfile.http_file = True
        zipfile.description = _('zip file')
        zipfile.maxsize = 1024 * 1024 * 1024  # 1Go
        zipfile.add_filter('.zip')
        zipfile.set_location(1, 15)
        dlg.add_component(zipfile)

    def run_archive(self):
        viewerids = self.getparam("viewer", ())
        modifierids = self.getparam("modifier", ())
        if 'zipfile' in self.request.FILES.keys():
            upload_file = self.request.FILES['zipfile']
            tmp_dir = join(get_tmp_dir(), 'zipfile')
            if exists(tmp_dir):
                rmtree(tmp_dir)
            makedirs(tmp_dir)
            try:
                with ZipFile(upload_file, 'r') as zip_ref:
                    zip_ref.extractall(tmp_dir)
                viewers = LucteriosGroup.objects.filter(id__in=viewerids)
                modifiers = LucteriosGroup.objects.filter(id__in=modifierids)
                self.item.import_files(
                    tmp_dir, viewers, modifiers, self.request.user)
            finally:
                if exists(tmp_dir):
                    rmtree(tmp_dir)


@ActionsManage.affect_grid(_("Extract"), short_icon='mdi:mdi-folder-zip-outline', unique=SELECT_NONE)
@MenuManage.describ('documents.add_folder')
class FolderExtract(FolderImportExport):
    caption = _("Extract")

    def open_zipfile(self, filename):
        dlg = self.create_custom()
        dlg.item = self.item
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 3)
        dlg.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(self.caption)
        lbl.set_location(1, 0, 6)
        dlg.add_component(lbl)
        zipdown = XferCompDownLoad('filename')
        zipdown.compress = False
        zipdown.http_file = True
        zipdown.maxsize = 0
        zipdown.set_value(filename)
        zipdown.set_download(filename)
        zipdown.set_location(1, 15, 2)
        dlg.add_component(zipdown)

    def run_archive(self):
        tmp_dir = join(get_tmp_dir(), 'zipfile')
        download_file = join(get_user_dir(), 'extract.zip')
        if exists(tmp_dir):
            rmtree(tmp_dir)
        makedirs(tmp_dir)
        try:
            self.item.extract_files(tmp_dir)
            with ZipFile(download_file, 'w') as zip_ref:
                for (dirpath, _dirs, filenames) in walk(tmp_dir):
                    for filename in filenames:
                        zip_ref.write(
                            join(dirpath, filename), join(dirpath[len(tmp_dir):], filename))
        finally:
            if exists(tmp_dir):
                rmtree(tmp_dir)
        self.open_zipfile('extract.zip')


if not apps.is_installed("lucterios.contacts"):
    MenuManage.add_sub("office", None, short_icon='mdi:mdi-monitor', caption=_("Office"), desc=_("Office tools"), pos=70)

MenuManage.add_sub("documents.actions", "office", short_icon='mdi:mdi-folder-outline', caption=_("Documents management"), desc=_("Documents storage tools"), pos=80)


def docshow_modify_condition(xfer):
    if xfer.item.parent is not None and notfree_mode_connect() and not xfer.request.user.is_superuser:
        if xfer.item.parent.cannot_view(xfer.request.user):
            raise LucteriosException(IMPORTANT, _("No allow to view!"))
        if xfer.item.parent.is_readonly(xfer.request.user):
            return False
    return True


def folder_notreadonly_condition(xfer, gridname=''):
    if notfree_mode_connect() and not xfer.request.user.is_superuser:
        if not hasattr(xfer, 'curren_item'):
            return False
        elif xfer.curren_item.id is not None:
            folder = FolderContainer.objects.get(id=xfer.curren_item.id)
            if folder.cannot_view(xfer.request.user):
                raise LucteriosException(IMPORTANT, _("No allow to view!"))
            if folder.is_readonly(xfer.request.user):
                return False
    return True


@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', close=CLOSE_YES, condition=docshow_modify_condition)
@MenuManage.describ('documents.add_document')
class DocumentAddModify(XferAddEditor):
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = 'document'
    caption_add = _("Add document")
    caption_modify = _("Modify document")

    def _search_model(self):
        self.current_folder = FolderContainer.objects.filter(id=self.getparam('document', 0)).first()
        if self.current_folder is not None:
            self.params['parent'] = self.current_folder.id
            del self.params['document']
        XferAddEditor._search_model(self)

    def fillresponse(self):
        if not docshow_modify_condition(self):
            raise LucteriosException(IMPORTANT, _("No allow to write!"))
        XferAddEditor.fillresponse(self)
        if self.current_folder is not None:
            self.get_components('parent').set_value(self.current_folder.id)


@MenuManage.describ('documents.change_document')
class DocumentShow(XferShowEditor):
    caption = _("Show document")
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = 'document'

    def fillresponse(self, current_folder=0):
        if (self.item.id is None) and (current_folder != 0):
            self.item = DocumentContainer.objects.get(id=current_folder)
        XferShowEditor.fillresponse(self)
        mini_image = self.item.get_image()
        self.get_components('img').set_value(mini_image, '#' if mini_image.startswith('mdi:') else 'png')


@ActionsManage.affect_show(_('Editor'), short_icon='mdi:mdi-file-outline', modal=FORMTYPE_NOMODAL,
                           close=CLOSE_YES, condition=lambda xfer: xfer.item.get_doc_editors(wantWrite=False) is not None)
@MenuManage.describ('documents.add_document')
class DocumentEditor(XferContainerAcknowledge):
    caption = _("Edit document")
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = 'document'

    def fillresponse(self):
        editor = self.item.get_doc_editors(self.request.user, False)
        if self.getparam('SAVE', '') == 'YES':
            editor.save_content()
        elif self.getparam('CLOSE', '') == 'YES':
            editor.close()
        else:
            editor.send_content()
            dlg = self.create_custom(self.model)
            dlg.item = self.item
            dlg.fill_from_model(0, 0, True, [('parent', 'name')])
            frame = XferCompLabelForm('frame')
            frame.set_value(editor.get_iframe())
            frame.set_location(0, 2, 2, 0)
            dlg.add_component(frame)
            if editor.withSaveBtn:
                dlg.add_action(self.return_action(TITLE_SAVE, short_icon='mdi:mdi-content-save-outline'), close=CLOSE_NO, params={'SAVE': 'YES'})
            dlg.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))
            dlg.set_close_action(self.return_action(), params={'CLOSE': 'YES'})


def file_createnew_condition(xfer, gridname=''):
    if folder_notreadonly_condition(xfer, gridname):
        return (len(DocEditor.get_all_extension_supported()) > 0)
    else:
        return False


@ActionsManage.affect_grid(_('File'), short_icon='mdi:mdi-pencil-plus-outline', condition=file_createnew_condition)
@MenuManage.describ('documents.add_document')
class ContainerAddFile(XferContainerAcknowledge):
    caption = _("Create document")
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = 'document'

    def _search_model(self):
        if 'document' in self.params:
            current_id = self.getparam('document', 0)
            del self.params['document']
        else:
            current_id = 0
        self.current_folder = FolderContainer.objects.get(id=current_id) if current_id != 0 else None
        XferContainerAcknowledge._search_model(self)

    def fillresponse(self, docext=""):
        if self.getparam('CONFIRME', '') == 'YES':
            self.params = {}
            filename_spited = self.item.name.split('.')
            if len(filename_spited) > 1:
                filename_spited = filename_spited[:-1]
            self.item.name = "%s.%s" % (".".join(filename_spited), docext)
            self.item.parent = self.current_folder
            self.item.editor.before_save(self)
            self.item.save()
            self.item.get_doc_editors(self.request.user, True).get_empty()
            self.redirect_action(DocumentEditor.get_action(), modal=FORMTYPE_NOMODAL, close=CLOSE_YES, params={'document': self.item.id})
        else:
            dlg = self.create_custom(self.model)
            max_row = dlg.get_max_row() + 1
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 6)
            dlg.add_component(img)
            dlg.item.parent = self.current_folder
            dlg.fill_from_model(1, max_row, True, ['parent'])
            dlg.fill_from_model(1, max_row + 1, False, ['name', 'description'])

            max_row = dlg.get_max_row() + 1
            select = XferCompSelect('docext')
            select.set_select([(item, item) for item in DocEditor.get_all_extension_supported()])
            select.set_value(select.select_list[0][1])
            select.set_location(1, max_row)
            select.description = _('document type')
            dlg.add_component(select)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), close=CLOSE_YES, params={'CONFIRME': 'YES'})
            dlg.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@MenuManage.describ('documents.delete_document')
class DocumentDel(XferDelete):
    caption = _("Delete document")
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = ('document', 'current_folder')

    def fillresponse(self, current_folder=()):
        if len(self.items) > 0:
            self.item = self.items[0]
            if not docshow_modify_condition(self):
                raise LucteriosException(IMPORTANT, _("No allow to write!"))
            XferDelete.fillresponse(self)
        else:
            XferContainerAcknowledge.fillresponse(self)


@MenuManage.describ('documents.change_document', FORMTYPE_NOMODAL, 'documents.actions', _("Management of documents"))
class DocumentMosaic(XferListEditor):
    caption = _("Documents")
    short_icon = 'mdi:mdi-folder-outline'
    model = AbstractContainer
    field_id = 'document'

    def _search_model(self):
        if self.getparam('document') == '0':
            del self.params['document']
        XferListEditor._search_model(self)

    def fillresponse_header(self):
        self.get_components('title').colspan = 3
        lbl = XferCompLabelForm('title_folder')
        lbl.set_location(0, 2, 2)
        lbl.description = _("current folder:")
        self.add_component(lbl)
        if self.item.id is not None:
            self.curren_item = self.item.get_final_child()
            lbl.set_value(self.curren_item.get_title())
            lbl = XferCompLabelForm('desc_folder')
            lbl.set_location(2, 2, 2)
            lbl.set_value(self.curren_item.description)
            self.add_component(lbl)
            self.filter = Q(parent=self.curren_item)
            if notfree_mode_connect() and not self.request.user.is_superuser:
                filter_folder = Q(foldercontainer__isnull=False) & Q(foldercontainer__viewer__in=self.request.user.groups.all())
                filter_document = Q(documentcontainer__isnull=False) & Q(documentcontainer__parent__viewer__in=self.request.user.groups.all())
                self.filter = self.filter & (filter_folder | filter_document)
        else:
            self.curren_item = AbstractContainer()
            lbl.set_value('>')
            self.filter = Q(parent=None)
            if notfree_mode_connect() and not self.request.user.is_superuser:
                filter_folder = Q(foldercontainer__isnull=False) & Q(foldercontainer__viewer__in=self.request.user.groups.all())
                self.filter = self.filter & filter_folder

    def get_items_from_filter(self):
        class ContainerQuerySet(QuerySet):
            def __init__(self, model, *args, initial=[], **kwargs):
                super(ContainerQuerySet, self).__init__(model=model, *args, **kwargs)
                self._result_cache = initial

            def order_by(self, *field_names):
                return self
        order_field = self.getparam(MOSAIC_ORDER + self.field_id, '')
        items = XferListEditor.get_items_from_filter(self)
        if order_field.replace('-', '') == 'datemodif':
            items = ContainerQuerySet(
                model=AbstractContainer,
                initial=sorted(items, key=lambda doc: str(doc.date_modif).lower(), reverse=order_field.startswith('-'))
            )
        return items

    def fill_grid(self, row, model, field_id, items):
        root_document = self.getparam('root', 0)
        mosaic = XferCompMosaic(field_id)
        mosaic.adding_fiedsorder.append(('datemodif', _('date modification')))
        mosaic.set_model(items, self, "image", "indentification", "html_info", "group")
        mosaic.set_location(0, row + 1, 4)
        mosaic.set_height(350)
        mosaic.add_action(self.request, FolderAddModify.get_action(TITLE_CREATE, short_icon='mdi:mdi-folder-plus-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_NONE)
        if folder_notreadonly_condition(self):
            mosaic.add_action(self.request, DocumentAddModify.get_action(TITLE_ADD, short_icon='mdi:mdi-file-plus-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_NONE)
        if file_createnew_condition(self):
            mosaic.add_action(self.request, ContainerAddFile.get_action(_('File'), short_icon='mdi:mdi-file-plus'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_NONE)
        mosaic.add_action(self.request, DocumentDel.get_action(TITLE_DELETE, short_icon='mdi:mdi-file-remove-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_MULTI)
        if self.curren_item.id is not None:
            mosaic.add_action(self.request, FolderAddModify.get_action(TITLE_MODIFY, short_icon='mdi:mdi-folder-edit'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_NONE, params={'folder': self.curren_item.id, 'parent': self.curren_item.parent_id})
            if self.curren_item.id != root_document:
                mosaic.add_action(self.request, self.return_action(_('Back'), short_icon='mdi:mdi-folder-arrow-left'), modal=FORMTYPE_REFRESH, close=CLOSE_NO, unique=SELECT_NONE, params={'document': self.curren_item.parent_id if self.curren_item.parent_id is not None else 0})
        mosaic.add_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO, unique=SELECT_SINGLE, group=FolderContainer().get_group())
        mosaic.add_action(self.request, DocumentShow.get_action(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE, group=DocumentContainer().get_group())
        self.add_component(mosaic)


@MenuManage.describ('documents.change_document', FORMTYPE_NOMODAL, 'documents.actions', _('To find a document following a set of criteria.'))
class DocumentSearch(XferSavedCriteriaSearchEditor):
    caption = _("Document search")
    short_icon = 'mdi:mdi-folder-search-outline'
    model = DocumentContainer
    field_id = 'document'
    mode_select = SELECT_SINGLE
    select_class = None

    def fillresponse_search(self):
        XferSavedCriteriaSearchEditor.fillresponse_search(self)
        if notfree_mode_connect() and not self.request.user.is_superuser:
            if self.filter is None:
                self.filter = Q()
            self.filter = self.filter & (Q(parent=None) | Q(parent__viewer__in=self.request.user.groups.all()))

    def fillresponse(self):
        XferSearchEditor.fillresponse(self)
        grid = self.get_components(self.field_id)
        grid.actions = []
        grid.add_action(self.request, DocumentShow.get_action(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline'), close=CLOSE_NO, unique=SELECT_SINGLE)
        if self.select_class is not None:
            grid.add_action(self.request, self.select_class.get_action(_("Select"), short_icon="mdi:mdi-check"), close=CLOSE_YES, unique=self.mode_select, pos_act=0)


@ActionsManage.affect_show(_('delete shared link'), short_icon="mdi:mdi-file-key-outline", condition=lambda xfer: docshow_modify_condition(xfer) and (xfer.item.sharekey is not None))
@ActionsManage.affect_show(_('create shared link'), short_icon="mdi:mdi-file-key-outline", condition=lambda xfer: docshow_modify_condition(xfer) and (xfer.item.sharekey is None))
@MenuManage.describ('documents.add_document')
class DocumentChangeShared(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = 'document'

    def fillresponse(self):
        if not docshow_modify_condition(self):
            raise LucteriosException(IMPORTANT, _("No allow to write!"))
        self.item.change_sharekey(self.item.sharekey is not None)
        self.item.save()


@MenuManage.describ('')
class DownloadFile(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-folder-outline'
    model = DocumentContainer
    field_id = 'document'
    caption = _("Download document")
    methods_allowed = ('GET', 'PUT')

    def request_handling(self, request, *args, **kwargs):
        from django.http.response import StreamingHttpResponse, HttpResponse
        getLogger("lucterios.documents").debug(">> DownloadFile get %s [%s]", request.path, request.user)
        try:
            self._initialize(request, *args, **kwargs)
            fileid = self.getparam('fileid', 0)
            shared = self.getparam('shared', '')
            filename = self.getparam('filename', '')
            try:
                if fileid == 0:
                    doc = DocumentContainer.objects.get(name=filename, sharekey=shared)
                else:
                    doc = DocumentContainer.objects.get(id=fileid, name=filename)
                response = StreamingHttpResponse(doc.content, content_type='application/octet-stream')
                response['Content-Disposition'] = 'attachment; filename=%s' % doc.name
                if hasattr(request, 'session') and hasattr(request.session, 'accessed'):
                    request.session.accessed = False
                if hasattr(request, 'session') and hasattr(request.session, 'modified'):
                    request.session.modified = False
            except DocumentContainer.DoesNotExist:
                getLogger('lucterios.documents.DownloadFile').exception("downloadFile")
                response = HttpResponse(_("File not found !"))
            return response
        finally:
            getLogger("lucterios.documents").debug("<< DownloadFile get %s [%s]", request.path, request.user)


@MenuManage.describ('')
class UploadFile(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-folder-outline'
    field_id = 'document'
    caption = "document"

    def request_handling(self, request, *args, **kwargs):
        getLogger("lucterios.documents").debug(">> UploadFile get %s [%s]", request.path, request.user)
        try:
            from lucterios.documents.doc_editors import OnlyOfficeEditor
            from django.http.response import JsonResponse
            self._initialize(request, *args, **kwargs)
            doc = DocumentContainer.objects.get(id=self.getparam('fileid', 0), name=self.getparam('filename', ''))
            editor = OnlyOfficeEditor(get_url_from_request(request), doc)
            responsejson = editor.uploadFile(request.body)
            return JsonResponse(responsejson, json_dumps_params={'indent': 3})
        finally:
            getLogger("lucterios.documents").debug("<< UploadFile get %s [%s]", request.path, request.user)


def file_check_permission(file_id, request):
    from django.http.response import HttpResponse, HttpResponseNotFound
    can_write = False
    user = None
    try:
        doc = DocumentContainer.objects.get(id=file_id)
    except (ValueError, ObjectDoesNotExist):
        return HttpResponseNotFound(f"File id {file_id} no found".encode())
    if ('access_token' not in request.GET) or (request.GET['access_token'].count('-') != 1):
        return HttpResponse(b"token invalid: no token", status=401)
    user_id, date_timestamp = request.GET['access_token'].split('-')
    user_id = int(user_id)
    if str(doc.date_modification.timestamp()) != date_timestamp:
        return HttpResponse(b"token invalid: timestamp", status=401)
    if user_id == 0:
        if notfree_mode_connect():
            return HttpResponse(b"token invalid: unsecure", status=401)
        else:
            can_write = True
    else:
        try:
            user = LucteriosUser.objects.get(id=user_id)
        except ObjectDoesNotExist:
            return HttpResponse(b"token invalid: user unknown", status=401)
        if (doc.parent is not None) and doc.parent.cannot_view(user):
            return HttpResponse(b"token invalid: no permission", status=401)
        can_write = (doc.parent is None) or not doc.parent.is_readonly(user)
    return doc, can_write, user


@require_GET
def check_file_info(request, file_id):
    from django.http.response import JsonResponse, HttpResponseBase, HttpResponseServerError
    getLogger("lucterios.documents").debug(f"Check file: file id: {file_id}")
    try:
        perm_res = file_check_permission(file_id, request)
        if isinstance(perm_res, HttpResponseBase):
            return perm_res
        doc, can_write, user = perm_res
        res = {
            'BaseFileName': doc.name,
            'Size': len(doc.content.read()),
            'UserId': str(user.id) if user is not None else '0',
            'OwnerId': str(doc.creator.id) if doc.creator is not None else '0',
            'UserCanWrite': can_write,
            'UserFriendlyName': str(user) if user is not None else '---',
            'HidePrintOption': False,
            'DisablePrint': False,
            'HideSaveOption': False,
            'HideExportOption': True,
            'DisableExport': True,
            'DisableCopy': True,
            'EnableOwnerTermination': False,
            'LastModifiedTime': doc.date_modification.isoformat(),
            'IsUserLocked': False,
            'IsUserRestricted': False,
        }
        return JsonResponse(res)
    except Exception:
        getLogger("lucterios.documents").exception("check_file_info failure!!!")
        return HttpResponseServerError()


class FileContentView(View):

    @staticmethod
    def get(request, file_id):
        from django.http.response import HttpResponse, HttpResponseBase, HttpResponseServerError
        getLogger("lucterios.documents").info(f"GetFile: file id: {file_id}, access token: {request.GET['access_token']}")
        try:
            perm_res = file_check_permission(file_id, request)
            if isinstance(perm_res, HttpResponseBase):
                return perm_res
            doc, _can_write, _user_id = perm_res
            return HttpResponse(doc.content.read())
        except Exception:
            getLogger("lucterios.documents").exception("FileContentView get failure!!!")
            return HttpResponseServerError()

    @staticmethod
    def post(request, file_id):
        from django.http.response import HttpResponse, HttpResponseBase, HttpResponseNotFound, HttpResponseServerError
        getLogger("lucterios.documents").info(f"PutFile: file id: {file_id}, access token: {request.GET['access_token']}")
        if not request.body:
            return HttpResponseNotFound(b'Not possible to get the file content.')
        try:
            perm_res = file_check_permission(file_id, request)
            if isinstance(perm_res, HttpResponseBase):
                return perm_res
            doc, _can_write, _user_id = perm_res
            doc.content = request.read()
            return HttpResponse()  # status 200
        except Exception:
            getLogger("lucterios.documents").exception("FileContentView post failure!!!")
            return HttpResponseServerError()


@signal_and_lock.Signal.decorate('summary')
def summary_documents(xfer):
    if not hasattr(xfer, 'add_component'):
        return WrapAction.is_permission(xfer, 'documents.change_document')
    elif WrapAction.is_permission(xfer.request, 'documents.change_document'):
        row = xfer.get_max_row() + 1
        lab = XferCompLabelForm('documenttitle')
        lab.set_value_as_infocenter(_('Document management'))
        lab.set_location(0, row, 4)
        xfer.add_component(lab)
        filter_result = Q()
        if notfree_mode_connect():
            filter_result = filter_result & (Q(parent=None) | Q(parent__viewer__in=xfer.request.user.groups.all() if xfer.request.user.id is not None else []))
        nb_doc = len(DocumentContainer.objects.filter(*[filter_result]))
        lbl_doc = XferCompLabelForm('lbl_nbdocument')
        lbl_doc.set_location(0, row + 1, 4)
        if nb_doc == 0:
            lbl_doc.set_value_center(_("no file currently available"))
        elif nb_doc == 1:
            lbl_doc.set_value_center(_("one file currently available"))
        else:
            lbl_doc.set_value_center(_("%d files currently available") % nb_doc)
        xfer.add_component(lbl_doc)
        lab = XferCompLabelForm('documentend')
        lab.set_value_center('{[hr/]}')
        lab.set_location(0, row + 2, 4)
        xfer.add_component(lab)
        return True
    else:
        return False


@signal_and_lock.Signal.decorate('get_url_patterns')
def get_url_patterns(url_patterns):
    from django.urls import re_path
    url_patterns.append(re_path(r'^lucterios.documents/files/(.*)/contents', FileContentView.as_view()))
    url_patterns.append(re_path(r'^lucterios.documents/files/(.*)', check_file_info))
    return True


@signal_and_lock.Signal.decorate('conf_wizard')
def conf_wizard_document(wizard_ident, xfer):
    if isinstance(wizard_ident, list) and (xfer is None):
        wizard_ident.append(("document_params", 55))
    elif (xfer is not None) and (wizard_ident == "document_params"):
        xfer.add_title(_("Lucterios documents"), _("Parameters"))
        lbl = XferCompLabelForm("nb_folder")
        lbl.set_location(1, xfer.get_max_row() + 1)
        lbl.set_value(TEXT_TOTAL_NUMBER % {'name': FolderContainer._meta.verbose_name_plural, 'count': len(FolderContainer.objects.all())})
        xfer.add_component(lbl)
        lbl = XferCompLabelForm("nb_doc")
        lbl.set_location(1, xfer.get_max_row() + 1)
        lbl.set_value(TEXT_TOTAL_NUMBER % {'name': DocumentContainer._meta.verbose_name_plural, 'count': len(DocumentContainer.objects.all())})
        xfer.add_component(lbl)
        btn = XferCompButton("btnconf")
        btn.set_location(4, xfer.get_max_row() - 1, 1, 2)
        btn.set_action(xfer.request, FolderList.get_action(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline'), close=CLOSE_NO)
        xfer.add_component(btn)
