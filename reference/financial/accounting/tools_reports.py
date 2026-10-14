# -*- coding: utf-8 -*-
'''
Describe report accounting viewer for Django

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

from django.db.models import Q
from django.db.models.aggregates import Sum

from diacamma.accounting.models import EntryLineAccount, ChartsAccount, Budget, Third
from diacamma.accounting.tools import correct_accounting_code


def get_spaces(size):
    return '&#160;' * size


def credit_debit_way(data_line):
    if 'account' in data_line.keys():
        account = ChartsAccount.objects.get(id=data_line['account'])
        return account.credit_debit_way()
    elif 'code' in data_line.keys():
        account_code = correct_accounting_code(data_line['code'])
        account = ChartsAccount.get_chart_account(account_code)
        return account.credit_debit_way()
    return 0


def get_totalaccount_for_query(query, sign_value=None, with_third=False):
    total = 0
    values = {}
    if with_third:
        fields = ['account', 'third']
    else:
        fields = ['account']
    for data_line in EntryLineAccount.objects.filter(query).order_by(*fields).values(*fields).annotate(data_sum=Sum('amount')):
        if abs(data_line['data_sum']) > 0.001:
            account = ChartsAccount.objects.get(id=data_line['account'])
            account_code = correct_accounting_code(account.code)
            if ('third' in data_line.keys()) and (data_line['third'] is not None):
                account_code = "%s#%s" % (account_code, data_line['third'])
                third = Third.objects.get(id=data_line['third'])
                account_title = "[%s %s]" % (account.code, str(third))
            else:
                account_title = account.get_name()
            amount = None
            if sign_value is None:
                amount = data_line['data_sum']
            elif isinstance(sign_value, bool):
                if sign_value:
                    amount = credit_debit_way(data_line) * data_line['data_sum']
                else:
                    amount = -1 * credit_debit_way(data_line) * data_line['data_sum']
            else:
                amount = sign_value * credit_debit_way(data_line) * data_line['data_sum']
                if (amount < 0):
                    amount = None
            if amount is not None:
                if account_code not in values.keys():
                    values[account_code] = [0, account_title]
                values[account_code][0] += amount
                total += amount
    return values, total


def get_account_total(query, account_codethird, sign_value=None):
    total = 0
    account_code_and_third = account_codethird.split('#')
    if len(account_code_and_third) == 2:
        extra_filter = Q(account__code=account_code_and_third[0]) & Q(third_id=int(account_code_and_third[1]))
    else:
        extra_filter = Q(account__code=account_code_and_third[0])
    for data_line in EntryLineAccount.objects.filter(query & extra_filter).order_by('account').values('account').annotate(data_sum=Sum('amount')):
        if abs(data_line['data_sum']) > 0.001:
            amount = None
            if sign_value is None:
                amount = data_line['data_sum']
            elif isinstance(sign_value, bool):
                if sign_value:
                    amount = credit_debit_way(data_line) * data_line['data_sum']
                else:
                    amount = -1 * credit_debit_way(data_line) * data_line['data_sum']
            else:
                amount = sign_value * credit_debit_way(data_line) * data_line['data_sum']
                if (amount < 0):
                    amount = None
            if amount is not None:
                total += amount
    return total


def get_budget_total(query, account_codethird, sign_value=None):
    total = 0
    account_code_and_third = account_codethird.split('#')
    extra_filter = Q(code=account_code_and_third[0])
    for data_line in Budget.objects.filter(query & extra_filter).order_by('code').values('code').annotate(data_sum=Sum('amount')):
        if abs(data_line['data_sum']) > 0.001:
            amount = None
            if sign_value is None:
                amount = data_line['data_sum']
            elif isinstance(sign_value, bool):
                if sign_value:
                    amount = credit_debit_way(data_line) * data_line['data_sum']
                else:
                    amount = -1 * credit_debit_way(data_line) * data_line['data_sum']
            else:
                amount = sign_value * credit_debit_way(data_line) * data_line['data_sum']
                if (amount < 0):
                    amount = None
            if amount is not None:
                total += amount
    return total


def add_account_without_amount(dict_account, query1, query2, query_budget_list, sign_value):
    extra_account = ~Q(code__in=[account_codethird.split('#')[0] for account_codethird in dict_account.keys()])
    for item in query1.children:
        if isinstance(item, tuple) and (item[0].startswith('account__') or (item[0] == 'entry__year')):
            extra_account &= Q(**{'__'.join(item[0].split('__')[1:]): item[1]})
    total2 = 0
    if query_budget_list is not None:
        total3_initial = [0 for _item in query_budget_list]
    else:
        total3_initial = [0]
    total3 = total3_initial[:]
    account_codes = []
    for account in ChartsAccount.objects.filter(extra_account).order_by('-year_id'):
        if account.code not in account_codes:
            account_codes.append(account.code)
        else:
            continue
        value2 = 0
        total_b = []
        if query2 is not None:
            value2 = get_account_total(query2, account.code, sign_value)
        if query_budget_list is not None:
            for query_budget_item in query_budget_list:
                total_b.append(get_budget_total(query_budget_item, account.code, sign_value))

        if (value2 != 0) or ((total_b != []) and (total_b != total3_initial)):
            dict_account[account.code] = [str(account), None, None] + total3_initial
            if abs(value2) > 0.001:
                dict_account[account.code][2] = value2
            total2 += value2
            if query_budget_list is not None:
                for budget_item_idx in range(len(query_budget_list)):
                    if abs(total_b[budget_item_idx]) > 0.001:
                        dict_account[account.code][budget_item_idx + 3] = total_b[budget_item_idx]
                        total3[budget_item_idx] += total_b[budget_item_idx]

    return total2, total3


def convert_query_to_account(query1, query2=None, query_budget=None, sign_value=None, with_third=False, old_accountcode=None):
    def check_account(account_code, account_title):
        if account_code not in dict_account.keys():
            dict_account[account_code] = [account_title, None, None]
            if isinstance(query_budget, list):
                for _item in query_budget:
                    dict_account[account_code].append(None)
            else:
                dict_account[account_code].append(None)
    if query_budget is not None:
        if isinstance(query_budget, list):
            query_budget_list = query_budget
        else:
            query_budget_list = [query_budget]
    else:
        query_budget_list = None
    dict_account = {}
    total2 = 0
    total3 = 0 if not isinstance(query_budget, list) else [0 for _item in query_budget_list]
    values1, total1 = get_totalaccount_for_query(query1, sign_value, with_third)
    for account_code in values1.keys():
        check_account(account_code, values1[account_code][1])
        dict_account[account_code][1] = values1[account_code][0]
        if query2 is not None:
            value2 = get_account_total(query2, account_code, sign_value)
            if abs(value2) > 0.001:
                dict_account[account_code][2] = value2
            total2 += value2
        if query_budget_list is not None:
            total_b = []
            id_dict = 3
            for query_budget_item in query_budget_list:
                valueb = get_budget_total(query_budget_item, account_code)
                if abs(valueb) > 0.001:
                    dict_account[account_code][id_dict] = valueb
                total_b.append(valueb)
                id_dict += 1
            if isinstance(query_budget, list):
                total3 = [total3[budget_item_idx] + total_b[budget_item_idx] for budget_item_idx in range(len(query_budget_list))]
            else:
                total3 += total_b[0]
    if (query2 is not None) or (query_budget is not None):
        total_2, total_3 = add_account_without_amount(dict_account, query1, query2, query_budget_list, sign_value)
        total2 += total_2
        if isinstance(query_budget, list):
            total3 = [total3[budget_item_idx] + total_3[budget_item_idx] for budget_item_idx in range(len(query_budget_list))]
        else:
            total3 += total_3[0]
    if (query2 is not None) and (old_accountcode is not None):
        old_accountcode.extend(dict_account.keys())
        values_2, total_2 = get_totalaccount_for_query(query2 & ~Q(account__code__in=[account_codethird.split('#')[0] for account_codethird in old_accountcode]), sign_value, with_third)
        sub_total2 = 0.0
        for account_code in values_2.keys():
            check_account(account_code, values_2[account_code][1])
            dict_account[account_code][2] = values_2[account_code][0]
            sub_total2 += values_2[account_code][0]
        total2 += total_2
    res = []
    account_codes = sorted(dict_account.keys())
    for account_code in account_codes:
        res.append(dict_account[account_code])
    return res, total1, total2, total3, account_codes


def add_cell_in_grid(grid, line_idx, colname, value, formttext='%s', line_ident=0):
    if value is None:
        return
    if formttext != '%s':
        grid.set_value("L%04d-%d" % (line_idx, line_ident), colname, {'value': value, 'format': formttext.replace('%s', '{0}')})
    else:
        grid.set_value("L%04d-%d" % (line_idx, line_ident), colname, value)


def add_item_in_grid(grid, line_idx, side, data_item, formttext='%s'):
    add_cell_in_grid(grid, line_idx, side, data_item[0], formttext)
    add_cell_in_grid(grid, line_idx, side + '_n', data_item[1], formttext)
    if data_item[2] is not None:
        add_cell_in_grid(grid, line_idx, side + '_n_1', data_item[2], formttext)
    if data_item[3] is not None:
        add_cell_in_grid(grid, line_idx, side + '_b', data_item[3], formttext)


def fill_grid(grid, index_begin, side, data_line):
    line_idx = index_begin
    for data_item in data_line:
        add_item_in_grid(grid, line_idx, side, data_item)
        line_idx += 1
    return line_idx
