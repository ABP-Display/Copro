# -*- coding: utf-8 -*-
'''
diacamma.invoice test_tools package

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
from re import match
from django.core.exceptions import ObjectDoesNotExist
from urllib.parse import urlsplit, parse_qsl
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from base64 import b64encode
from json import dumps
from unittest.mock import Mock

from django.conf import settings
from django.test.client import FakePayload

from lucterios.framework.test import LucteriosTest
from lucterios.documents.models import DocumentContainer

from diacamma.accounting.test_tools import create_account
from diacamma.accounting.models import FiscalYear, ChartsAccount
from diacamma.payoff.models import BankAccount, PaymentMethod
from diacamma.payoff.views_deposit import BankTransactionList, BankTransactionShow
from diacamma.payoff.payment_type import PaymentTypeMoneticoPaiement, PaymentTypeHelloAsso
from lucterios.CORE.parameters import Params


def default_bankaccount_fr():
    Params.setvalue("payoff-cash-account", "531")
    create_account(['581'], 0, FiscalYear.get_current())
    BankAccount.objects.create(designation="My bank", reference="0123 456789 321654 12", account_code="512")
    BankAccount.objects.create(designation="PayPal", reference="paypal@moi.com", account_code="581", fee_account_code='627')
    BankAccount.objects.create(designation="Old", reference="Old", account_code="531", is_disabled=True)


def default_bankaccount_be():
    Params.setvalue("payoff-cash-account", "570000")
    create_account(['552000'], 0, FiscalYear.get_current())
    BankAccount.objects.create(designation="My bank", reference="0123 456789 321654 12", account_code="550000")
    BankAccount.objects.create(designation="PayPal", reference="paypal@moi.com", account_code="552000")
    BankAccount.objects.create(designation="Old", reference="Old", account_code="570000", is_disabled=True)


def default_bankaccount_ma():
    Params.setvalue("payoff-cash-account", "5161")
    create_account(['5122'], 0, FiscalYear.get_current())
    BankAccount.objects.create(designation="My bank", reference="0123 456789 321654 12", account_code="5121")
    BankAccount.objects.create(designation="PayPal", reference="paypal@moi.com", account_code="5122")
    BankAccount.objects.create(designation="Old", reference="Old", account_code="5123", is_disabled=True)


def default_paymentmethod():
    PaymentMethod.objects.create(paytype=0, bank_account_id=1, extra_data='123456789\nAABBCCDD')
    PaymentMethod.objects.create(paytype=1, bank_account_id=1, extra_data='Truc\n1 rue de la Paix{[newline]}99000 LA-BAS')
    PaymentMethod.objects.create(paytype=2, bank_account_id=2, extra_data='monney@truc.org')
    PaymentMethod.objects.create(paytype=3, bank_account_id=1, extra_data='http://payement.online.com\nPrécisez le N° de devis ou de facture')
    PaymentMethod.objects.create(paytype=4, bank_account_id=2, extra_data='7979879878\nababab\n12345678901234567890')
    PaymentMethod.objects.create(paytype=5, bank_account_id=2, extra_data='0123456789\n0123456789')


class PaymentTest(LucteriosTest):

    server_port = 9500

    def setUp(self):
        LucteriosTest.setUp(self)
        if hasattr(settings, "DIACAMMA_PAYOFF_PAYPAL_URL"):
            del settings.DIACAMMA_PAYOFF_PAYPAL_URL
        if hasattr(settings, "DIACAMMA_HELLO_ASSO_URL"):
            del settings.DIACAMMA_HELLO_ASSO_URL

    def check_account(self, year_id, code, value, name=""):
        try:
            chart = ChartsAccount.objects.get(year_id=year_id, code=code)
            self.assertAlmostEqual(value, chart.get_current_total(with_correction=False), msg=chart.name, delta=0.0001)
            if name != '':
                self.assertEqual(name, chart.name)
        except ObjectDoesNotExist:
            if value is not None:
                raise

    def check_email_msg(self, msg, itemid, title, amount='100.0', tax='0.0'):
        from lucterios.mailing.tests import decode_b64
        email_content = decode_b64(msg.get_payload())
        self.assertTrue('<html>this is a bill.<hr/>' in email_content, email_content)
        self.assertTrue(email_content.find('<u><i>IBAN</i></u>') != -1, email_content)
        self.assertTrue(email_content.find('123456789') != -1, email_content)
        self.assertTrue(email_content.find("<u><i>à l'ordre de</i></u>") != -1, email_content)
        self.assertTrue(email_content.find('<u><i>adresse</i></u>') != -1, email_content)
        self.assertTrue(email_content.find('Truc') != -1, email_content)
        self.assertTrue(email_content.find('1 rue de la Paix<newline>99000 LA-BAS') != -1, email_content)
        self.check_paypal_msg(email_content, itemid, title, amount, tax)

    def check_paypal_msg(self, html_content, itemid, title, amount='100.0', tax='0.0'):
        paypal_href = match(".*<a href='(.*)' name='paypal' target='_blank'>.*", html_content)
        self.assertTrue(paypal_href is not None, html_content)
        paypal_params = dict(parse_qsl(urlsplit(paypal_href.group(1)).query))
        self.assertEqual(paypal_params['currency_code'], 'EUR', paypal_params)
        self.assertEqual(paypal_params['lc'], 'fr', paypal_params)
        self.assertEqual(paypal_params['return'], 'http://testserver', paypal_params)
        self.assertEqual(paypal_params['cancel_return'], 'http://testserver', paypal_params)
        self.assertEqual(paypal_params['notify_url'], 'http://testserver/diacamma.payoff/validationPaymentPaypal', paypal_params)
        self.assertEqual(paypal_params['business'], 'monney@truc.org', paypal_params)
        self.assertEqual(paypal_params['item_name'], title, paypal_params)
        self.assertEqual(paypal_params['custom'], str(itemid), paypal_params)
        self.assertEqual(paypal_params['amount'], amount, paypal_params)
        self.assertEqual(paypal_params['tax'], tax, paypal_params)

    def check_payment(self, itemid, title, amount='100.0', tax='0.0'):
        if len(self.json_data) > 0:
            self.assert_attrib_equal('paymeth_1', 'description', 'virement')
            txt_value = self.json_data["paymeth_1"]
            self.assertTrue(txt_value.find('{[u]}{[i]}IBAN{[/i]}{[/u]}') != -1, txt_value)
            self.assertTrue(txt_value.find('123456789') != -1, txt_value)

            self.assert_attrib_equal('paymeth_2', 'description', 'chèque')
            txt_value = self.json_data["paymeth_2"]
            self.assertTrue(txt_value.find("{[u]}{[i]}à l'ordre de{[/i]}{[/u]}") != -1, txt_value)
            self.assertTrue(txt_value.find('{[u]}{[i]}adresse{[/i]}{[/u]}') != -1, txt_value)
            self.assertTrue(txt_value.find('Truc') != -1, txt_value)
            self.assertTrue(txt_value.find('1 rue de la Paix{[newline]}99000 LA-BAS') != -1, txt_value)

            self.assert_attrib_equal('paymeth_3', 'description', 'PayPal')
            txt_value = self.json_data["paymeth_3"]
            self.check_paypal_msg(txt_value.replace('{[', '<').replace(']}', '>'), itemid, title, amount, tax)
            return txt_value

    def check_payment_paypal(self, itemid, title, success=True, amount=100.0):
        paypal_validation_fields = {"txn_id": "2X7444647R1155525", "residence_country": "FR",
                                    "payer_status": "verified", "protection_eligibility": "Ineligible",
                                    "mc_gross": "%.2f" % amount, "charset": "windows-1252",
                                    "test_ipn": "1", "first_name": "test",
                                    "payment_date": "13:52:34 Apr 03, 2015 PDT", "transaction_subject": "",
                                    "ipn_track_id": "dda0f18cb9279", "shipping": "0.00",
                                    "item_number": "", "payment_type": "instant",
                                    "txn_type": "web_accept", "mc_fee": "3.67",
                                    "payer_email": "test-buy@gmail.com", "payment_status": "Completed",
                                    "payment_fee": "", "payment_gross": "",
                                    "business": "monney@truc.org", "tax": "0.00",
                                    "handling_amount": "0.00", "item_name": title,
                                    "notify_version": "3.8", "last_name": "buyer",
                                    "custom": "%d" % itemid, "verify_sign": "A7lgc2.jwEO6kvL1E5vEX03Q2la0A8TLpWtV5daGrDAvTm8c8AewCHR3",
                                    "mc_currency": "EUR", "payer_id": "BGZCL28GZVFHE",
                                    "receiver_id": "4P9LXTHC9TRYS", "quantity": "1",
                                    "receiver_email": "monney@truc.org", }

        self.factory.xfer = BankTransactionList()
        self.calljson('/diacamma.payoff/bankTransactionList', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankTransactionList')
        self.assert_count_equal('banktransaction', 0)
        PaymentTest.server_port += 1
        setattr(settings, "DIACAMMA_PAYOFF_PAYPAL_URL", "http://localhost:%d" % PaymentTest.server_port)
        httpd = TestHTTPServer(('localhost', PaymentTest.server_port))
        httpd.start()
        try:
            self.call_ex('/diacamma.payoff/validationPaymentPaypal', paypal_validation_fields, True)
            self.assertEqual(self.response.content, b'', 'validationPaymentPaypal')
        finally:
            httpd.shutdown()
        self.factory.xfer = BankTransactionShow()
        self.calljson('/diacamma.payoff/bankTransactionShow', {'banktransaction': 1}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankTransactionShow')
        self.assert_json_equal('LABELFORM', 'date', "2015-04-03T20:52", True)
        contains = self.json_data["contains"]
        if success:
            self.assertEqual(len(contains), 1093 + len(title) + len("%.2f" % amount), contains)
        self.assertTrue("item_name = %s" % title in contains, contains)
        self.assertTrue("custom = %d" % itemid in contains, contains)
        self.assertTrue("business = monney@truc.org" in contains, contains)
        if success:
            self.assert_json_equal('LABELFORM', 'status', 1)
        else:
            self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'payer', "test buyer")
        self.assert_json_equal('LABELFORM', 'amount', amount)
        self.assert_json_equal('', '#amount/formatnum', "N3")

        self.factory.xfer = BankTransactionList()
        self.calljson('/diacamma.payoff/bankTransactionList', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankTransactionList')
        self.assert_count_equal('banktransaction', 1)
        self.assert_json_equal('', 'banktransaction/@0/date', '2015-04-03T20:52', True)
        if success:
            self.assert_json_equal('', 'banktransaction/@0/status', 1)
        else:
            self.assert_json_equal('', 'banktransaction/@0/status', 0)
        self.assert_json_equal('', 'banktransaction/@0/payer', 'test buyer')
        self.assert_json_equal('', 'banktransaction/@0/amount', amount)

    def check_payment_moneticopaiement(self, itemid, title, success=True, amount=100.0, payer="Minimum"):
        monetico_method = PaymentMethod.objects.filter(paytype=PaymentTypeMoneticoPaiement.num).first()
        monetico_fields = {"TPE": "0000001",
                           "date": "20/07/2018_a_18:24:10",
                           "montant": "%.2fEUR" % amount,
                           "reference": "REF%08d" % itemid,
                           "texte-libre": title,
                           "code-retour": "payetest",
                           "cvx": "oui",
                           "vld": "1223",
                           "brand": "VI",
                           "numauto": "000000",
                           "usage": "inconnu",
                           "typecompte": "particulier",
                           "ecard": "non",
                           "modepaiement": "CB",
                           "authentification": "ewogICAicHJvdG9jb2wiIDogIjNEU2VjdXJlIiwKICAgInN0YXR1cyIgOiAibm90X2Vucm9sbGVkIiwKICAgInZlcnNpb24iIDogIjEuMC4yIgp9Cg==",
                           "MAC": "12345697890"}
        if success:
            monetico_fields['MAC'] = monetico_method.paymentType.get_mac(monetico_fields)

        self.factory.xfer = BankTransactionList()
        self.calljson('/diacamma.payoff/bankTransactionList', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankTransactionList')
        self.assert_count_equal('banktransaction', 0)

        self.call_ex('/diacamma.payoff/validationPaymentMoneticoPaiement', monetico_fields, True)
        self.assertEqual(self.content, "version=2\ncdr=0" if success else "version=2\ncdr=1", 'validationPaymentMoneticoPaiement')

        self.factory.xfer = BankTransactionList()
        self.calljson('/diacamma.payoff/bankTransactionList', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankTransactionList')
        self.assert_count_equal('banktransaction', 1)
        if success:
            self.assert_json_equal('', 'banktransaction/@0/status', 1)
        else:
            self.assert_json_equal('', 'banktransaction/@0/status', 0)
        self.assert_json_equal('', 'banktransaction/@0/payer', payer)
        self.assert_json_equal('', 'banktransaction/@0/amount', amount)
        self.assert_json_equal('', 'banktransaction/@0/date', '2018-07-20T18:24', True)

    def check_payment_helloasso(self, itemid, success=True, amount=100.0, payer="Minimum"):
        PaymentTypeHelloAsso.connect = Mock()
        PaymentTypeHelloAsso.get_api = Mock()
        setattr(settings, "DIACAMMA_HELLO_ASSO_URL", "http://localhost:%d" % PaymentTest.server_port)
        helloasso_fields = {
            'data': {
                'state': 'Authorized',
                'amount': int(amount * 100),
                'payer': {'firstName': '', 'lastName': '', 'company': payer},
                'date': '2015-04-03T20:52:23.456891345678',
                'items': [{"id": 357}],
            },
            'eventType': "Payment",
            'metadata': {
                'reference': itemid,
            },
        }
        self.call_ex('/diacamma.payoff/validationPaymentHelloAsso', {}, True, **{"wsgi.input": FakePayload(dumps(helloasso_fields).encode('ascii'))})
        self.assertEqual(self.content, "", 'validationPaymentHelloAsso')

        self.factory.xfer = BankTransactionList()
        self.calljson('/diacamma.payoff/bankTransactionList', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankTransactionList')
        self.assert_count_equal('banktransaction', 1)
        if success:
            self.assert_json_equal('', 'banktransaction/@0/status', 1)
        else:
            self.assert_json_equal('', 'banktransaction/@0/status', 0)
        self.assert_json_equal('', 'banktransaction/@0/payer', payer)
        self.assert_json_equal('', 'banktransaction/@0/amount', amount)
        self.assert_json_equal('', 'banktransaction/@0/date', '2015-04-03T20:52', True)


class TestHTTPServer(HTTPServer, BaseHTTPRequestHandler, Thread):

    def __init__(self, server_address):
        HTTPServer.__init__(self, server_address, TestHandle)
        Thread.__init__(self, target=self.serve_forever)


class TestHandle(BaseHTTPRequestHandler):

    result = 'VERIFIED'

    def do_POST(self):
        """Respond to a POST request."""
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(self.result.encode())


def check_pdfreport(testobj, objectname, itemid, is_saved, pdfreportB64=None):
    doc = DocumentContainer.objects.filter(metadata='%s-%d' % (objectname, itemid)).first()
    testobj.assertTrue(doc is not None)
    doc_content = b64encode(doc.content.read()).decode()
    if pdfreportB64 is None:
        pdfreportB64 = testobj.response_json['print']["content"]
    pdfreportB64 = pdfreportB64.replace('\r', '').strip()
    pdfreportB64 = pdfreportB64.replace('\n', '').strip()
    if is_saved:
        testobj.assertEqual(len(doc_content), len(pdfreportB64), '%s-%d : %s' % (objectname, itemid, doc.name))
        testobj.assertSequenceEqual(doc_content, pdfreportB64, '%s-%d : %s' % (objectname, itemid, doc.name))
    else:
        testobj.assertNotEqual(doc_content, pdfreportB64, '%s-%d : %s' % (objectname, itemid, doc.name))
