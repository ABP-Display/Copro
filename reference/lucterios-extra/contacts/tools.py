# -*- coding: utf-8 -*-
'''
lucterios.contacts package

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
from django.apps import apps

from lucterios.contacts.models import AbstractContact
from lucterios.framework.xfersearch import XferSearchEditor
from lucterios.framework.xfercomponents import XferCompSelect
from lucterios.framework.tools import FORMTYPE_REFRESH, CLOSE_NO, CLOSE_YES, SELECT_SINGLE
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor
from lucterios.framework.xferadvance import TITLE_OK


class ContactSelection(XferSavedCriteriaSearchEditor):
    model = AbstractContact
    inital_model = AbstractContact
    field_id = 'abstractcontact'
    caption = _("Select contact")
    mode_select = SELECT_SINGLE
    select_class = None
    final_class = None

    def fillresponse(self):
        self.action_list = []
        if self.final_class is not None:
            self.add_action(self.final_class.get_action(TITLE_OK, short_icon='mdi:mdi-check'))
        model_current = self.getparam('modelname')
        if model_current is None:
            self.model = self.inital_model
        else:
            self.model = apps.get_model(model_current)
        self.field_id = self.model.__name__.lower()
        if self.field_id == 'legalentity':
            self.field_id = 'legal_entity'
        self.item = self.model()
        XferSearchEditor.fillresponse(self)
        self.remove_component('title')
        selected_model = XferCompSelect('modelname')
        selected_model.set_value(model_current)
        selected_model.set_select(self.inital_model.get_select_contact_type())
        selected_model.set_location(1, 0, 4)
        selected_model.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        selected_model.description = _('model')
        self.add_component(selected_model)
        if self.select_class is not None:
            grid = self.get_components(self.field_id)
            grid.add_action(self.request, self.select_class.get_action(_("Select"), short_icon='mdi:mdi-check'),
                            close=CLOSE_YES, unique=self.mode_select, params={'pkname': self.field_id}, pos_act=0)
