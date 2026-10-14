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
from os.path import isfile

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework.tools import ActionsManage, CLOSE_NO, FORMTYPE_MODAL
from lucterios.framework.xfercomponents import XferCompUpLoad, XferCompDownLoad, XferCompEdit
from lucterios.framework.editors import LucteriosEditor

from lucterios.CORE.models import LucteriosUser
from lucterios.documents.models import FolderContainer


class DocumentContainerEditor(LucteriosEditor):

    def before_save(self, xfer):
        current_folder = xfer.getparam('current_folder')
        if (current_folder is not None) and (self.item.parent_id is None):
            current_folder = int(current_folder)
            if current_folder != 0:
                self.item.folder = FolderContainer.objects.get(id=current_folder)
            else:
                self.item.folder = None
        if xfer.getparam('filename_FILENAME') is not None:
            self.item.name = xfer.getparam('filename_FILENAME')
        if (self.item.creator is None) and xfer.request.user.is_authenticated:
            self.item.creator = LucteriosUser.objects.get(pk=xfer.request.user.id)
        if xfer.request.user.is_authenticated:
            self.item.modifier = LucteriosUser.objects.get(pk=xfer.request.user.id)
        else:
            self.item.modifier = None
        self.item.date_modification = timezone.now()
        if self.item.id is None:
            self.item.date_creation = self.item.date_modification
        return

    def saving(self, xfer):
        if 'filename' in xfer.request.FILES.keys():
            tmp_file = xfer.request.FILES['filename']
            self.item.content = tmp_file
        elif not isfile(xfer.item.file_path):
            raise LucteriosException(IMPORTANT, _("File not found!"))

    def edit(self, xfer):
        obj_cmt = xfer.get_components('name')
        xfer.remove_component('name')
        file_name = XferCompUpLoad('filename')
        file_name.http_file = True
        file_name.maxsize = 64 * 1024 * 1024  # 64Mo
        file_name.compress = True
        file_name.set_value('')
        file_name.set_location(obj_cmt.col, obj_cmt.row, obj_cmt.colspan, obj_cmt.rowspan)
        xfer.add_component(file_name)
        if self.item.id is None:
            xfer.change_to_readonly('parent')
        else:
            obj_folder = xfer.get_components('parent')
            obj_folder.set_needed(False)
            obj_folder.select_list.sort(key=lambda item: str(item[1]))

    def show(self, xfer):
        obj_cmt = xfer.get_components('creator')
        down = XferCompDownLoad('filename')
        down.compress = True
        down.http_file = True
        down.maxsize = 0
        down.set_value(self.item.name)
        down.set_download(self.item.file_path)
        down.set_action(xfer.request, ActionsManage.get_action_url('documents.DocumentContainer', 'AddModify', xfer),
                        modal=FORMTYPE_MODAL, close=CLOSE_NO)
        down.set_location(obj_cmt.col, obj_cmt.row + 1, 4)
        xfer.add_component(down)
        link = self.item.shared_link
        if link is not None:
            shared_link = XferCompEdit('shared_link')
            shared_link.description = _('shared link')
            shared_link.set_value(link)
            shared_link.set_location(obj_cmt.col, obj_cmt.row + 2, 4)
            xfer.add_component(shared_link)
