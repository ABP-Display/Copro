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
from os import unlink
from os.path import isfile
from zipfile import ZipFile

from django.db import models
from django.utils.translation import gettext_lazy as _

from lucterios.framework.models import LucteriosModel
from lucterios.framework.filetools import get_user_path
from lucterios.CORE.models import LucteriosGroup, LucteriosUser


class Folder(LucteriosModel):
    name = models.CharField(_('name'), max_length=250, blank=False)
    description = models.TextField(_('description'), blank=False)
    parent = models.ForeignKey('Folder', verbose_name=_('parent'), null=True, on_delete=models.CASCADE)
    viewer = models.ManyToManyField(LucteriosGroup, related_name="folder_viewer", verbose_name=_('viewer'), blank=True)
    modifier = models.ManyToManyField(LucteriosGroup, related_name="folder_modifier", verbose_name=_('modifier'), blank=True)

    def delete(self):
        file_paths = []
        docs = self.document_set.all()
        for doc in docs:
            file_paths.append(get_user_path("documents", "document_%s" % str(doc.id)))
        LucteriosModel.delete(self)
        for file_path in file_paths:
            if isfile(file_path):
                unlink(file_path)

    # DEPRECATED MODEL

    class Meta(object):
        verbose_name = _('folder')
        verbose_name_plural = _('folders')
        ordering = ['parent__name', 'name']


class Document(LucteriosModel):
    folder = models.ForeignKey('Folder', verbose_name=_('folder'), null=True, on_delete=models.CASCADE)
    name = models.CharField(_('name'), max_length=250, blank=False)
    description = models.TextField(_('description'), blank=False)
    modifier = models.ForeignKey(LucteriosUser, related_name="document_modifier", verbose_name=_('modifier'), null=True, on_delete=models.CASCADE)
    date_modification = models.DateTimeField(verbose_name=_('date modification'), null=False)
    creator = models.ForeignKey(LucteriosUser, related_name="document_creator", verbose_name=_('creator'), null=True, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(verbose_name=_('date creation'), null=False)
    sharekey = models.CharField('sharekey', max_length=100, null=True)

    @property
    def content(self):
        from _io import BytesIO
        file_path = get_user_path("documents", "document_%s" % str(self.id))
        if isfile(file_path):
            with ZipFile(file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                if len(file_list) > 0:
                    doc_file = zip_ref.open(file_list[0])
                    return BytesIO(doc_file.read())
        return BytesIO(b'')

    # DEPRECATED MODEL

    class Meta(object):
        verbose_name = _('document')
        verbose_name_plural = _('documents')
        ordering = ['folder__name', 'name']
