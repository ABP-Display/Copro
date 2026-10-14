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
from os.path import dirname, join, isfile
from logging import getLogger
import sys

from django.db import models, migrations, transaction
from django.db.utils import IntegrityError
from django.conf import settings

from lucterios.CORE.models import PrintModel
from lucterios.framework.tools import set_locale_lang


def initial_values(apps, schema_editor):
    set_locale_lang(settings.LANGUAGE_CODE)
    legalentity = apps.get_model("contacts", "LegalEntity")
    current_entity = legalentity.objects.create(id=1, name="---", address='---',
                                                postal_code='00000', city='---', country='---')
    current_entity.save()

    PrintModel().load_model('lucterios.contacts', "LegalEntity_0001", is_default=True)
    PrintModel().load_model('lucterios.contacts', "LegalEntity_0002", is_default=True)
    PrintModel().load_model('lucterios.contacts', "Individual_0001", is_default=True)
    PrintModel().load_model('lucterios.contacts', "Individual_0002", is_default=True)


def save_postalcodes(postalcode, pc_list):
    try:
        with transaction.atomic():
            postalcode.objects.bulk_create(pc_list)
    except IntegrityError as err:
        getLogger(__name__).warning(
            str(" --- IntegrityError:") + str(err))
    return []


def import_file_postalcode(postalcode, migrat_file):
    import codecs
    pc_list = []
    if isfile(migrat_file):
        with codecs.open(migrat_file, 'r', 'utf-8') as flpc:
            for line in flpc.readlines():
                postal_code, city, country = str(line).split(';')[:3]
                newpc = postalcode()
                newpc.postal_code = str(postal_code).strip()
                newpc.city = str(city).strip()
                newpc.country = str(country).strip()
                pc_list.append(newpc)
                if len(pc_list) > 900:
                    pc_list = save_postalcodes(postalcode, pc_list)
    return pc_list


def initial_postalcodes(apps, schema_editor):
    postalcode = apps.get_model("contacts", "PostalCode")
    pcfile_list = ['postalcode_frDOMTOM.csv']
    if not (len(sys.argv) >= 2) or (sys.argv[1] != 'test'):
        pcfile_list.append("postalcode_ch.csv")
        pcfile_list.append("postalcode_fr01.csv")
        pcfile_list.append("postalcode_fr02.csv")
        pcfile_list.append("postalcode_fr03.csv")
        pcfile_list.append("postalcode_fr04.csv")
        pcfile_list.append("postalcode_fr05.csv")
        pcfile_list.append("postalcode_fr06.csv")
        pcfile_list.append("postalcode_fr07.csv")
        pcfile_list.append("postalcode_fr08.csv")
        pcfile_list.append("postalcode_fr09.csv")
        pcfile_list.append("postalcode_fr10.csv")
        pcfile_list.append("postalcode_fr11.csv")
        pcfile_list.append("postalcode_fr12.csv")
        pcfile_list.append("postalcode_fr13.csv")
        pcfile_list.append("postalcode_fr14.csv")
    pc_list = []
    migrat_dir = dirname(__file__)
    for pcfile in pcfile_list:
        pc_list.extend(
            import_file_postalcode(postalcode, join(migrat_dir, pcfile)))
    if len(pc_list) > 0:
        pc_list = save_postalcodes(postalcode, pc_list)


class Migration(migrations.Migration):

    dependencies = [
        (str("auth"), str("0001_initial")),
        (str("CORE"), str("0001_initial")),
    ]

    operations = [
        migrations.CreateModel(
            name='PostalCode',
            fields=[
                ('id', models.AutoField(
                    serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('postal_code', models.CharField(
                    max_length=10, blank=False, verbose_name='postal code')),
                ('city', models.CharField(
                    max_length=100, blank=False, verbose_name='city')),
                ('country', models.CharField(
                    max_length=100, blank=False, verbose_name='country')),
            ],
            options={
                'verbose_name_plural': 'postal codes',
                'verbose_name': 'postal code',
                'default_permissions': ['add', 'change'],
                'ordering': ['postal_code', 'city'],
                'unique_together': (('postal_code', 'city', 'country'),)
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Function',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(
                    unique=True, max_length=50, verbose_name='name')),
            ],
            options={
                'verbose_name_plural': 'individual functions',
                'verbose_name': 'individual function',
                'default_permissions': []
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='StructureType',
            fields=[
                ('id', models.AutoField(
                    primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(
                    unique=True, max_length=50, verbose_name='name')),
            ],
            options={
                'default_permissions': [],
                'verbose_name': 'structure type',
                'verbose_name_plural': 'structure types'
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CustomField',
            fields=[
                ('id', models.AutoField(
                    serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('modelname', models.CharField(
                    max_length=100, verbose_name='model')),
                ('name', models.CharField(
                    max_length=100, verbose_name='name')),
                ('kind', models.IntegerField(choices=[
                 (0, 'String'), (1, 'Integer'), (2, 'Real'), (3, 'Boolean'), (4, 'Select'), (5, 'Date')], verbose_name='kind')),
                ('args', models.CharField(
                    default='{}', max_length=200, verbose_name='arguments')),
            ],
            options={
                'default_permissions': [],
                'verbose_name_plural': 'custom fields',
                'verbose_name': 'custom field',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AbstractContact',
            fields=[
                ('id', models.AutoField(
                    serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('address', models.TextField(
                    verbose_name='address', blank=False)),
                ('postal_code', models.CharField(
                    max_length=10, verbose_name='postal code', blank=False)),
                ('city', models.CharField(
                    max_length=100, verbose_name='city', blank=False)),
                ('country', models.CharField(
                    max_length=100, verbose_name='country', blank=True)),
                ('tel1', models.CharField(
                    max_length=15, blank=True, verbose_name='tel1')),
                ('tel2', models.CharField(
                    max_length=15, blank=True, verbose_name='tel2')),
                ('email', models.EmailField(
                    max_length=254, blank=True, verbose_name='email')),
                ('comment', models.TextField(
                    blank=True, verbose_name='comment')),
            ],
            options={'verbose_name': 'generic contact',
                     'verbose_name_plural': 'generic contacts'},
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContactCustomField',
            fields=[
                ('id', models.AutoField(
                    serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('value', models.TextField(verbose_name='value', default='')),
                ('contact', models.ForeignKey(
                    to='contacts.AbstractContact', verbose_name='contact', on_delete=models.CASCADE)),
                ('field', models.ForeignKey(
                    to='contacts.CustomField', verbose_name='field', on_delete=models.CASCADE)),
            ],
            options={
                'default_permissions': [],
                'verbose_name_plural': 'custom field values',
                'verbose_name': 'custom field value',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LegalEntity',
            fields=[
                ('abstractcontact_ptr', models.OneToOneField(auto_created=True,
                                                             to='contacts.AbstractContact', serialize=False, parent_link=True, primary_key=True, on_delete=models.CASCADE)),
                ('name', models.CharField(max_length=100, verbose_name='denomination')),
                ('identify_number', models.CharField(
                    max_length=100, blank=True, verbose_name='identify number')),
                ('structure_type', models.ForeignKey(on_delete=models.deletion.SET_NULL,
                                                     to='contacts.StructureType', verbose_name='structure type', null=True)),
            ],
            options={'verbose_name': 'legal entity', 'default_permissions': [
            ], 'verbose_name_plural': 'legal entities', 'ordering': ['name']},
            bases=('contacts.abstractcontact',),
        ),
        migrations.CreateModel(
            name='Individual',
            fields=[
                ('abstractcontact_ptr', models.OneToOneField(auto_created=True, on_delete=models.CASCADE,
                                                             to='contacts.AbstractContact', serialize=False, parent_link=True, primary_key=True)),
                ('firstname', models.CharField(
                    max_length=50, verbose_name='firstname')),
                ('lastname', models.CharField(
                    max_length=50, verbose_name='lastname')),
                ('genre', models.IntegerField(
                    default=1, choices=[(1, 'Man'), (2, 'Woman')], blank=False)),
                ('user', models.ForeignKey(to='CORE.LucteriosUser', null=True,
                                           on_delete=models.deletion.SET_NULL, verbose_name='user')),
            ],
            options={'verbose_name': 'individual', 'default_permissions': [
            ], 'verbose_name_plural': 'individuals', 'ordering': ['lastname', 'firstname']},
            bases=('contacts.abstractcontact',),
        ),
        migrations.CreateModel(
            name='Responsability',
            fields=[
                ('id', models.AutoField(
                    serialize=False, auto_created=True, verbose_name='ID', primary_key=True)),
                ('functions', models.ManyToManyField(
                    blank=True, verbose_name='functions', to='contacts.Function')),
                ('individual', models.ForeignKey(on_delete=models.CASCADE,
                                                 verbose_name='individual', to='contacts.Individual')),
                ('legal_entity', models.ForeignKey(on_delete=models.CASCADE,
                                                   verbose_name='legal entity', to='contacts.LegalEntity')),
            ],
            options={'verbose_name': 'associate', 'verbose_name_plural': 'associates'},
            bases=(models.Model,),
        ),
        migrations.RunPython(initial_postalcodes),
        migrations.RunPython(initial_values),
    ]
