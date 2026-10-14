# -*- coding: utf-8 -*-
'''
Unit tests for contacts viewer

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
from shutil import rmtree

from lucterios.framework.filetools import get_user_dir

from lucterios.contacts.models import LegalEntity, Individual, StructureType, Function


def change_contact(contact, **field_values):
    for field_name, field_value in field_values.items():
        if hasattr(contact, field_name):
            if field_name[:7] == "custom_":
                contact.set_custom_values({field_name: field_value})
            else:
                setattr(contact, field_name, field_value)
    contact.save()


def change_ourdetail(**field_values):
    ourdetails = LegalEntity.objects.get(id=1)
    ourdetails.name = "WoldCompany"
    change_contact(ourdetails, address="Place des cocotiers", postal_code="97200", city="FORT DE FRANCE",
                   country="MARTINIQUE", tel1="01-23-45-67-89", email="mr-sylvestre@worldcompany.com", **field_values)


def create_jack(empty_user=None, firstname="jack", lastname="MISTER", with_email=True, **field_values):
    empty_contact = Individual()
    empty_contact.firstname = firstname
    empty_contact.lastname = lastname
    empty_contact.user = empty_user
    if with_email:
        empty_contact.email = "%s@worldcompany.com" % firstname
    empty_contact.save()
    change_contact(empty_contact, address="rue de la liberté", postal_code="97250", city="LE PRECHEUR",
                   country="MARTINIQUE", tel2="02-78-45-12-95", **field_values)
    return empty_contact


def initial_contact(empty_user=None):
    change_ourdetail()
    rmtree(get_user_dir(), True)
    StructureType.objects.create(name="Type A")
    StructureType.objects.create(name="Type B")
    StructureType.objects.create(name="Type C")
    Function.objects.create(name="President")
    Function.objects.create(name="Secretaire")
    Function.objects.create(name="Tresorier")
    Function.objects.create(name="Troufion")
    return create_jack(empty_user)
