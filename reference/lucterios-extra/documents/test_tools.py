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
from os.path import join, dirname
from zipfile import ZipFile
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs

from django.utils import timezone

from lucterios.framework.filetools import get_user_path

from lucterios.CORE.models import LucteriosGroup

from lucterios.documents.models import FolderContainer, DocumentContainer
from lucterios.framework.test import add_empty_user


def create_doc(user, with_folder=True):
    root_path = join(dirname(__file__), 'docs', 'fr')
    current_date = timezone.now()
    new_doc1 = DocumentContainer.objects.create(name='doc1.png', description="doc 1", creator=user,
                                                date_creation=current_date, date_modification=current_date)
    if with_folder:
        new_doc1.parent = FolderContainer.objects.get(id=2)
    new_doc1.save()
    with ZipFile(get_user_path('documents', 'container_%d' % new_doc1.id), 'w') as zip_ref:
        zip_ref.write(join(root_path, 'configuration.png'), arcname='doc1.png')

    new_doc2 = DocumentContainer.objects.create(name='doc2.png', description="doc 2", creator=user,
                                                date_creation=current_date, date_modification=current_date)
    if with_folder:
        new_doc2.parent = FolderContainer.objects.get(id=1)
    new_doc2.save()
    with ZipFile(get_user_path('documents', 'container_%d' % new_doc2.id), 'w') as zip_ref:
        zip_ref.write(join(root_path, 'listdoc.png'), arcname='doc2.png')

    new_doc3 = DocumentContainer.objects.create(name='doc3.png', description="doc 3", creator=user,
                                                date_creation=current_date, date_modification=current_date)
    if with_folder:
        new_doc3.parent = FolderContainer.objects.get(id=4)
    new_doc3.save()
    with ZipFile(get_user_path('documents', 'container_%d' % new_doc3.id), 'w') as zip_ref:
        zip_ref.write(join(root_path, 'showdoc.png'), arcname='doc3.png')
    return current_date


def default_groups():
    group = LucteriosGroup.objects.create(name="my_group")
    group.save()
    group = LucteriosGroup.objects.create(name="other_group")
    group.save()
    current_user = add_empty_user()
    current_user.is_superuser = False
    current_user.save()
    return current_user


def default_folders():
    folder1 = FolderContainer.objects.create(name='truc1', description='blabla')
    folder1.viewer.set(LucteriosGroup.objects.filter(id__in=[1, 2]))
    folder1.modifier.set(LucteriosGroup.objects.filter(id__in=[1]))
    folder1.save()
    folder2 = FolderContainer.objects.create(name='truc2', description='bouuuuu!')
    folder2.viewer.set(LucteriosGroup.objects.filter(id__in=[2]))
    folder2.modifier.set(LucteriosGroup.objects.filter(id__in=[2]))
    folder2.save()
    folder3 = FolderContainer.objects.create(name='truc3', description='----')
    folder3.parent = folder2
    folder3.viewer.set(LucteriosGroup.objects.filter(id__in=[2]))
    folder3.save()
    folder4 = FolderContainer.objects.create(name='truc4', description='no')
    folder4.parent = folder2
    folder4.save()


class TestHTTPServer(HTTPServer, BaseHTTPRequestHandler, Thread):

    def __init__(self, server_address):
        HTTPServer.__init__(self, server_address, TestMoke)
        Thread.__init__(self, target=self.serve_forever)


class TestMoke(BaseHTTPRequestHandler):

    results = []
    requests = []
    content_type = "text/plain"

    @classmethod
    def initial(cls, results):
        cls.results = results
        cls.requests = []

    def do_GET(self):
        """Respond to a GET request."""
        TestMoke.requests.append(self.path)
        self.response()

    def do_DELETE(self):
        """Respond to a DELETE request."""
        TestMoke.requests.append(('DELETE', self.path))
        self.response()

    def get_request_fields(self):
        from cgi import parse_header, parse_multipart
        ctype, pdict = parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            requestvars = parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            requestvars = parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            requestvars = {}
        request_field = {}
        for key, value in requestvars.items():
            if isinstance(value, bytes):
                value = value.decode()
            elif isinstance(value, list):
                value = [item.decode() for item in value]
            request_field[key.decode()] = value
        return request_field

    def do_POST(self):
        """Respond to a POST request."""
        post_field = self.get_request_fields()
        TestMoke.requests.append((self.path, post_field))
        self.response()

    def do_PUT(self):
        """Respond to a PUT request."""
        put_field = self.get_request_fields()
        TestMoke.requests.append(('PUT', self.path, put_field))
        self.response()

    def response(self):
        self.send_response(200)
        self.send_header("Content-type", self.content_type)
        self.end_headers()
        if len(TestMoke.results) > 0:
            self.wfile.write(TestMoke.results[0].encode())
            del TestMoke.results[0]
        else:
            self.wfile.write(b'')
