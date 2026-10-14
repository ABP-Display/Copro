# -*- coding: utf-8 -*-
'''
diacamma.payoff views package

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
from datetime import datetime, timezone as tzdatetime, timedelta, tzinfo
import logging
from json import dumps

from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.http.response import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from lucterios.framework.tools import MenuManage, toHtml, get_url_from_request
from lucterios.framework.xferbasic import XferContainerAbstract
from lucterios.framework.error import LucteriosException, IMPORTANT, MINOR
from lucterios.contacts.models import LegalEntity
from lucterios.mailing.email_functions import will_mail_send, send_email

from diacamma.payoff.models import BankTransaction, PaymentMethod, Supporting, Payoff
from diacamma.payoff.payment_type import PaymentType, PaymentTypePayPal, PaymentTypeMoneticoPaiement, \
    PaymentTypeHelloAsso, PaymentTypeStripe
from time import sleep


class CheckPaymentGeneric(XferContainerAbstract):
    caption = _("Payment")
    short_icon = "mdi:mdi-credit-card-outline"
    readonly = True
    methods_allowed = ('GET', )

    payment_name = ""

    @property
    def payid(self):
        return self.getparam("payid", 0)

    @property
    def support(self):
        if not hasattr(self, '_support'):
            self._support = Supporting.objects.get(id=self.payid).get_final_child()
        return self._support

    @property
    def payment_meth(self):
        return None

    def get_form(self):
        root_uri = self.getparam("url", get_url_from_request(self.request))
        return self.payment_meth.paymentType.get_form(root_uri, self.language, self.support)

    @property
    def sub_title_default(self):
        return ""

    @property
    def sub_title_error(self):
        return _("It is not possible to pay-off this item with %s !") % self.payment_name

    def request_handling(self, request, *args, **kwargs):
        from django.shortcuts import render
        dictionary = {}
        dictionary['title'] = str(settings.APPLIS_NAME)
        dictionary['subtitle'] = settings.APPLIS_SUBTITLE()
        dictionary['applogo'] = settings.APPLIS_LOGO.decode()
        dictionary['content1'] = ''
        dictionary['content2'] = ''
        dictionary['error'] = ''
        self._initialize(request, *args, **kwargs)
        try:
            dictionary['content1'] = self.sub_title_default
            dictionary['content2'] = toHtml(self.get_form(), withclean=False)
        except Exception as err:
            logging.getLogger('diacamma.payoff').exception("CheckPayment")
            dictionary['content1'] = self.sub_title_error
            if isinstance(err, ObjectDoesNotExist) or (isinstance(err, LucteriosException) and err.code in (IMPORTANT, MINOR)):
                dictionary['content2'] = _("This item is deleted, payed or disabled.")
            else:
                dictionary['error'] = str(err)
        return render(request, 'info.html', context=dictionary)


class ValidationPaymentGeneric(XferContainerAbstract):
    model = BankTransaction
    short_icon = "mdi:mdi-credit-card-outline"
    field_id = 'banktransaction'
    methods_allowed = ('GET', 'POST', 'PUT')

    def __init__(self, **kwargs):
        XferContainerAbstract.__init__(self, **kwargs)
        self.success = False
        self.reponse_content = b''

    @property
    def payer(self):
        return ""

    @property
    def amount(self):
        return 0.0

    @property
    def date(self):
        return timezone.now()

    def confirm(self):
        return True

    @property
    def customid(self):
        return 0

    @property
    def supporting(self):
        if not hasattr(self, '_supporting'):
            try:
                self._supporting = Supporting.objects.get(id=self.customid).get_final_child()
            except ObjectDoesNotExist:
                self._supporting = None
        return self._supporting

    @property
    def reference(self):
        return ""

    @property
    def sender_email(self):
        sender_obj = LegalEntity.objects.get(id=1)
        return sender_obj.email

    @property
    def bank_fee(self):
        return 0.0

    @property
    def payment_meth(self):
        return PaymentMethod(paytype=PaymentType.num, extra_data="")

    def fillresponse(self):
        if self.supporting is None:
            return
        try:
            self.item.contains = ""
            self.item.payer = self.payer
            self.item.amount = self.amount
            self.item.date = self.date
            if self.item.date is None:
                self.item.date = timezone.now()
            if self.confirm():
                bank_account = self.payment_meth.bank_account
                if bank_account is None:
                    raise LucteriosException(IMPORTANT, "No account!")
                new_payoff = Payoff()
                new_payoff.supporting = self.supporting.support_validated(self.item.date, with_valid=False)
                new_payoff.date = self.item.date
                new_payoff.amount = self.item.amount
                new_payoff.payer = self.item.payer
                new_payoff.mode = Payoff.MODE_CREDITCARD
                new_payoff.bank_account = bank_account
                new_payoff.reference = self.reference
                new_payoff.bank_fee = self.bank_fee
                new_payoff.save()
                new_payoff.supporting.renew_generate_pdfreport()
                self.item.status = BankTransaction.STATUS_SUCCESS
                self.success = True
            else:
                self.item.status = BankTransaction.STATUS_FAILURE
                self.success = False
        except Exception as err:
            logging.getLogger('diacamma.payoff').exception("ValidationPayment")
            self.item.contains += "{[newline]}"
            self.item.contains += str(err)
            self.item.status = BankTransaction.STATUS_FAILURE
        self.item.save()
        if (self.item.status != BankTransaction.STATUS_SUCCESS) and will_mail_send():
            send_email(self.sender_email, _('Payment failure'), _("""
<html>
An online payment request was received in error in <i>Diacamma</i>.<br/>
<ul>
 <li><u>Mode:</u> %(mode)s</li>
 <li><u>Document:</u> %(doc)s</li>
 <li><u>Date:</u> %(date)s</li>
 <li><u>Amount:</u> %(amount)s</li>
 <li><u>Payer:</u> %(payer)s</li>
<ul>
<br/>
%(current_name)s<br/>
</html>
""") % {'mode': str(self.payment_meth), 'date': self.date, 'payer': self.payer, 'amount': self.amount, 'doc': str(self.supporting), 'current_name': str(LegalEntity.objects.get(id=1))})

    def get_response(self):
        if self.supporting is None:
            from django.shortcuts import render
            dictionary = {}
            dictionary['title'] = str(settings.APPLIS_NAME)
            dictionary['subtitle'] = settings.APPLIS_SUBTITLE()
            dictionary['applogo'] = settings.APPLIS_LOGO.decode()
            dictionary['content1'] = ''
            dictionary['content2'] = ''
            dictionary['error'] = ''
            if self.getparam('ret', 'none') == 'OK':
                dictionary['content1'] = _("Payoff terminate.")
                dictionary['content2'] = _("Thanks you.")
            else:
                dictionary['content1'] = _("Payoff aborded.")
                logging.getLogger('diacamma.payoff').warning("Aborded : %s" % dumps(self.params))
            return render(self.request, 'info.html', context=dictionary)
        else:
            return HttpResponse(self.reponse_content)


@MenuManage.describ('')
class CheckPaymentPaypal(CheckPaymentGeneric):

    payment_name = "PayPal"

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypePayPal.num).first()


@MenuManage.describ('')
class ValidationPaymentPaypal(ValidationPaymentGeneric):
    observer_name = 'PayPal'
    caption = 'ValidationPaymentPaypal'

    @property
    def payer(self):
        return self.getparam('first_name', '') + " " + self.getparam('last_name', '')

    @property
    def amount(self):
        return self.getparam('mc_gross', 0.0)

    @property
    def sender_email(self):
        return self.getparam('payer_email', super().sender_email)

    @property
    def date(self):
        import locale
        saved = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        try:
            payment_date = self.getparam("payment_date", '')
            payoff_date = datetime.strptime(payment_date.replace('PDT', 'GMT'), '%H:%M:%S %b %d, %Y %Z')
            if 'PDT' in payment_date:
                payoff_date += timedelta(hours=7)
            ret_date = timezone.make_aware(payoff_date, timezone=tzdatetime.utc)
            return ret_date
        except Exception:
            logging.getLogger('diacamma.payoff').exception("problem of date %s" % self.getparam("payment_date", ''))
            return timezone.now()
        finally:
            locale.setlocale(locale.LC_ALL, saved)

    def confirm(self):
        from urllib.parse import quote_plus
        from requests import post
        paypal_url = PaymentTypePayPal({}, 0).get_url("")
        paypal_url = paypal_url.replace('https://www.', 'https://ipnpb.')
        fields = 'cmd=_notify-validate'
        try:
            for key, value in self.request.POST.items():
                fields += "&%s=%s" % (key, quote_plus(value))
                if key != 'FORMAT':
                    self.item.contains += "%s = %s{[newline]}" % (key, value)
            res = post(paypal_url, data=fields.encode(), headers={"Content-Type": "application/x-www-form-urlencoded", 'user-agent': 'Python-IPN-Verification-Script'}).text
            logging.getLogger('diacamma.payoff').debug("Check PayPal %s: %s => %s" % (paypal_url, fields, res))
        except Exception:
            logging.getLogger('diacamma.payoff').warning(paypal_url)
            logging.getLogger('diacamma.payoff').warning(fields)
            raise
        if res == 'VERIFIED':
            return True
        elif res == 'INVALID':
            self.item.contains += "{[newline]}- NOT VALIDED BY PAYPAL -{[newline]}"
            return "paypal" in self.request.META.get('HTTP_USER_AGENT', '').lower()
        else:
            self.item.contains += "{[newline]}"
            if res != 'VERIFIED':
                self.item.contains += "NO VALID:"
            self.item.contains += res.replace('\n', '{[newline]}')
            return False

    @property
    def payment_meth(self):
        for payment_meth in PaymentMethod.objects.filter(paytype=PaymentTypePayPal.num):
            if payment_meth.get_items()[0] == self.getparam('receiver_email', ''):
                return payment_meth
        return PaymentMethod(paytype=PaymentType.num, extra_data="")

    @property
    def customid(self):
        return self.getparam('custom', 0)

    @property
    def reference(self):
        return "PayPal " + self.getparam('txn_id', '')

    @property
    def bank_fee(self):
        return self.getparam('mc_fee', 0.0)


@MenuManage.describ('')
class CheckPaymentMoneticoPaiement(CheckPaymentGeneric):

    payment_name = "MoneticoPaiement"

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeMoneticoPaiement.num).first()


@MenuManage.describ('')
class ValidationPaymentMoneticoPaiement(ValidationPaymentGeneric):
    observer_name = 'MoneticoPaiement'
    caption = 'ValidationPaymentMoneticoPaiement'

    @property
    def payer(self):
        return str(self.supporting.third)

    @property
    def amount(self):
        return float(self.getparam('montant', '0EUR')[:-3])

    @property
    def date(self):
        try:
            payoff_date = datetime.strptime(self.getparam("date", ''), '%d/%m/%Y_a_%H:%M:%S')
            return timezone.make_aware(payoff_date, timezone=tzdatetime.utc)
        except Exception:
            logging.getLogger('diacamma.payoff').exception("problem of date %s" % self.getparam("date", ''))
            return timezone.now()

    def confirm(self):
        try:
            parameters = {key: value[0] if isinstance(value, list) else value for key, value in self.request.POST.items()}
            for key, value in parameters.items():
                if key != 'MAC':
                    self.item.contains += "%s = %s{[newline]}" % (key, value)
            if self.payment_meth.paymentType.is_valid_mac(parameters):
                code_retour = parameters['code-retour']
                res = (code_retour.lower() != 'annulation')
                if not res:
                    self.item.contains += "{[newline]}--- NO VALID ---{[newline]}"
            else:
                self.item.contains += "{[newline]}--- INVALID ---{[newline]}"
                res = False
        except Exception:
            logging.getLogger('diacamma.payoff').warning(parameters)
            raise
        if res:
            self.reponse_content = b"version=2\ncdr=0\n"
        else:
            self.reponse_content = b"version=2\ncdr=1\n"
        return res

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeMoneticoPaiement.num).first()

    @property
    def customid(self):
        return int(self.getparam('reference', 'REF0000000')[3:])

    @property
    def reference(self):
        return "MoneticoPaiement " + self.getparam('numauto', '')

    @property
    def bank_fee(self):
        return 0.0


@MenuManage.describ('')
class CheckPaymentHelloAsso(CheckPaymentGeneric):

    payment_name = "Hello-Asso"

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeHelloAsso.num).first()


@MenuManage.describ('')
class ValidationPaymentHelloAsso(ValidationPaymentGeneric):
    observer_name = 'HelloAsso'
    caption = 'ValidationPaymentHelloAsso'

    def __init__(self, **kwargs):
        ValidationPaymentGeneric.__init__(self, **kwargs)
        self.helloasso_data = {}
        self.helloasso_eventtype = ""

    @property
    def payer(self):
        if 'company' not in self.helloasso_data['payer']:
            self.helloasso_data['payer']['company'] = ''
        return str("%(firstName)s %(lastName)s %(company)s" % self.helloasso_data['payer']).strip()

    @property
    def amount(self):
        return self.helloasso_data['amount'] / 100.0

    @property
    def date(self):
        try:
            payoff_date = datetime.strptime(self.helloasso_data['date'][:19], '%Y-%m-%dT%H:%M:%S')
            return timezone.make_aware(payoff_date, timezone=tzdatetime.utc)
        except Exception:
            logging.getLogger('diacamma.payoff').exception("problem of date %s" % self.helloasso_data['date'])
            return timezone.now()

    @property
    def customid(self):
        if (self.helloasso_eventtype == 'Payment') and (self.helloasso_data['state'] == 'Authorized'):
            return self.payment_meth.paymentType.get_customid(self.helloasso_data, self.helloasso_meta)
        else:
            return 0

    def confirm(self):
        self.item.contains += "eventType = %s{[newline]}" % self.helloasso_eventtype
        self.item.contains += "Meta = %s{[newline]}" % self.helloasso_meta
        for key, value in self.helloasso_data.items():
            self.item.contains += "%s = %s{[newline]}" % (key, value)
        return True

    @property
    def reference(self):
        return "N°%s" % self.helloasso_data['items'][0]['id']

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeHelloAsso.num).first()

    def _initialize(self, request, *_, **kwargs):
        from json import loads
        wsgi_input_content = self.request.META['wsgi.input'].read().decode()
        logging.getLogger('diacamma.payoff').debug("wsgi_input_content = %s / META = %s" % (wsgi_input_content, self.request.META))
        return_content = loads(wsgi_input_content)
        self.helloasso_data = return_content['data']
        self.helloasso_eventtype = return_content['eventType']
        self.helloasso_meta = return_content['metadata'] if 'metadata' in return_content else {}
        logging.getLogger('diacamma.payoff').debug("eventType = %s / data = %s / metadata = %s" % (self.helloasso_eventtype, self.helloasso_data, self.helloasso_meta))
        ValidationPaymentGeneric._initialize(self, request, *_, **kwargs)


@MenuManage.describ('')
class CheckPaymentStripe(CheckPaymentGeneric):

    payment_name = "Stripe"

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeStripe.num).first()


@MenuManage.describ('')
class ValidationPaymentStripe(ValidationPaymentGeneric):
    observer_name = 'Stripe'
    caption = 'ValidationPaymentStripe'

    @property
    def payer(self):
        name = self.data['customer_details']['name']
        if name is not None:
            return name
        else:
            return str(self.supporting.third)

    @property
    def amount(self):
        return float(self.data['amount_total'] / 100.0)

    @property
    def date(self):
        datetime.fromtimestamp(self.data['created'])
        return timezone.now()

    @property
    def payment_meth(self):
        return PaymentMethod.objects.get(id=self.getparam('parent_id', 0))

    @property
    def payment_items(self):
        if not hasattr(self, '_payment_items'):
            self._payment_items = self.payment_meth.paymentType.get_items()
        return self._payment_items

    @property
    def customid(self):
        import stripe
        stripe.api_key = self.payment_items[0]
        checkout_session = stripe.checkout.Session.retrieve(self.getparam('session_id', ''))
        self.data = dict(checkout_session.last_response.data)
        return int(self.data['metadata']['custom'])

    @property
    def reference(self):
        return self.data['payment_intent']

    @property
    def bank_fee(self):
        import stripe
        stripe.api_key = self.payment_items[0]
        loop_nb = 0
        while (loop_nb < 3):
            charge = stripe.Charge.list(payment_intent=self.data['payment_intent'])
            if charge.last_response.data['data'][0]["balance_transaction"] is not None:
                break
            sleep(0.5 * loop_nb)
            loop_nb += 1
        self.item.contains += "%s = %s{[newline]}" % ('Charge[payment_intent](%d)' % loop_nb, str(charge))
        fee_sum = 0.0
        for charge_item in charge.last_response.data['data']:
            if charge_item["balance_transaction"] is not None:
                balance = stripe.BalanceTransaction.retrieve(charge_item["balance_transaction"])
                self.item.contains += "%s = %s{[newline]}" % ('BalanceTransaction[balance_transaction]', str(balance))
                fee_sum += balance['fee']
        return float(fee_sum / 100.0)

    def confirm(self):
        is_ok = self.data['payment_status'] == 'paid'
        self.params['ret'] = 'OK' if is_ok else 'BAD'
        for key, value in self.data.items():
            self.item.contains += "%s = %s{[newline]}" % (key, dumps(value))
        return is_ok

    def fillresponse(self):
        ValidationPaymentGeneric.fillresponse(self)
        self._supporting = None
