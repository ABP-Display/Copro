# -*- coding: utf-8 -*-
'''
Printmodel django module for accounting

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2016 sd-libre.fr
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

from diacamma.accounting.models import ChartsAccount

name = _("listing")
kind = 0
modelname = ChartsAccount.get_long_name()
value = """210
297
10//%s//#code
25//%s//#name
15//%s//#last_year_total
15//%s//#current_total
15//%s//#current_validated
""" % (_('code'), _('name'), _("total of last year"), _('total current'), _('total validated'))
