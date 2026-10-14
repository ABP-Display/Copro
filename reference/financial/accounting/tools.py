# -*- coding: utf-8 -*-
'''
tools for accounting package

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

from django.utils.translation import gettext_lazy as _

from lucterios.CORE.parameters import Params

from diacamma.accounting.system import get_accounting_system
from lucterios.framework.tools import format_to_string
from lucterios.framework.models import extract_format


def current_system_account():
    import sys
    current_module = sys.modules[__name__]
    if not hasattr(current_module, 'SYSTEM_ACCOUNT_CACHE'):
        setattr(current_module, 'SYSTEM_ACCOUNT_CACHE', get_accounting_system(Params.getvalue("accounting-system")))
    return current_module.SYSTEM_ACCOUNT_CACHE


def clear_system_account():
    import sys
    current_module = sys.modules[__name__]

    if hasattr(current_module, 'SYSTEM_ACCOUNT_CACHE'):
        del current_module.SYSTEM_ACCOUNT_CACHE


def get_amount_sum(val):
    if val['amount__sum'] is None:
        return 0
    else:
        return val['amount__sum']


def currency_round(amount):
    currency_decimal = Params.getvalue("accounting-devise-prec")
    try:
        return round(float(amount), currency_decimal)
    except Exception:
        return round(0.0, currency_decimal)


def correct_accounting_code(code):
    code = code.strip()
    if current_system_account().has_minium_code_size() and (code != ''):
        code_size = Params.getvalue("accounting-sizecode")
        if code == '0' * code_size:
            return ''
        while len(code) > code_size and code[-1] == '0':
            code = code[:-1]
        while len(code) < code_size:
            code += '0'
    return code


def get_currency_symbole(iso_ident):
    symbole = format_to_string(0, 'C1' + iso_ident, '%s')
    symbole = symbole.replace(',', '')
    symbole = symbole.replace('.', '')
    symbole = symbole.replace('0', '')
    return symbole.strip()


def format_with_devise(mode):
    result = []
    currency_iso = Params.getvalue("accounting-devise-iso")
    currency_decimal = Params.getvalue("accounting-devise-prec")
    result.append('C%d%s' % (currency_decimal, currency_iso))
    if mode == 0:  # 25.45 => 25,45€ / -25.45 => / 0 =>
        result.append('%s')
        result.append('')
        result.append('')
    elif mode == 1:  # 25.45 => Credit: 25,45 € / -25.45 => Debit: 25,45 € / 0 => 0,00 €
        result.append('%s: %%s' % _('Credit'))
        result.append('%s: %%s' % _('Debit'))
        result.append('%s')
    elif mode == 2:  # 25.45 => {[font color="green"]}Credit: 25,45 €{[/font]} / -25.45 => {[font color="blue"]}Debit: 25,45 €{[/font]} / 0 => 0,00 €
        result.append('{[font color="green"]}%s: %%s{[/font]}' % _('Credit'))
        result.append('{[font color="blue"]}%s: %%s{[/font]}' % _('Debit'))
        result.append('%s')
    elif mode == 3:  # 25.45 => 25,45 / -25.45 => -25,45
        result[0] = 'N%d' % currency_decimal
        result.append('%s')
    elif mode == 4:  # 25.45 => 25,45 € / -25.45 => 25,45 € / 0 => 0,00 €
        result.append('%s')
        result.append('%s')
    elif mode == 5:  # 25.45 => 25,45 € / -25.45 => -25,45 € / 0 => 0,00 €
        result.append('%s')
    elif mode == 6:  # 25.45 => {[font color="green"]}25,45 €{[/font]} / -25.45 => {[font color="blue"]}25,45 €{[/font]} / 0 =>
        result.append('{[font color="green"]}%s{[/font]}')
        result.append('{[font color="blue"]}%s{[/font]}')
        result.append('')
    return ";".join(map(lambda item: "{[p align='right']}" + item + "{[/p]}" if ((item != '') and (currency_iso not in item) and (mode != 3)) else item, result))


def get_amount_from_format_devise(amount, mode):
    formatnum, formatstr = extract_format(format_with_devise(mode))
    return format_to_string(amount, formatnum, formatstr)
