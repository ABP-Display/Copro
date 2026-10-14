# -*- coding: utf-8 -*-
'''
@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2020 sd-libre.fr
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
from json import dumps
from base64 import b64encode
from datetime import datetime
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from lucterios.framework.tools import get_bool_textual
from lucterios.framework.error import LucteriosException, IMPORTANT, GRAVE
from lucterios.framework.filetools import remove_accent
from lucterios.framework.xfercomponents import XferCompPassword
from lucterios.CORE.parameters import Params

from lucterios.contacts.models import LegalEntity

from diacamma.accounting.tools import get_amount_from_format_devise


class PaymentType(object):
    FIELDTYPE_EDIT = 0
    FIELDTYPE_MEMO = 1
    FIELDTYPE_CHECK = 2
    FIELDTYPE_PWD = 3
    FIELDTYPE_EMAIL = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    FIELDTYPE_URL = r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"

    name = ''
    num = -1
    logo_bank = ''
    form_method = 'post'
    help_content = ''

    def __init__(self, extra_data, parentid):
        self.extra_data = extra_data
        self.parentid = parentid

    def get_extra_fields(self):
        return []

    def get_help(self, root_url):
        ret_content = str(self.help_content).strip()
        if "%s" in ret_content:
            return ret_content % root_url
        else:
            return ret_content

    def get_default_items(self):
        items = self.extra_data.split("\n")
        return items

    def get_items(self):
        items = self.get_default_items()
        size = len(self.get_extra_fields())
        while len(items) < size:
            items.append("")
        return items

    def get_info(self):
        res = ""
        items = self.get_items()
        for fieldid, fieldtitle, fieldtype in self.get_extra_fields():
            res += "{[b]}%s{[/b]}{[br/]}" % fieldtitle
            if fieldtype == PaymentType.FIELDTYPE_CHECK:
                res += str(get_bool_textual((items[fieldid - 1] == 'o') or (items[fieldid - 1] == 'True')))
            elif fieldtype == PaymentType.FIELDTYPE_PWD:
                res += "*" * 10
            else:
                res += items[fieldid - 1]
            res += "{[br/]}"
        return res

    def set_items(self, items):
        size = len(self.get_extra_fields())
        while len(items) < size:
            items.append("")
        self.extra_data = "\n".join(items)

    def get_components(self):
        from lucterios.framework.xfercomponents import XferCompEdit, XferCompMemo, XferCompCheck
        items = self.get_items()
        for fieldid, fieldtitle, fieldtype in self.get_extra_fields():
            if fieldtype == PaymentType.FIELDTYPE_EDIT:
                edt = XferCompEdit('item_%d' % fieldid)
            elif fieldtype == PaymentType.FIELDTYPE_MEMO:
                edt = XferCompMemo('item_%d' % fieldid)
            elif fieldtype == PaymentType.FIELDTYPE_CHECK:
                edt = XferCompCheck('item_%d' % fieldid)
            elif fieldtype == PaymentType.FIELDTYPE_PWD:
                edt = XferCompPassword('item_%d' % fieldid)
                edt.security = 0
            elif isinstance(fieldtype, str):
                edt = XferCompEdit('item_%d' % fieldid)
                edt.mask = fieldtype
            edt.set_value(items[fieldid - 1])
            edt.description = fieldtitle
            yield edt

    def get_url(self, root_url, supporting=None):
        return root_url

    def _get_parameters_dict(self, root_url, lang, supporting):
        return {}

    def get_redirect_url(self, root_url, lang, supporting):
        from urllib.parse import quote_plus
        args = ""
        for key, val in self._get_parameters_dict(root_url, lang, supporting).items():
            args += "&%s=%s" % (key, quote_plus(val))
        args = args[1:]
        return "%s?%s" % (self.get_url(root_url, supporting), args)

    def get_html_link(self, root_url, link_url, supportingid=None):
        if supportingid is not None:
            import urllib.parse
            link_url = '%s/%s?payid=%d&url=%s' % (root_url, link_url, supportingid, urllib.parse.quote(root_url))
        formTxt = "{[center]}"
        formTxt += "{[a href='%s' name='%s' target='_blank']}" % (link_url, self.name.lower())
        formTxt += "{[img src='%s/static/diacamma.payoff/images/%s' title='%s' alt='%s' /]}" % (root_url, self.logo_bank, self.name, self.name)
        formTxt += "{[/a]}"
        formTxt += "{[/center]}"
        return formTxt

    def get_form(self, root_url, lang, supporting):
        formTxt = "{[h3]}%s{[/h3]}" % _('Payment')
        formTxt += '{[table border="0"]}\n'
        formTxt += "{[tr]}{[th]}%s{[/th]}{[td]}%s{[/td]}{[/tr]}\n" % (_('nature'), str(supporting))
        formTxt += "{[tr]}{[th]}%s{[/th]}{[td]}%s{[/td]}{[/tr]}\n" % (_('amount'), get_amount_from_format_devise(supporting.total_rest_topay, 5))
        formTxt += "{[/table]}\n"
        formTxt += "{[br/]}\n"
        formTxt += '{[form method="%s" id="payment" name="payment" action="%s"]}\n' % (self.form_method, self.get_url(root_url, supporting))
        for key, value in self._get_parameters_dict(root_url, lang, supporting).items():
            formTxt += '{[input type="hidden" name="%s" value="%s" /]}\n' % (key, value)
        formTxt += '{[button type="submit"]}\n'
        formTxt += "{[img src='%s/static/diacamma.payoff/images/%s' title='%s' alt='%s' /]}\n" % (root_url, self.logo_bank, self.name, self.name)
        formTxt += '{[/button]}\n'
        formTxt += "{[/form]}\n"
        formTxt += '{[label class="info"]}{[br/]}%s{[/label]}\n' % _('Please wait, you will be logged into the payment platform.')
        return formTxt

    def show_pay(self, root_url, lang, supporting):
        return ""


class PaymentTypeTransfer(PaymentType):
    name = _('transfer')
    num = 0
    help_content = _("help_payoff_transfer")

    def get_extra_fields(self):
        return [(1, _('IBAN'), PaymentType.FIELDTYPE_EDIT), (2, _('BIC'), PaymentType.FIELDTYPE_EDIT)]

    def show_pay(self, root_url, lang, supporting):
        items = self.get_items()
        formTxt = "{[center]}"
        formTxt += "{[table width='100%']}{[tr]}"
        formTxt += "    {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('IBAN')
        formTxt += "    {[td]}%s{[/td]}" % items[0]
        formTxt += "{[/tr]}{[tr]}"
        formTxt += "    {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('BIC')
        formTxt += "    {[td]}%s{[/td]}" % items[1]
        formTxt += "{[/tr]}{[tr]}"
        formTxt += "    {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('Reference to remind')
        formTxt += "    {[td]}%s{[/td]}" % supporting.reference
        formTxt += "{[/tr]}{[/table]}"
        formTxt += "{[/center]}"
        return formTxt


class PaymentTypeCheque(PaymentType):
    name = _('cheque')
    num = 1
    help_content = _("help_payoff_cheque")

    def get_extra_fields(self):
        return [(1, _('payable to'), PaymentType.FIELDTYPE_EDIT), (2, _('address'), PaymentType.FIELDTYPE_MEMO)]

    def get_default_items(self):
        if (self.extra_data == ''):
            current_legal = LegalEntity.objects.get(id=1)
            items = [current_legal.name, "%s{[newline]}%s %s" % (current_legal.address, current_legal.postal_code, current_legal.city)]
        else:
            items = self.extra_data.split("\n")
        return items

    def show_pay(self, root_url, lang, supporting):
        items = self.get_items()
        formTxt = "{[center]}"
        formTxt += "{[table width='100%%']}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('payable to')
        formTxt += "        {[td]}%s{[/td]}" % items[0]
        formTxt += "    {[/tr]}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('address')
        formTxt += "        {[td]}%s{[/td]}" % items[1]
        formTxt += "    {[/tr]}"
        formTxt += "{[/table]}"
        formTxt += "{[/center]}"
        return formTxt


class PaymentTypePayPal(PaymentType):
    name = _('PayPal')
    num = 2
    logo_bank = 'pp_cc_mark_74x46.jpg'
    help_content = _("help_payoff_paypal")

    def get_extra_fields(self):
        return [(1, _('Paypal account'), PaymentType.FIELDTYPE_EMAIL), (2, _('With control'), PaymentType.FIELDTYPE_CHECK)]

    def get_url(self, root_url, supporting=None):
        return getattr(settings, 'DIACAMMA_PAYOFF_PAYPAL_URL', 'https://www.paypal.com/cgi-bin/webscr')

    def _get_parameters_dict(self, root_url, lang, supporting):
        if abs(supporting.get_payable_without_tax()) < 0.0001:
            raise LucteriosException(IMPORTANT, _("This item can't be validated!"))
        items = self.get_items()
        parameters_dict = {}
        parameters_dict['business'] = items[0]
        parameters_dict['currency_code'] = Params.getvalue("accounting-devise-iso")
        parameters_dict['lc'] = lang
        parameters_dict['return'] = root_url
        parameters_dict['cancel_return'] = root_url
        parameters_dict['notify_url'] = root_url + '/diacamma.payoff/validationPaymentPaypal'
        parameters_dict['item_name'] = remove_accent(supporting.get_payment_name())
        parameters_dict['custom'] = str(supporting.id)
        parameters_dict['tax'] = str(supporting.get_tax())
        parameters_dict['amount'] = str(supporting.get_payable_without_tax())
        parameters_dict['cmd'] = '_xclick'
        parameters_dict['no_note'] = '1'
        parameters_dict['no_shipping'] = '1'
        return parameters_dict

    def show_pay(self, root_url, lang, supporting):
        items = self.get_items()
        if (items[1] == 'o') or (items[1] == 'True'):
            formTxt = self.get_html_link(root_url, 'diacamma.payoff/checkPaymentPaypal', supporting.id)
        else:
            formTxt = self.get_html_link(root_url, self.get_redirect_url(root_url, lang, supporting))
        return formTxt


class PaymentTypeOnline(PaymentType):
    name = _('online')
    num = 3
    help_content = _("help_payoff_online")

    def get_extra_fields(self):
        return [(1, _('web address'), PaymentType.FIELDTYPE_URL), (2, _('info'), PaymentType.FIELDTYPE_MEMO)]

    def show_pay(self, root_url, lang, supporting):
        items = self.get_items()
        formTxt = "{[center]}"
        formTxt += "{[table width='100%%']}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('web address')
        formTxt += "        {[td]}{[a href='%s' target='_blank']}%s{[/a]}{[/td]}" % (items[0], items[0])
        formTxt += "    {[/tr]}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('info')
        formTxt += "        {[td]}%s{[/td]}" % items[1]
        formTxt += "    {[/tr]}"
        formTxt += "{[/table]}"
        formTxt += "{[/center]}"
        return formTxt


class PaymentTypeMoneticoPaiement(PaymentType):
    name = _('MoneticoPaiement')
    num = 4
    logo_bank = 'monetico_logo.png'
    help_content = _("help_payoff_moneticopaiement")

    def compute_HMACSHA1(self, custumer_key, sData):
        import hashlib
        import hmac
        import encodings.hex_codec
        hexStrKey = custumer_key[0:38]
        hexFinal = custumer_key[38:40] + "00"
        first_letter = ord(hexFinal[0:1])
        if first_letter > 70 and first_letter < 97:
            hexStrKey += chr(first_letter - 23) + hexFinal[1:2]
        elif hexFinal[1:2] == "M":
            hexStrKey += hexFinal[0:1] + "0"
        else:
            hexStrKey += hexFinal[0:2]
        current_codex = encodings.hex_codec.Codec()
        usable_key = current_codex.decode(hexStrKey)[0]
        HMAC = hmac.HMAC(usable_key, None, hashlib.sha1)
        HMAC.update(sData.encode('iso8859-1'))
        return HMAC.hexdigest()

    def get_extra_fields(self):
        return [(1, _('companie code'), PaymentType.FIELDTYPE_EDIT), (2, _('TPE'), PaymentType.FIELDTYPE_EDIT), (3, _('key'), PaymentType.FIELDTYPE_EDIT)]

    def get_contexte_commande(self, supporting):
        contexte = {}
        contexte["billing"] = {
            "firstName": "Ada",
            "lastName": "Lovelace",
            "mobilePhone": "+33-612345678",
            "addressLine1": "101 Rue de Roisel",
            "city": "Y",
            "postalCode": "80190",
            "country": "FR"
        }
        return contexte

    def get_mac(self, parameters):
        paramkeys = list(parameters.keys())
        paramkeys.sort()
        sChaineMAC = '*'.join(["%s=%s" % (key, parameters[key]) for key in paramkeys if key != 'MAC'])
        return self.compute_HMACSHA1(self.get_items()[2], sChaineMAC)

    def is_valid_mac(self, parameters):
        return self.get_mac(parameters) == parameters['MAC'].lower()

    def get_url(self, root_url, supporting=None):
        return getattr(settings, 'DIACAMMA_MONETICO_PAIEMENT_URL', 'https://p.monetico-services.com/') + 'paiement.cgi'

    def _get_parameters_dict(self, root_url, lang, supporting):
        if abs(supporting.get_payable_without_tax()) < 0.0001:
            raise LucteriosException(IMPORTANT, _("This item can't be validated!"))
        parameters_dict = {}
        parameters_dict["version"] = "3.0"
        parameters_dict["TPE"] = self.get_items()[1]
        parameters_dict["contexte_commande"] = b64encode(dumps(self.get_contexte_commande(supporting)).encode('utf8')).decode()
        parameters_dict["date"] = datetime.now().strftime("%d/%m/%Y:%H:%M:%S")
        parameters_dict["montant"] = '%.2f%s' % (supporting.get_total_rest_topay(), Params.getvalue("accounting-devise-iso"))
        parameters_dict["reference"] = 'REF%08d' % supporting.id
        parameters_dict["url_retour_err"] = root_url + '/diacamma.payoff/validationPaymentMoneticoPaiement?ret=BAD'
        parameters_dict["url_retour_ok"] = root_url + '/diacamma.payoff/validationPaymentMoneticoPaiement?ret=OK'
        parameters_dict["lgue"] = lang
        parameters_dict["societe"] = self.get_items()[0]
        parameters_dict["texte-libre"] = supporting.get_payment_name()
        sender_email = LegalEntity.objects.get(id=1).email
        if (sender_email != ''):
            parameters_dict["mail"] = sender_email
        parameters_dict["MAC"] = self.get_mac(parameters_dict)
        return parameters_dict

    def show_pay(self, root_url, lang, supporting):
        formTxt = self.get_html_link(root_url, 'diacamma.payoff/checkPaymentMoneticoPaiement', supporting.id)
        return formTxt


class PaymentTypeHelloAsso(PaymentType):
    name = _('Hello-Asso')
    num = 5
    logo_bank = 'helloasso-logo.png'

    form_method = 'get'
    help_content = _("help_payoff_helloasso")

    @staticmethod
    def check_error(response, *args, **kwargs):
        try:
            value = response.json()
        except Exception:
            value = {'message': response.content.decode()}
        if response.status_code != 200:
            message_txt = value['message'] if 'message' in value else response.content.decode()
            raise LucteriosException(GRAVE, "[%d] %s" % (response.status_code, message_txt))
        for key in args:
            if isinstance(value, dict) and isinstance(key, str) and (key in value):
                value = value[key]
            elif isinstance(value, list) and isinstance(key, int) and (key < len(value)):
                value = value[key]
            else:
                value = None
                break
        if kwargs:
            new_value = []
            for item in value:
                add = True
                for filter_item in kwargs.keys():
                    if filter_item in item.keys():
                        if item[filter_item] != kwargs[filter_item]:
                            add = False
                            break
                if add:
                    new_value.append(item)
            if len(new_value) == 0:
                value = None
            else:
                value = new_value[0]
        return value

    def __init__(self, extra_data, parentid):
        from requests_oauthlib.oauth2_session import log
        PaymentType.__init__(self, extra_data, parentid)
        payoff_logger = logging.getLogger('diacamma.payoff')
        log.setLevel(payoff_logger.level)
        for hdl in payoff_logger.handlers:
            log.addHandler(hdl)
        base_url = getattr(settings, 'DIACAMMA_HELLO_ASSO_URL', 'https://api.helloasso.com')
        self.base_url = base_url[:-1] if base_url[-1] == '/' else base_url
        self.api_session = None

    def connect(self):
        from oauthlib.oauth2 import BackendApplicationClient
        from requests_oauthlib import OAuth2Session
        from requests_oauthlib.oauth2_session import log
        paoff_log = logging.getLogger('diacamma.payoff')
        log.setLevel(paoff_log.level)
        for hdlr in paoff_log.handlers:
            log.addHandler(hdlr)
        client_id = self.get_items()[0]
        client_secret = self.get_items()[1]
        oauth_client = BackendApplicationClient(client_id=client_id)
        oauth_client.grant_type = "client_credentials"
        self.api_session = OAuth2Session(client=oauth_client)
        self.api_session.fetch_token(token_url='%s/oauth2/token' % self.base_url, client_id=client_id, client_secret=client_secret)

    def get_api(self, suburl, *args, **kwargs):
        return self.check_error(self.api_session.get(self.base_url + suburl), *args, **kwargs)

    def get_post(self, suburl, json):
        return self.api_session.post(self.base_url + suburl, json=json)

    def disconnect(self):
        self.get_api('/oauth2/disconnect')

    def get_customid(self, helloasso_data, helloasso_meta):
        self.connect()
        try:
            reference = helloasso_meta["reference"]
            return int(reference)
        except Exception:
            return 0
        finally:
            self.disconnect()

    def get_url(self, root_url, supporting=None):
        from requests_oauthlib.oauth2_session import log
        self.connect()
        try:
            organization_slug = self.get_api("/v5/users/me/organizations", 0, 'organizationSlug')
            new_checkout = {
                "totalAmount": int(supporting.get_total_rest_topay() * 100),
                "initialAmount": int(supporting.get_total_rest_topay() * 100),
                "itemName": str(supporting),
                "backUrl": "%s/%s" % (root_url, 'diacamma.payoff/validationPaymentHelloAsso'),
                "errorUrl": "%s/%s" % (root_url, 'diacamma.payoff/validationPaymentHelloAsso'),
                "returnUrl": root_url,
                "containsDonation": False,
                "metadata": {
                    "reference": supporting.id
                }
            }
            log.debug('new_checkout : %s' % new_checkout)
            form_create = self.check_error(self.get_post("/v5/organizations/%s/checkout-intents" % organization_slug, new_checkout))
            log.debug('form_create : %s' % form_create)
            checkout_id = form_create['id']
            checkout_url = form_create['redirectUrl']
            log.debug('organization_slug : %s  form_slug : %s  form_url : %s' % (organization_slug, checkout_id, checkout_url))
        finally:
            self.disconnect()
        return checkout_url

    def get_extra_fields(self):
        return [(1, _('clientid'), PaymentType.FIELDTYPE_EDIT), (2, _('clientsecret'), PaymentType.FIELDTYPE_PWD)]

    def show_pay(self, root_url, lang, supporting):
        return self.get_html_link(root_url, 'diacamma.payoff/checkPaymentHelloAsso', supporting.id)


class PaymentTypeStripe(PaymentType):
    name = _('Stripe')
    num = 6
    logo_bank = 'stripe_logo_icon.png'
    help_content = _("help_payoff_stripe")
    form_method = 'get'

    def get_extra_fields(self):
        return [(1, _('secret key'), PaymentType.FIELDTYPE_PWD)]

    def get_price_id(self, amount):
        import stripe
        items = self.get_items()
        stripe.api_key = items[0]
        prices = stripe.Price.list(active=True, currency=Params.getvalue("accounting-devise-iso"))
        for price in prices['data']:
            if abs(price['unit_amount'] - amount * 100) < 1e-1:
                return price['id']
        price = stripe.Price.create(
            currency=Params.getvalue("accounting-devise-iso"),
            unit_amount_decimal=str(amount * 100),
            active=True,
            product_data={"name": _("Purchase with Stripe")},
        )
        return price['id']

    def get_url(self, root_url, supporting=None):
        from stripe import StripeClient
        items = self.get_items()
        client = StripeClient(items[0])
        checkout_session = client.v1.checkout.sessions.create(params={
            "currency": Params.getvalue("accounting-devise-iso"),
            "line_items": [
                {"price": self.get_price_id(supporting.get_total_rest_topay()), "quantity": 1}
            ],
            'mode': 'payment',
            'metadata': {"custom": str(supporting.id)},
            'custom_text': {
                "submit": {'message': str(supporting)}
            },
            'success_url': root_url + '/diacamma.payoff/validationPaymentStripe?session_id={CHECKOUT_SESSION_ID}&parent_id=%d' % self.parentid,
        })
        return checkout_session.url

    def show_pay(self, root_url, lang, supporting):
        return self.get_html_link(root_url, 'diacamma.payoff/checkPaymentStripe', supporting.id)


PAYMENTTYPE_LIST = (PaymentTypeTransfer, PaymentTypeCheque, PaymentTypeStripe, PaymentTypePayPal, PaymentTypeOnline, PaymentTypeMoneticoPaiement, PaymentTypeHelloAsso)
