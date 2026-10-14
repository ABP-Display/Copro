# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
'''
Initial django functions

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
from django.db.models.deletion import PROTECT, SET_NULL
from django.db import models, migrations
from django.conf import settings

from lucterios.CORE.models import PrintModel
from lucterios.framework.tools import set_locale_lang


def initial_values(*args):
    set_locale_lang(settings.LANGUAGE_CODE)

    PrintModel().load_model('diacamma.accounting', "Third_0001", is_default=True)
    PrintModel().load_model('diacamma.accounting', "ChartsAccount_0001", is_default=True)
    PrintModel().load_model('diacamma.accounting', "EntryLineAccount_0001", is_default=True)


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Third',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('status', models.IntegerField(
                    choices=[(0, 'Enable'), (1, 'Disable')], verbose_name='status')),
                ('contact', models.ForeignKey(
                    verbose_name='contact', to='contacts.AbstractContact', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'third',
                'verbose_name_plural': 'thirds',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AccountThird',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('code', models.CharField(max_length=50, verbose_name='code')),
                ('third', models.ForeignKey(
                    verbose_name='third', to='accounting.Third', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'account',
                'default_permissions': [],
                'verbose_name_plural': 'accounts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FiscalYear',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('begin', models.DateField(verbose_name='begin')),
                ('end', models.DateField(verbose_name='end')),
                ('status', models.IntegerField(verbose_name='status', choices=[(0, 'building year'), (1, 'running year'), (2, 'finished year')], default=0)),
                ('is_actif', models.BooleanField(verbose_name='actif', default=False, db_index=True)),
                ('last_fiscalyear', models.ForeignKey(to='accounting.FiscalYear', verbose_name='last fiscal year', related_name='next_fiscalyear',
                                                      null=True, on_delete=models.SET_NULL)),
            ],
            options={
                'verbose_name_plural': 'fiscal years',
                'verbose_name': 'fiscal year',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ChartsAccount',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('code', models.CharField(
                    verbose_name='code', max_length=50, db_index=True)),
                ('name', models.CharField(
                    verbose_name='name', max_length=200)),
                ('type_of_account', models.IntegerField(verbose_name='type of account',
                                                        choices=[(0, 'Asset'), (1, 'Liability'), (2, 'Equity'), (3, 'Revenue'), (4, 'Expense'), (5, 'Contra-accounts')], null=True, db_index=True)),
                ('year', models.ForeignKey(verbose_name='fiscal year',
                                           to='accounting.FiscalYear', on_delete=models.CASCADE, db_index=True)),
            ],
            options={
                'verbose_name': 'charts of account',
                'verbose_name_plural': 'charts of accounts',
                'ordering': ['year', 'code']
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Journal',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', auto_created=True, serialize=False, primary_key=True)),
                ('name', models.CharField(
                    max_length=50, verbose_name='name', unique=True)),
            ],
            options={
                'default_permissions': [],
                'verbose_name': 'accounting journal',
                'verbose_name_plural': 'accounting journals',
            },
        ),
        migrations.CreateModel(
            name='AccountLink',
            fields=[
                ('id', models.AutoField(
                    serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
            ],
            options={
                'verbose_name_plural': 'letters',
                'verbose_name': 'letter',
                'default_permissions': [],
            },
        ),
        migrations.CreateModel(
            name='CostAccounting',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(
                    verbose_name='name', unique=True, max_length=50)),
                ('description', models.CharField(
                    verbose_name='description', max_length=50)),
                ('status', models.IntegerField(
                    verbose_name='status', choices=[(0, 'opened'), (1, 'closed')], default=0)),
                ('last_costaccounting', models.ForeignKey(null=True, verbose_name='last cost accounting',
                                                          to='accounting.CostAccounting', related_name='next_costaccounting', on_delete=SET_NULL)),
                ('is_default', models.BooleanField(
                    verbose_name=_('default'), default=False)),
            ],
            options={
                'verbose_name': 'cost accounting',
                'verbose_name_plural': 'costs accounting',
                'default_permissions': [],
            },
        ),
        migrations.CreateModel(
            name='EntryAccount',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('num', models.IntegerField(
                    verbose_name='numeros', null=True)),
                ('journal', models.ForeignKey(
                    verbose_name='journal', to='accounting.Journal', default=0, on_delete=PROTECT)),
                ('link', models.ForeignKey(verbose_name='link',
                                           to='accounting.AccountLink', null=True, on_delete=SET_NULL)),
                ('date_entry', models.DateField(
                    verbose_name='date entry', null=True)),
                ('date_value', models.DateField(
                    verbose_name='date value', null=False, db_index=True)),
                ('designation', models.CharField(
                    verbose_name='name', max_length=200)),
                ('close', models.BooleanField(
                    verbose_name='close', default=False, db_index=True)),
                ('year', models.ForeignKey(verbose_name='fiscal year',
                                           to='accounting.FiscalYear', on_delete=models.CASCADE)),
                ('costaccounting', models.ForeignKey(verbose_name='cost accounting',
                                                     to='accounting.CostAccounting', on_delete=PROTECT, null=True)),
            ],
            options={
                'verbose_name': 'entry of account',
                'verbose_name_plural': 'entries of account',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntryLineAccount',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('amount', models.FloatField(
                    verbose_name='amount', db_index=True)),
                ('reference', models.CharField(
                    verbose_name='reference', max_length=100, null=True)),
                ('account', models.ForeignKey(verbose_name='account',
                                              to='accounting.ChartsAccount', on_delete=models.PROTECT)),
                ('entry', models.ForeignKey(
                    verbose_name='entry', to='accounting.EntryAccount', on_delete=models.CASCADE)),
                ('third', models.ForeignKey(null=True, verbose_name='third',
                                            to='accounting.Third', on_delete=models.PROTECT, db_index=True)),
            ],
            options={
                'default_permissions': [],
                'ordering': ['entry__date_value', 'entry_id', 'account__code', 'third'],
                'verbose_name': 'entry line of account',
                'verbose_name_plural': 'entry lines of account',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ModelEntry',
            fields=[
                ('id', models.AutoField(
                    primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('designation', models.CharField(
                    max_length=200, verbose_name='name')),
                ('journal', models.ForeignKey(to='accounting.Journal',
                                              default=0, verbose_name='journal', on_delete=models.PROTECT)),
            ],
            options={
                'verbose_name_plural': 'Models of entry',
                'verbose_name': 'Model of entry',
                'default_permissions': [],
            },
        ),
        migrations.CreateModel(
            name='ModelLineEntry',
            fields=[
                ('id', models.AutoField(
                    primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('code', models.CharField(max_length=50, verbose_name='code')),
                ('amount', models.FloatField(
                    verbose_name='amount', default=0)),
                ('model', models.ForeignKey(
                    default=0, verbose_name='model', to='accounting.ModelEntry', on_delete=models.CASCADE)),
                ('third', models.ForeignKey(to='accounting.Third',
                                            verbose_name='third', on_delete=models.PROTECT, null=True)),
            ],

            options={
                'verbose_name_plural': 'Model lines',
                'verbose_name': 'Model line',
                'default_permissions': [],
            },
        ),
        migrations.RunPython(initial_values),
    ]
