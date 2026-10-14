# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations
from django.db.models import deletion

from lucterios.CORE.models import PrintModel
from lucterios.framework.tools import set_locale_lang


def addons_values(apps, schema_editor):
    set_locale_lang(settings.LANGUAGE_CODE)
    PrintModel().load_model("lucterios.mailing", "Message_0001", is_default=True)


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(
                    auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('subject', models.CharField(
                    max_length=50, verbose_name='subject')),
                ('body', models.TextField(default='', verbose_name='body')),
                ('status', models.IntegerField(
                    verbose_name='status', default=0, choices=[(0, 'open'), (1, 'close')])),
                ('recipients', models.TextField(
                    default='', null=False, verbose_name='recipients')),
                ('date', models.DateField(null=True, verbose_name='date')),
                ('contact', models.ForeignKey(on_delete=deletion.SET_NULL,
                                              verbose_name='contact', null=True, to='contacts.AbstractContact')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(addons_values),
    ]
