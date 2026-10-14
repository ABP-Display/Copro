'''
Created on 2026 Jun 29

@author: lag
'''
from requests import request
from abc import ABC
from requests.exceptions import HTTPError
from datetime import datetime
import json

from django.utils.translation import gettext_lazy as _
from lucterios.CORE.parameters import Params

DEFAULT_CONFIG = [
    {"id": 0, 'name': None, 'flow_url': '', "directory_url": "", 'auth_url': ''},
    {"id": -1, 'name': _('Customize'), 'flow_url': '', "directory_url": "", 'auth_url': ''},
    {"id": 1, 'name': "SuperPDP", 'flow_url': 'https://api.superpdp.tech/afnor-flow', "directory_url": "https://api.superpdp.tech/afnor-directory", 'auth_url': 'https://api.superpdp.tech/oauth2/token'}
]


def extract_config(config_id):
    for default_item in DEFAULT_CONFIG:
        if default_item['id'] == config_id:
            return {'flow_url': default_item['flow_url'], 'auth_url': default_item['auth_url'], "directory_url": default_item['directory_url']}
    return {}


def get_einvoice_config(xfer=None):
    config = json.loads(Params.getvalue('accounting-einvoicing-conf'))
    if xfer is not None:
        type_changed = xfer.getparam("einvoice_type") != config.get("einvoice_type")
        config = {
            "einvoice_type": xfer.getparam("einvoice_type", config.get("einvoice_type", 0)),
            "flow_url": xfer.getparam("flow_url", config.get("flow_url", "")),
            "directory_url": xfer.getparam("directory_url", config.get("directory_url", "")),
            "auth_url": xfer.getparam("auth_url", config.get("auth_url", "")),
            "client_id": xfer.getparam("client_id", config.get("client_id", "")),
            "secret_id": xfer.getparam("secret_id", config.get("secret_id", "")),
        }
    else:
        type_changed = False
    return config, type_changed


def get_einvoicing_flow(xfer=None):
    config, _changed = get_einvoice_config(xfer)
    return EInvoicingFlow(**config)


def get_einvoicing_directory(xfer=None):
    config, _changed = get_einvoice_config(xfer)
    return EInvoicingDirectory(**config)


class EInvoicingAbstract(ABC):

    http_timeout = 30

    def __init__(self, base_url, auth_url, client_id, secret_id, **kwarg):
        self.base_url = base_url
        self.auth_url = auth_url
        self.client_id = client_id
        self.secret_id = secret_id
        self._access_token = None

    @property
    def access_token(self):
        if self._access_token is None:
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.secret_id,
            }
            response = request("POST", self.auth_url, data=data)
            response.raise_for_status()
            payload = response.json()
            self._access_token = payload.get("access_token")
        return self._access_token

    def invalidate_token(self):
        self._access_token = None

    def get_headers(self):
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        return headers

    def _request(self, method, path, params=None, json=None, data=None, files=None, retry_on_401=True, raise_error=True):
        try:
            url = f"{self.base_url}{path}"
            headers = self.get_headers()
            if json is not None and files is None:
                headers["Content-Type"] = "application/json"
            response = request(method, url, headers=headers,
                               params=params, json=json, data=data, files=files)
            if response.status_code == 401 and retry_on_401:
                self.invalidate_token()
                return self._request(method, path, params=params,
                                     json=json, data=data, files=files, retry_on_401=False)
            if raise_error:
                response.raise_for_status()
            return response
        except HTTPError as err:
            print('response.content', err.response.content)
            raise

    def healthcheck(self):
        response = self._request("GET", "/v1/healthcheck")
        try:
            return response.json()
        except Exception:
            return {"status": "ok", "http_status": response.status_code}


class EInvoicingFlow(EInvoicingAbstract):

    def __init__(self, flow_url, auth_url, client_id, secret_id, **kwarg):
        super().__init__(flow_url, auth_url, client_id, secret_id, **kwarg)

    def submit_flow(self, file_content, file_name, flow_syntax,
                    processing_rule=None, flow_profile=None, tracking_id=None, sha256=None):
        flow_info = {"flowSyntax": flow_syntax, "name": file_name}
        if processing_rule:
            flow_info["processingRule"] = processing_rule
        if flow_profile:
            flow_info["flowProfile"] = flow_profile
        if tracking_id:
            flow_info["trackingId"] = tracking_id
        if sha256:
            flow_info["sha256"] = sha256
        files = {
            "file": (file_name, file_content, "application/octet-stream"),
            "flowInfo": (None, json.dumps(flow_info), "application/xml"),
        }
        response = self._request("POST", "/v1/flows", files=files)
        return response.json()

    def submit_cdar(self, current_ident, issuer_ident, bill_ref, bill_date, status_code, reason_code):
        hdl = CdarHandler(current_ident, issuer_ident, bill_ref, bill_date)
        xml = hdl.generate(status_code, reason_code)
        print("--- cdar ---", xml, "---------")
        self.submit_flow(file_content=xml, file_name=bill_ref, flow_syntax='CDAR')

    def search_flows(self, processing_rule=None, flow_type=None, status=None,
                     flow_direction=None, ack_status=None, updated_after=None, updated_before=None,
                     tracking_id=None,
                     ignore=0, limit=25):
        where = {}
        if processing_rule:
            where["processingRule"] = (
                processing_rule if isinstance(processing_rule, list) else [processing_rule]
            )
        if flow_type:
            where["flowType"] = flow_type if isinstance(flow_type, list) else [flow_type]
        if status:
            where["status"] = status if isinstance(status, list) else [status]
        if flow_direction:
            where["flowDirection"] = (
                flow_direction if isinstance(flow_direction, list) else [flow_direction]
            )
        if ack_status:
            where["ackStatus"] = ack_status
        if updated_after:
            where["updatedAfter"] = updated_after
        if updated_before:
            where["updatedBefore"] = updated_before
        if tracking_id:
            where["trackingId"] = tracking_id
        body = {"ignore": ignore, "limit": limit, "where": where}
        response = self._request("POST", "/v1/flows/search", json=body)
        return response.json()

    def get_flow(self, flow_id, doc_type="Metadata"):
        response = self._request("GET", f"/v1/flows/{flow_id}", params={"docType": doc_type})
        if doc_type == "Metadata":
            return response.json()
        return response.content


class EInvoicingDirectory(EInvoicingAbstract):

    def __init__(self, directory_url, auth_url, client_id, secret_id, **kwarg):
        super().__init__(directory_url, auth_url, client_id, secret_id, **kwarg)

    def search_company(self, name=None, siren_siret=None, postalcode=None, locality=None, status=None, ignore=0, limit=50):
        body = {"limit": limit, "ignore": ignore}
        body['fields'] = ["siret", "siren", "name", "facilityType", "administrativeStatus", "siretInstructions",
                          "address", "pmStatus", "pmOnly", "managesPaymentStatus",
                          "managesLegalCommitment", "managesLegalCommitmentOrService", "serviceCodeStatus"]
        filters = {}
        if name:
            filters["name"] = {"op": "contains", "value": name}
        if siren_siret:
            if len(siren_siret) < 10:
                filters["siren"] = {"op": "strict", "value": siren_siret}
            else:
                filters["siret"] = {"op": "strict", "value": siren_siret}
        if postalcode:
            filters["postalcode"] = {"op": "contains", "value": postalcode}
        if locality:
            filters["locality"] = {"op": "contains", "value": locality}
        if status:
            filters["administrativeStatus"] = {"op": "strict", "value": status}
        if len(filters) > 0:
            body['filters'] = filters
        print(">> body", body)
        response = self._request("POST", "/v1/siret/search", json=body, raise_error=False)
        if response.status_code == 204:
            return {"total": 0, "results": [], "error": response.json()}
        elif response.status_code == 400:
            return {"total": 0, "results": [], "error": response.json()}
        return response.json()

    def get_establishment_by_siret(self, siret):
        response = self._request("GET", f"/v1/siret/code-insee:{siret}")
        return response.json()


class CdarHandler(object):

    ROLE_WK = 'WK'  # Platform
    ROLE_SE = 'SE'  # Seller
    ROLE_BY = 'BY'  # Buyer
    ROLE_CN = 'CN'  # Consignee
    ROLE_DP = 'DP'  # Delivery point

    FORMAT_DATETIME = '204'  # YYYYMMDDHHmmss
    FORMAT_DATE = '102'  # YYYYMMDD

    SCHEME_SIREN_0225 = '0225'
    SCHEME_SIREN_0002 = '0002'

    DOC_INVOICE = '380'

    namespaces = {
        'rsm': 'urn:un:unece:uncefact:data:standard:CrossDomainAcknowledgementAndResponse:100',
        'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100',
        'udt': 'urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100',
        'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

    STATUS_DEPOSITED = 200
    STATUS_ISSUED = 201
    STATUS_RECEIVED = 202
    STATUS_AVAILABLE = 203
    STATUS_TAKEN_OVER = 204
    STATUS_APPROVED = 205
    STATUS_PARTIALLY_APPROVED = 206
    STATUS_DISPUTED = 207
    STATUS_SUSPENDED = 208
    STATUS_COMPLETED = 209
    STATUS_REFUSED = 210
    STATUS_PAYMENT_SENT = 211
    STATUS_PAID = 212
    STATUS_REJECTED = 213

    STATUS_LABEL_KEYS = {
        STATUS_DEPOSITED: 'EInvStatus200Deposited',
        STATUS_ISSUED: 'EInvStatus201Issued',
        STATUS_RECEIVED: 'EInvStatus202Received',
        STATUS_AVAILABLE: 'EInvStatus203Available',
        STATUS_TAKEN_OVER: 'EInvStatus204TakenOver',
        STATUS_APPROVED: 'EInvStatus205Approved',
        STATUS_PARTIALLY_APPROVED: 'EInvStatus206PartiallyApproved',
        STATUS_DISPUTED: 'EInvStatus207Disputed',
        STATUS_SUSPENDED: 'EInvStatus208Suspended',
        STATUS_COMPLETED: 'EInvStatus209Completed',
        STATUS_PAYMENT_SENT: 'EInvStatus211PaymentTransmitted',
        STATUS_PAID: 'EInvStatus212Paid',
        STATUS_REFUSED: 'EInvStatus210Refused',
        STATUS_REJECTED: 'EInvStatus213Rejected',
    }

    def __init__(self, current_ident, issuer_ident, bill_ref, bill_date):
        self.current_ident = current_ident
        self.issuer_ident = issuer_ident
        self.bill_ref = bill_ref
        self.bill_date = bill_date if isinstance(bill_date, datetime) else datetime.fromisoformat(bill_date)
        self.data = {}
        self.cdar_id = None
        self._initial_dom()

    def _initial_dom(self):
        from xml.dom.minidom import getDOMImplementation
        impl = getDOMImplementation()
        self.dom = impl.createDocument(self.namespaces['rsm'], "rsm:CrossDomainAcknowledgementAndResponse", None)
        self.root = self.dom.documentElement
        self.root.setAttribute('xmlns:rsm', self.namespaces['rsm'])
        self.root.setAttribute('xmlns:xsi', self.namespaces['xsi'])
        self.root.setAttribute('xmlns:qdt', self.namespaces['qdt'])
        self.root.setAttribute('xmlns:ram', self.namespaces['ram'])
        self.root.setAttribute('xmlns:udt', self.namespaces['udt'])

    def get_current_datetime(self):
        return datetime.now().strftime('%Y%m%d%H%M%S')

    def generate(self, status_code, reason_code=''):
        self.cdar_id = "%s_%s_%s#%s_%s" % (self.bill_ref,
                                           str(status_code),
                                           self.bill_date.strftime('%Y%m%d%H%M%S'),
                                           self.DOC_INVOICE,
                                           self.bill_date.strftime('%Y%m%d'))
        process_condition = self.STATUS_LABEL_KEYS[status_code] if status_code in self.STATUS_LABEL_KEYS else 'EInvStatus%s' % status_code

        self.data = {
            'GuidelineID': 'urn.cpro.gouv.fr:1p0:CDV:invoice',

            'ExchangedDocument': {
                'ID': self.cdar_id,
                'Name': self.cdar_id,
                'IssueDateTime': self.get_current_datetime(),

                'SenderTradeParty': {
                    'RoleCode': self.ROLE_WK
                },

                'IssuerTradeParty': {
                    'GlobalID': self.current_ident,  # GlobalID of CDAR SENDER
                    'RoleCode': self.ROLE_BY
                },

                'RecipientTradeParty': {
                    'GlobalID': self.issuer_ident,  # GlobalID of CDAR RECIPIENT
                    'SchemeID': self.SCHEME_SIREN_0002,
                    'RoleCode': self.ROLE_SE,
                    'URIID': self.issuer_ident,
                    'URISchemeID': self.SCHEME_SIREN_0225
                }
            },

            'AcknowledgementDocument': {
                'MultipleReferencesIndicator': False,
                'TypeCode': '23',
                'IssueDateTime': self.get_current_datetime(),

                'ReferenceReferencedDocument': {
                    'IssuerAssignedID': self.issuer_ident,
                    'TypeCode': self.DOC_INVOICE,  # TODO: map DOC_INVOICE with object type
                    'FormattedIssueDateTime': self.bill_date.strftime('%Y%m%d%H%M%S'),
                    'ProcessConditionCode': status_code,
                    'ProcessCondition': process_condition,

                    'SpecifiedDocumentStatus': {
                        'ReasonCode': reason_code,
                    } if reason_code != '' else {},

                    'IssuerTradeParty': {
                        'GlobalID': self.issuer_ident,  # GlobalID of invoice sender (Supplier)
                        'SchemeID': self.SCHEME_SIREN_0002,
                        'RoleCode': self.ROLE_SE
                    }
                }
            }
        }
        return self.convert_to_xml()

    def convert_to_xml(self):
        self.addContext(self.data['GuidelineID'])
        self.addExchangedDocument(self.data['ExchangedDocument'])
        self.addAcknowledgementDocument(self.data['AcknowledgementDocument'])
        return self.dom.toprettyxml()

    def _createElementValue(self, tagname, value):
        el = self.dom.createElement(tagname)
        el.appendChild(self.dom.createTextNode(str(value)))
        return el

    def addContext(self, guidelineID):
        context = self.dom.createElement('rsm:ExchangedDocumentContext')

        process = self.dom.createElement('ram:BusinessProcessSpecifiedDocumentContextParameter')
        process.appendChild(self._createElementValue('ram:ID', 'REGULATED'))
        context.appendChild(process)

        guideline = self.dom.createElement('ram:GuidelineSpecifiedDocumentContextParameter')
        guideline.appendChild(self._createElementValue('ram:ID', guidelineID))
        context.appendChild(guideline)
        self.root.appendChild(context)

    def addExchangedDocument(self, doc):
        exchanged = self.dom.createElement('rsm:ExchangedDocument')
        exchanged.appendChild(self._createElementValue('ram:ID', doc['ID']))
        exchanged.appendChild(self._createElementValue('ram:Name', doc['Name']))

        self.addDateTimeElement(exchanged, 'ram:IssueDateTime', doc['IssueDateTime'], self.FORMAT_DATETIME)

        self.addTradeParty(exchanged, 'ram:SenderTradeParty', doc['SenderTradeParty'])
        self.addTradeParty(exchanged, 'ram:IssuerTradeParty', doc['IssuerTradeParty'])
        self.addTradeParty(exchanged, 'ram:RecipientTradeParty', doc['RecipientTradeParty'])

        self.root.appendChild(exchanged)

    def addDateTimeElement(self, parent, elementName, value, dateformat):
        element = self.dom.createElement(elementName)
        dateTimeStr = self._createElementValue('udt:DateTimeString', value)
        dateTimeStr.setAttribute('format', dateformat)
        element.appendChild(dateTimeStr)
        parent.appendChild(element)

    def addTradeParty(self, parent, elementName, data):
        party = self.dom.createElement(elementName)
        if 'GlobalID' in data:
            globalID = self._createElementValue('ram:GlobalID', data['GlobalID'])
            if 'SchemeID' in data:
                globalID.setAttribute('schemeID', data['SchemeID'])
            party.appendChild(globalID)
        party.appendChild(self._createElementValue('ram:RoleCode', data['RoleCode']))
        if 'URIID' in data:
            uriComm = self.dom.createElement('ram:URIUniversalCommunication')
            uriID = self._createElementValue('ram:URIID', data['URIID'])
            uriID.setAttribute('schemeID', data['URISchemeID'])
            uriComm.appendChild(uriID)
            party.appendChild(uriComm)
        parent.appendChild(party)

    def addAcknowledgementDocument(self, doc):
        ack = self.dom.createElement('rsm:AcknowledgementDocument')
        multipleRef = self.dom.createElement('ram:MultipleReferencesIndicator')
        indicator = self._createElementValue('udt:Indicator', 'true' if doc['MultipleReferencesIndicator'] else 'false')
        multipleRef.appendChild(indicator)
        ack.appendChild(multipleRef)
        ack.appendChild(self._createElementValue('ram:TypeCode', doc['TypeCode']))
        self.addDateTimeElement(ack, 'ram:IssueDateTime', doc['IssueDateTime'], self.FORMAT_DATETIME)
        self.addReferencedDocument(ack, doc['ReferenceReferencedDocument'])
        self.root.appendChild(ack)

    def addReferencedDocument(self, parent, doc):
        ref = self.dom.createElement('ram:ReferenceReferencedDocument')
        ref.appendChild(self._createElementValue('ram:IssuerAssignedID', doc['IssuerAssignedID']))
        ref.appendChild(self._createElementValue('ram:TypeCode', doc['TypeCode']))

        formattedDateTime = self.dom.createElement('ram:FormattedIssueDateTime')
        dateTimeStr = self._createElementValue('qdt:DateTimeString', doc['FormattedIssueDateTime'])
        dateTimeStr.setAttribute('format', self.FORMAT_DATETIME)
        formattedDateTime.appendChild(dateTimeStr)
        ref.appendChild(formattedDateTime)

        ref.appendChild(self._createElementValue('ram:ProcessConditionCode', doc['ProcessConditionCode']))
        ref.appendChild(self._createElementValue('ram:ProcessCondition', doc['ProcessCondition']))

        self.addTradeParty(ref, 'ram:IssuerTradeParty', doc['IssuerTradeParty'])
        parent.appendChild(ref)

        if 'SpecifiedDocumentStatus' in doc:
            status = self.dom.createElement('ram:SpecifiedDocumentStatus')
            if 'ReasonCode' in doc['SpecifiedDocumentStatus']:
                status.appendChild(self._createElementValue('ram:ReasonCode', doc['SpecifiedDocumentStatus']['ReasonCode']))
            if 'Reason' in doc['SpecifiedDocumentStatus']:
                status.appendChild(self._createElementValue('ram:Reason', doc['SpecifiedDocumentStatus']['Reason']))
            ref.appendChild(status)
