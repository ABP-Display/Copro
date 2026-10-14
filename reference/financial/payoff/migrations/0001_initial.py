# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
from lucterios.framework.model_fields import LucteriosDecimalField


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Supporting',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('third', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                            null=True, to='accounting.Third', default=None, verbose_name='third')),
                ('is_revenu', models.BooleanField(
                    default=True, verbose_name='is revenu')),
            ],
            options={
                'verbose_name_plural': 'supporting',
                'verbose_name': 'supporting',
                'default_permissions': []
            },
        ),
        migrations.CreateModel(
            name='BankAccount',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('designation', models.TextField(verbose_name='designation')),
                ('reference', models.CharField(
                    max_length=200, verbose_name='reference')),
                ('account_code', models.CharField(
                    max_length=50, verbose_name='account code')),
            ],
            options={
                'verbose_name_plural': 'bank accounts',
                'verbose_name': 'bank account',
            },
        ),
        migrations.CreateModel(
            name='Payoff',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('supporting', models.ForeignKey(
                    to='payoff.Supporting', verbose_name='supporting', on_delete=models.CASCADE)),
                ('date', models.DateField(verbose_name='date')),
                ('amount', LucteriosDecimalField(decimal_places=3, max_digits=10, validators=[django.core.validators.MinValueValidator(
                    0.0), django.core.validators.MaxValueValidator(9999999.999)], verbose_name='amount', default=0.0)),
                ('mode', models.IntegerField(choices=[(0, 'cash'), (1, 'cheque'), (2, 'transfer'), (
                    3, 'crédit card'), (4, 'other')], default=0, verbose_name='mode', db_index=True)),
                ('payer', models.CharField(
                    verbose_name='payer', max_length=150, null=True, default='')),
                ('reference', models.CharField(
                    verbose_name='reference', max_length=100, null=True, default='')),
                ('entry', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                            to='accounting.EntryAccount', default=None, verbose_name='entry')),
                ('bank_account', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT,
                                                   to='payoff.BankAccount', default=None, verbose_name='bank account')),
            ],
            options={
                'verbose_name_plural': 'payoffs',
                'verbose_name': 'payoff',
            },
        ),
        migrations.CreateModel(
            name='DepositSlip',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.IntegerField(db_index=True, choices=[
                 (0, 'building deposit'), (1, 'closed deposit'), (2, 'valid deposit')], verbose_name='status', default=0)),
                ('date', models.DateField(verbose_name='date')),
                ('reference', models.CharField(
                    null=False, verbose_name='reference', max_length=100, default='')),
                ('bank_account', models.ForeignKey(to='payoff.BankAccount', verbose_name='bank account',
                                                   on_delete=django.db.models.deletion.PROTECT, null=False)),
            ],
            options={
                'verbose_name_plural': 'deposit slips',
                'verbose_name': 'deposit slip',
            },
        ),
        migrations.CreateModel(
            name='DepositDetail',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deposit', models.ForeignKey(to='payoff.DepositSlip', verbose_name='deposit',
                                              on_delete=django.db.models.deletion.CASCADE, null=True, default=None)),
                ('payoff', models.ForeignKey(to='payoff.Payoff', verbose_name='payoff',
                                             on_delete=django.db.models.deletion.PROTECT, null=True, default=None)),
            ],
            options={
                'verbose_name_plural': 'deposit details',
                'verbose_name': 'deposit detail',
                'default_permissions': []
            },
        ),
    ]
