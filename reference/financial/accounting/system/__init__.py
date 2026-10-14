# -*- coding: utf-8 -*-
'''
diacamma.accounting.system package

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
from django.utils.module_loading import import_module


def accounting_system_list():
    res = {}
    res['diacamma.accounting.system.french.FrenchSystemAcounting'] = _('French system acounting')
    res['diacamma.accounting.system.belgium.BelgiumSystemAcounting'] = _('Belgium system acounting')
    res['diacamma.accounting.system.morocco.MoroccoSystemAcounting'] = _('Morocco system acounting')
    return res


def accounting_system_name(complete_name):
    sys_list = accounting_system_list()
    if complete_name in sys_list.keys():
        return sys_list[complete_name]
    else:
        return "---"


def accounting_system_ident(complete_name):
    modules_long = complete_name.split('.')
    sys_list = accounting_system_list()
    if (complete_name in sys_list.keys()) and (len(modules_long) == 5):
        return modules_long[3]
    else:
        return "---"


def get_accounting_system(complete_name):
    sys_list = accounting_system_list()
    if complete_name in sys_list.keys():
        modules_long = complete_name.split('.')
        module_name = ".".join(modules_long[:-1])
        class_name = modules_long[-1]
        try:
            module_sys = import_module(module_name)
            class_sys = getattr(module_sys, class_name)
            return class_sys()
        except (ImportError, AttributeError):
            pass
    from diacamma.accounting.system.default import DefaultSystemAccounting
    return DefaultSystemAccounting()
