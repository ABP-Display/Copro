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
from os.path import dirname, join
import sys

from django.db import migrations
from django.utils.module_loading import import_module


def addon_postalcodes(apps, schema_editor):
    init_module = import_module("lucterios.contacts.migrations.0001_initial")
    import_file_postalcode = getattr(init_module, "import_file_postalcode")
    save_postalcodes = getattr(init_module, "save_postalcodes")
    postalcode = apps.get_model("contacts", "PostalCode")
    pcfile_list = []
    if not (len(sys.argv) >= 2) or (sys.argv[1] != 'test'):
        pcfile_list.append("postalcode_be.csv")
    pc_list = []
    migrat_dir = dirname(__file__)
    for pcfile in pcfile_list:
        pc_list.extend(
            import_file_postalcode(postalcode, join(migrat_dir, pcfile)))
    if len(pc_list) > 0:
        pc_list = save_postalcodes(postalcode, pc_list)


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(addon_postalcodes),
    ]
