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
from os.path import join, dirname, isfile
from hashlib import md5
from urllib.error import URLError
from urllib import request
from urllib.parse import urlencode
from requests.exceptions import ConnectionError
from logging import getLogger
from lxml import etree
from json import dumps, loads

from django.conf import settings
from django.utils import timezone

from etherpad_lite import EtherpadLiteClient, EtherpadException

from lucterios.documents.ethercalc import EtherCalc
from lucterios.framework.error import LucteriosException, IMPORTANT


class DocEditor(object):

    SETTING_NAME = "XXX"

    def __init__(self, root_url, doccontainer, readonly=False, user=None):
        self.root_url = root_url
        self.doccontainer = doccontainer
        self._readonly = readonly
        self.user = user
        self.username = user.get_full_name() if (user is not None) and hasattr(user, 'get_full_name') else '???'
        self._client = None
        if hasattr(settings, self.SETTING_NAME):
            self.editorParams = getattr(settings, self.SETTING_NAME)
        else:
            self.editorParams = None

    @classmethod
    def get_all_editor(cls):
        def all_subclasses(cls):
            return set(cls.__subclasses__()).union([subclass_item for class_item in cls.__subclasses__() for subclass_item in all_subclasses(class_item)])
        return all_subclasses(cls)

    @classmethod
    def get_all_extension_supported(cls):
        res = []
        for cls in cls.get_all_editor():
            if hasattr(settings, cls.SETTING_NAME):
                for extitem in cls.extension_rw_supported():
                    if extitem not in res:
                        res.append(extitem)
        return res

    @classmethod
    def extension_rw_supported(cls):
        return ()

    @classmethod
    def extension_ro_supported(cls):
        return ()

    @property
    def readonly(self):
        return self._readonly

    @property
    def withSaveBtn(self):
        return not self.readonly

    @property
    def docid(self):
        md5res = md5()
        md5res.update(self.root_url.encode())
        return '%s-%d' % (md5res.hexdigest(), self.doccontainer.id)

    def is_manage(self):
        if self.doccontainer is not None:
            if hasattr(settings, self.SETTING_NAME):
                for ext_item in self.extension_rw_supported():
                    if self.doccontainer.name.endswith('.' + ext_item):
                        return True
                if self.readonly:
                    for ext_item in self.extension_ro_supported():
                        if self.doccontainer.name.endswith('.' + ext_item):
                            return True
        return False

    @property
    def client(self):
        return self._client

    def get_iframe(self):
        return "{[iframe]}{[/iframe]}"

    def send_content(self):
        pass

    def get_empty(self):
        self.doccontainer.content = ""

    def save_content(self):
        pass

    def close(self):
        pass


def disabled_ssl():
    def decorator(fn):
        def wrapper(*args, **kw):
            request._opener = EtherPadEditor.OPENER
            try:
                return fn(*args, **kw)
            finally:
                request._opener = None
        return wrapper
    return decorator


class EtherPadEditor(DocEditor):

    SETTING_NAME = "ETHERPAD"

    OPENER = None

    @classmethod
    def init_no_ssl(cls):
        from ssl import create_default_context
        from _ssl import CERT_NONE
        no_check_ssl = create_default_context()
        no_check_ssl.check_hostname = False
        no_check_ssl.verify_mode = CERT_NONE
        EtherPadEditor.OPENER = request.build_opener(request.HTTPSHandler(context=no_check_ssl))

    @classmethod
    def extension_rw_supported(cls):
        if hasattr(settings, 'ETHERPAD') and ('url' in settings.ETHERPAD) and ('apikey' in settings.ETHERPAD):
            try:
                cls('', None).check_token()
                return ('txt', 'html')
            except (URLError, EtherpadException) as con_err:
                getLogger('lucterios.documents').debug('extension_rw_supported error=%s', con_err)
        return ()

    @property
    def client(self):
        if self._client is None:
            self._client = EtherpadLiteClient(base_url='%s/api' % self.editorParams['url'], api_version='1.2.14',
                                              base_params={'apikey': self.editorParams['apikey']})
        return self._client

    def get_iframe(self):
        return '{[iframe name="embed_readwrite" src="%s/p/%s" width="100%%" height="450"]}{[/iframe]}' % (self.editorParams['url'], self.docid)

    @disabled_ssl()
    def check_token(self):
        return self.client.checkToken()

    @disabled_ssl()
    def close(self):
        if self.docid in self.client.listAllPads()['padIDs']:
            self.client.deletePad(padID=self.docid)

    @disabled_ssl()
    def send_content(self):
        pad_ids = self.client.listAllPads()['padIDs']
        if not (self.docid in pad_ids):
            self.client.createPad(padID=self.docid, padName=self.doccontainer.name)
        file_ext = self.doccontainer.name.split('.')[-1]

        content = self.doccontainer.content.read()
        if content != b'':
            if file_ext == 'html':
                self.client.setHTML(padID=self.docid, html=content.decode())
            else:
                self.client.setText(padID=self.docid, text=content.decode())

    @disabled_ssl()
    def load_export(self, export_type):
        url = "%s/p/%s/export/%s" % (self.editorParams['url'], self.docid, export_type)
        return request.urlopen(url, timeout=self.client.timeout).read()

    @disabled_ssl()
    def save_content(self):
        file_ext = self.doccontainer.name.split('.')[-1]
        if file_ext == 'txt':
            self.doccontainer.content = self.client.getText(padID=self.docid)['text']
        elif file_ext == 'html':
            self.doccontainer.content = self.client.getHTML(padID=self.docid)['html']
        else:
            self.doccontainer.content = self.load_export(file_ext)


if EtherPadEditor.OPENER is None:
    EtherPadEditor.init_no_ssl()


class EtherCalcEditor(DocEditor):

    SETTING_NAME = "ETHERCALC"

    @classmethod
    def extension_rw_supported(cls):
        if hasattr(settings, 'ETHERCALC') and ('url' in settings.ETHERCALC):
            try:
                cls('', None).client.get('')
                return ('csv', 'xlsx', 'ods')
            except ConnectionError as con_err:
                getLogger('lucterios.documents').debug('extension_rw_supported error=%s', con_err)
        return ()

    @property
    def client(self):
        if self._client is None:
            self._client = EtherCalc(url_root='%s' % self.editorParams['url'])
        return self._client

    def get_iframe(self):
        return '{[iframe name="embed_readwrite" src="%s/%s" width="100%%" height="450"]}{[/iframe]}' % (self.editorParams['url'], self.docid)

    def send_content(self):
        file_ext = self.doccontainer.name.split('.')[-1]
        if not self.client.is_exist(self.docid):
            self.client.new(self.docid)
        content = self.doccontainer.content.read()
        if content != b'':
            self.client.update(content, file_ext, self.docid)

    def close(self):
        if self.client.is_exist(self.docid):
            self.client.delete(self.docid)

    def save_content(self):
        if self.client.is_exist(self.docid):
            file_ext = self.doccontainer.name.split('.')[-1]
            self.doccontainer.content = self.client.export(self.docid, file_ext)


class OnlyOfficeEditor(DocEditor):

    SETTING_NAME = "ONLYOFFICE"

    @classmethod
    def extension_rw_supported(cls):
        if hasattr(settings, 'ONLYOFFICE') and ('url' in settings.ONLYOFFICE):
            return ('csv', 'xlsx', 'ods', 'docx', 'odt', 'txt', 'pptx', 'odp')
        else:
            return ()

    @classmethod
    def extension_ro_supported(cls):
        if hasattr(settings, 'ONLYOFFICE') and ('url' in settings.ONLYOFFICE):
            return ('xls', 'doc', 'ppt', 'pdf')
        else:
            return ()

    @property
    def withSaveBtn(self):
        return False

    @property
    def docid(self):
        doc_id = super().docid
        return "%s-%d" % (doc_id, self.doccontainer.date_modification.timestamp())

    @property
    def url_params(self):
        return urlencode({'filename': self.doccontainer.name, 'fileid': self.doccontainer.id})

    @property
    def doc_url(self):
        return "%s/lucterios.documents/downloadFile?%s" % (self.root_url, self.url_params)

    @property
    def editor_option(self):
        extension = str(self.doccontainer.name.split('.')[-1])
        if extension in ('csv', 'xlsx', 'ods', 'xls'):
            documentType = "cell"
        elif extension in ('docx', 'odt', 'txt', 'doc', 'pdf'):
            documentType = "word"
        elif extension in ('pptx', 'odp', 'ppt'):
            documentType = "slide"
        else:
            raise LucteriosException(IMPORTANT, 'Invalid format !')
        option = {"width": "100%", "height": "830px", 'type': "embedded", 'documentType': documentType}
        option['document'] = {
            'fileType': extension,
            'key': self.docid,
            "title": self.doccontainer.name,
            'url': self.doc_url,
            'info': {'folder': self.doccontainer.parent.name if self.doccontainer.parent is not None else ""}
        }
        lang = settings.LANGUAGE_CODE
        option['editorConfig'] = {
            "callbackUrl": "" if self.readonly else "%s/lucterios.documents/uploadFile?%s" % (self.root_url, self.url_params),
            'lang': lang,
            'mode': 'view' if self.readonly else 'edit',
            'region': '%s-%s' % (lang, lang.upper()),
            "customization": {
                'autosave': False,
                'chat': False,
                'comments': False,
                'commentAuthorOnly': False,
                "customer": {
                    "name": "Diacamma",
                    "info": "Diacamma",
                    "www": "https://www.diacamma.org"
                }
            },
            "user": {
                "name": self.username
            }
        }
        return option

    def get_iframe(self):
        option_json = dumps(self.editor_option, indent=2)
        return """
{[div id="iframeEditor-%(id)s"]}{[/div]}
{[script type="text/javascript"]}
    var docEditor, script, parent_id, resizefct;
    resizefct = function() {
        $("#"+parent_id+"_frame iframe:first").attr('height', ($("#"+parent_id).height()-25).toString()+"px");
    };
    if (docEditor!==undefined) {
        docEditor.destroyEditor()
    }
    script = document.createElement('script');
    script.onload = function () {
        parent_id = $("#iframeEditor-%(id)s:first").parent().attr('id').split("_")[0];
        docEditor = new DocsAPI.DocEditor("iframeEditor-%(id)s", %(option)s);
        resizefct();
        $("#"+parent_id).parent().resize(resizefct);
    };
    script.src = '%(url)s/web-apps/apps/api/documents/api.js';
    document.head.appendChild(script);
{[/script]}
""" % {'id': self.docid, 'url': self.editorParams['url'], 'option': option_json}

    def send_content(self):
        pass

    def close(self):
        pass

    def save_content(self):
        pass

    def _convert_download_url(self, download_extension, expected_extension):
        from requests import get
        convert_params = {"async": True,
                          "codePage": 65001,
                          "delimiter": 2,
                          "filetype": download_extension,
                          "key": self.info_body['key'] + '_convert',
                          "outputtype": expected_extension,
                          "url": self.doc_url}
        convert_res = loads(get("%s/ConvertService.ashx" % self.editorParams['url'], params=convert_params, verify=False, headers={'accept': 'application/json'}).content.decode())
        if 'error' in convert_res:
            raise Exception(str(convert_res['error']))
        return convert_res['fileUrl']

    def _get_download_url(self):
        from requests import get
        from urllib.parse import parse_qs, urlparse
        download_url = self.info_body['url']
        download_url_params = parse_qs(urlparse(download_url).query)
        download_extension = download_url_params['ooname'][0].split('.')[-1]
        expected_extension = self.doccontainer.name.split('.')[-1]
        if expected_extension == download_extension:
            return download_url
        else:
            self.doccontainer.content = get(download_url, verify=False).content
            return self._convert_download_url(download_extension, expected_extension)

    def uploadFile(self, info_body):
        from requests import get
        try:
            self.info_body = loads(info_body.decode())
            if self.info_body['status'] == 2:
                old_content = self.doccontainer.content
                try:
                    self.doccontainer.content = get(self._get_download_url(), verify=False).content
                    self.doccontainer.date_modification = timezone.now()
                    self.doccontainer.save()
                except Exception:
                    self.doccontainer.content = old_content
                    raise
            responsejson = {'error': 0}
        except Exception as error:
            getLogger('lucterios.plugin').exception("uploadfile")
            responsejson = {'error': str(error)}
        return responsejson

    def get_empty(self):
        extension = str(self.doccontainer.name.split('.')[-1])
        if extension in ('csv', 'xlsx', 'ods'):
            default_filename = "new.xlsx"
        elif extension in ('docx', 'odt', 'txt'):
            default_filename = "new.docx"
        elif extension in ('pptx', 'odp'):
            default_filename = "new.pptx"
        else:
            default_filename = "new.unknown"
        filename_path = join(dirname(__file__), 'assets', default_filename)
        if isfile(filename_path):
            with open(filename_path, 'rb') as filehdl:
                self.doccontainer.content = filehdl.read()
        else:
            raise LucteriosException(IMPORTANT, 'Invalid format !')


class CollaboraEditor(DocEditor):

    SETTING_NAME = "COLLABORA"

    @classmethod
    def extension_rw_supported(cls):
        if hasattr(settings, 'COLLABORA') and ('url' in settings.COLLABORA):
            return ('csv', 'xlsx', 'ods', 'docx', 'odt', 'txt', 'pptx', 'odp')
        else:
            return ()

    @classmethod
    def extension_ro_supported(cls):
        if hasattr(settings, 'COLLABORA') and ('url' in settings.COLLABORA):
            return ('xls', 'doc', 'ppt', 'pdf', "jpeg", "jpg", "gif", "png", "bmp")
        else:
            return ()

    @property
    def withSaveBtn(self):
        return False

    @property
    def doc_url(self):
        return "%s/lucterios.documents/files/%s" % (self.root_url, self.doccontainer.id)

    @property
    def access_token(self):
        return "%d-%s" % (self.user.id if self.user is not None else 0, self.doccontainer.date_modification.timestamp())

    @property
    def collabora_url(self):
        from requests import get
        extension = str(self.doccontainer.name.split('.')[-1])
        if extension in ('csv', 'xlsx', 'ods', 'xls'):
            mime_type = "calc"
        elif extension in ('docx', 'odt', 'txt', 'doc', 'pdf'):
            mime_type = "writer"
        elif extension in ('pptx', 'odp', 'ppt'):
            mime_type = "impress"
        elif extension in ('pdf', "jpeg", "jpg", "gif", "png", "bmp"):
            mime_type = "draw"
        else:
            raise LucteriosException(IMPORTANT, 'Invalid format !')
        response = get(self.editorParams['url'] + '/hosting/discovery', verify=False)
        discovery = response.text
        if not discovery:
            raise LucteriosException(IMPORTANT, 'No able to retrieve the discovery.xml file from the Collabora Online server with the submitted address.')
        getLogger("lucterios.document").debug(discovery)
        parsed = etree.fromstring(discovery)
        if parsed is None:
            raise LucteriosException(IMPORTANT, 'The retrieved discovery.xml file is not a valid XML file')
        result = parsed.xpath(f"/wopi-discovery/net-zone/app[@name='{mime_type}']/action")
        if len(result) == 1:
            raise LucteriosException(IMPORTANT, 'The requested mime type is not handled')
        online_url = result[0].get('urlsrc')
        if online_url.startswith(self.editorParams['url']):
            base_url = '/'.join(online_url.split('/')[:3])
            if self.editorParams['url'].startswith(base_url):
                online_url = online_url.replace(base_url, self.editorParams['url'][len(base_url):])
        return online_url

    def get_iframe(self):
        return """
{[div style="display: none"]}
  {[form action="%(collabora_url)sWOPISrc=%(url)s" enctype="multipart/form-data" method="post" target="iframeCollabora" id="collabora-submit-form" name="collabora-submit-form"]}
    {[input name="access_token" value="%(access_token)s" type="hidden" id="access-token"/]}
    {[button id="collabora-button" type="submit" value="show" /]}
  {[/form]}
{[/div]}
{[iframe id="iframeCollabora" name="iframeCollabora" style="width:98%%;height:91%%;position:absolute;"]}{[/iframe]}
{[script type="text/javascript"]}
    function refresh_collabora() {
        var btnElem = document.getElementById("collabora-button");
        if (!btnElem) {
            console.log('error: button not found');
        } else {
            console.log('loading ... ' + btnElem.value);
            btnElem.click();
        }
    }
    refresh_collabora();
    setTimeout(refresh_collabora, 100);
{[/script]}
""" % {'collabora_url': self.collabora_url, 'url': self.doc_url, 'access_token': self.access_token}

    def send_content(self):
        pass

    def close(self):
        pass

    def save_content(self):
        pass

    def uploadFile(self, info_body):
        from requests import get
        try:
            self.info_body = loads(info_body.decode())
            if self.info_body['status'] == 2:
                old_content = self.doccontainer.content
                try:
                    self.doccontainer.content = get(self._get_download_url(), verify=False).content
                    self.doccontainer.date_modification = timezone.now()
                    self.doccontainer.save()
                except Exception:
                    self.doccontainer.content = old_content
                    raise
            responsejson = {'error': 0}
        except Exception as error:
            getLogger('lucterios.plugin').exception("uploadfile")
            responsejson = {'error': str(error)}
        return responsejson

    def get_empty(self):
        extension = str(self.doccontainer.name.split('.')[-1])
        if extension in ('xlsx', ):
            default_filename = "new.xlsx"
        elif extension in ('docx', ):
            default_filename = "new.docx"
        elif extension in ('pptx', ):
            default_filename = "new.pptx"
        else:
            default_filename = "new.unknown"
        filename_path = join(dirname(__file__), 'assets', default_filename)
        if isfile(filename_path):
            with open(filename_path, 'rb') as filehdl:
                self.doccontainer.content = filehdl.read()
        else:
            self.doccontainer.content = b''
