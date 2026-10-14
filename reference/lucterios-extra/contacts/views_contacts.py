# -*- coding: utf-8 -*-
'''
Viewer of legal entity, individual and responsability actions

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
from django.db.models import Q
from django.apps.registry import apps
from django.conf import settings

from lucterios.framework.tools import MenuManage, WrapAction, ActionsManage, SELECT_MULTI
from lucterios.framework.tools import FORMTYPE_NOMODAL, FORMTYPE_REFRESH, CLOSE_NO, FORMTYPE_MODAL, CLOSE_YES, SELECT_SINGLE
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge, XFER_DBOX_WARNING
from lucterios.framework.xferadvance import XferAddEditor, XferDelete, XferShowEditor, XferListEditor, XferSave, \
    TITLE_ADD, TITLE_MODIFY, TITLE_EDIT, TITLE_PRINT, TITLE_DELETE, TITLE_LABEL, \
    TITLE_LISTING, TITLE_CREATE, TITLE_CANCEL
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompEdit, XferCompImage, XferCompGrid, \
    XferCompButton
from lucterios.framework.xfersearch import XferSearchEditor
from lucterios.framework import signal_and_lock

from lucterios.CORE.editors import XferSavedCriteriaSearchEditor
from lucterios.CORE.models import LucteriosUser
from lucterios.CORE.xferprint import XferPrintAction, XferPrintListing, XferPrintLabel
from lucterios.CORE.views import ObjectMerge, ObjectPromote

from lucterios.contacts.models import LegalEntity, Individual, Responsability, AbstractContact
from lucterios.CORE.parameters import Params


MenuManage.add_sub("office", None, short_icon='mdi:mdi-monitor', caption=_("Office"), desc=_("Office tools"), pos=70)

MenuManage.add_sub("contact.actions", "office", short_icon='mdi:mdi-account-outline', caption=_("Addresses and contacts"), desc=_("Management of men or women and organizations saved."), pos=50)


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus')
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', close=CLOSE_YES)
@MenuManage.describ('contacts.add_abstractcontact')
class LegalEntityAddModify(XferAddEditor):
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'
    caption_add = _("Add legal entity")
    caption_modify = _("Modify legal entity")


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('contacts.change_abstractcontact')
class LegalEntityShow(XferShowEditor):
    caption = _("Show legal entity")
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'

    def _search_model(self):
        if self.getparam(self.field_id, 0) == 0:
            self.params[self.field_id] = self.getparam('legalentity', '0')
        XferShowEditor._search_model(self)


@ActionsManage.affect_show(TITLE_PRINT, short_icon='mdi:mdi-printer-outline')
@MenuManage.describ('contacts.change_abstractcontact')
class LegalEntityPrint(XferPrintAction):
    caption = _("Show legal entity")
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'
    action_class = LegalEntityShow


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('contacts.delete_abstractcontact')
class LegalEntityDel(XferDelete):
    caption = _("Delete legal entity")
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('Management of a structure or organization of people (company, association, administration, ...)'))
class LegalEntityList(XferListEditor):
    caption = _("Legal entities")
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'

    def __init__(self, **kwargs):
        XferListEditor.__init__(self, **kwargs)
        self.size_by_page = Params.getvalue("contacts-size-page")

    def fillresponse_header(self):
        self.fill_from_model(0, 2, False, ['structure_type'])
        obj_strtype = self.get_components('structure_type')
        obj_strtype.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            self.filter = Q(structure_type=int(structure_type))

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 2)


@ActionsManage.affect_list(TITLE_LISTING, short_icon='mdi:mdi-printer-pos-edit-outline')
@MenuManage.describ('contacts.change_abstractcontact')
class LegalEntityListing(XferPrintListing):
    caption = _("Legal entities")
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'

    def get_filter(self):
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            return Q(structure_type=int(structure_type))
        else:
            return XferPrintListing.get_filter(self)


@ActionsManage.affect_list(TITLE_LABEL, short_icon='mdi:mdi-printer-pos-star-outline')
@MenuManage.describ('contacts.change_abstractcontact')
class LegalEntityLabel(XferPrintLabel):
    caption = _("Legal entities")
    short_icon = "mdi:mdi-account-multiple-outline"
    model = LegalEntity
    field_id = 'legal_entity'

    def get_filter(self):
        structure_type = self.getparam('structure_type')
        if (structure_type is not None) and (structure_type != '0'):
            return [Q(structure_type=int(structure_type))]
        else:
            return XferPrintLabel.get_filter(self)


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus')
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', close=CLOSE_YES)
@MenuManage.describ('contacts.add_abstractcontact')
class IndividualAddModify(XferAddEditor):
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'
    caption_add = _("Add individual")
    caption_modify = _("Modify individual")


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualShow(XferShowEditor):
    caption = _("Show individual")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualShowResp(XferContainerAcknowledge):
    caption = _("Show individual")
    short_icon = "mdi:mdi-account-outline"
    model = Responsability
    field_id = 'responsability'
    readonly = True
    methods_allowed = ('GET', )

    def fillresponse(self):
        self.redirect_action(IndividualShow.get_action('', ''),
                             close=CLOSE_NO, params={'individual': str(self.item.individual_id)})


@ActionsManage.affect_show(TITLE_PRINT, short_icon='mdi:mdi-printer-outline')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualPrint(XferPrintAction):
    caption = _("Show individual")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'
    action_class = IndividualShow


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('contacts.delete_abstractcontact')
class IndividualDel(XferDelete):
    caption = _("Delete individual")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('Management of men and women registered'))
class IndividualList(XferListEditor):
    caption = _("Individuals")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'

    def __init__(self, **kwargs):
        XferListEditor.__init__(self, **kwargs)
        self.size_by_page = Params.getvalue("contacts-size-page")

    def fillresponse_header(self):
        name_filter = self.getparam('filter')
        if name_filter is None:
            name_filter = ""
        comp = XferCompEdit('filter')
        comp.set_value(name_filter)
        comp.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        comp.set_location(0, 2)
        comp.is_default = True
        comp.description = _('Filtrer by name')
        self.add_component(comp)
        if name_filter != "":
            self.filter = Q(firstname__icontains=name_filter) | Q(
                lastname__icontains=name_filter)

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 2)


@ActionsManage.affect_list(TITLE_LABEL, short_icon='mdi:mdi-printer-pos-star-outline')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualLabel(XferPrintLabel):
    caption = _("Individuals")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'

    def get_filter(self):
        name_filter = self.getparam('filter')
        if (name_filter is not None) and (name_filter != ""):
            return [Q(firstname__icontains=name_filter) | Q(lastname__icontains=name_filter)]
        else:
            return XferPrintLabel.get_filter(self)


@ActionsManage.affect_list(TITLE_LISTING, short_icon='mdi:mdi-printer-pos-edit-outline')
@MenuManage.describ('contacts.change_abstractcontact')
class IndividualListing(XferPrintListing):
    caption = _("Individuals")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'
    with_text_export = True

    def get_filter(self):
        name_filter = self.getparam('filter')
        if (name_filter is not None) and (name_filter != ""):
            return Q(firstname__icontains=name_filter) | Q(lastname__icontains=name_filter)
        else:
            return XferPrintListing.get_filter(self)


@ActionsManage.affect_other("", short_icon='mdi:mdi-delete-outline')
@MenuManage.describ('auth.add_user')
class IndividualUserRemove(XferContainerAcknowledge):
    caption = _("Remove as an users")
    short_icon = "mdi:mdi-account-outline"
    model = Individual
    field_id = 'individual'

    def fillresponse(self):
        if self.confirme(_("Do you want to dissociate this user to this contact ?{[br/]}(User will be always active.)")):
            self.item.user = None
            self.item.save()


@ActionsManage.affect_show("", short_icon='mdi:mdi-pencil-plus')
@MenuManage.describ('auth.add_user')
class IndividualUserAdd(XferContainerAcknowledge):
    caption = _("Add as an users")
    short_icon = "mdi:mdi-account"
    model = LucteriosUser

    def fillresponse(self, individual):
        obj_indiv = Individual.objects.get(pk=individual)
        current_user = LucteriosUser.objects.filter(email=obj_indiv.email.split(';')[0], is_active=True).first()
        if current_user is not None:
            if self.confirme(_("An user with same email exists already.{[br/]}Do you want to associate it to this contact?")):
                for other_contact in Individual.objects.filter(user=current_user):
                    other_contact.user = None
                    other_contact.save()
                obj_indiv.user = current_user
                obj_indiv.save()
                self.redirect_action(ActionsManage.get_action_url('CORE.LucteriosUser', 'Edit', self),
                                     params={'user_actif': str(current_user.id), 'IDENT_READ': 'YES'})
        elif not settings.USER_READONLY:
            dlg = self.create_custom(LucteriosUser)
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 3)
            dlg.add_component(img)
            dlg.item.username = obj_indiv.create_username()
            dlg.fill_from_model(1, 0, False, ['username'])
            dlg.add_action(IndividualUserValid.get_action(_('Ok'), short_icon='mdi:mdi-check'))
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            self.message(_("No user association find for this contact"), XFER_DBOX_WARNING)


@MenuManage.describ('auth.add_user')
class IndividualUserValid(XferSave):
    caption = _("Add as an users")
    short_icon = "mdi:mdi-account"
    model = LucteriosUser

    def fillresponse(self, individual, username):
        current_user = LucteriosUser.objects.filter(username=username).first()
        if current_user is not None:
            if self.confirme(_("This user exist already.{[br/]}Do you want to associate it to this contact?")):
                for other_contact in Individual.objects.filter(user=current_user):
                    other_contact.user = None
                    other_contact.save()
                obj_indiv = Individual.objects.get(pk=individual)
                obj_indiv.user = current_user
                obj_indiv.save()
                self.redirect_action(ActionsManage.get_action_url('CORE.LucteriosUser', 'Edit', self),
                                     params={'user_actif': str(current_user.id), 'IDENT_READ': 'YES'})
        else:
            XferSave.fillresponse(self)
            if self.except_msg == '':
                obj_indiv = Individual.objects.get(pk=individual)
                obj_indiv.user = self.item
                obj_indiv.save()
                obj_indiv.editor.saving(self)
                defaultgroup = Params.getobject("contacts-defaultgroup")
                if defaultgroup is not None:
                    obj_indiv.user.groups.add(defaultgroup)
                self.redirect_action(ActionsManage.get_action_url('CORE.LucteriosUser', 'Edit', self),
                                     params={'user_actif': str(self.item.id), 'IDENT_READ': 'YES'})


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline')
@MenuManage.describ('contacts.add_responsability')
class ResponsabilityAdd(XferContainerCustom):
    caption = _("Add responsability")
    short_icon = "mdi:mdi-account-circle"
    model = Responsability
    field_id = 'responsability_set'

    def fillresponse(self, legal_entity=0, name_filter=''):
        self.item.legal_entity = LegalEntity.objects.get(id=legal_entity)
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0, 1, 3)
        self.add_component(img)
        self.fill_from_model(1, 0, True, ['legal_entity'])
        comp = XferCompEdit('filter')
        comp.set_value(name_filter)
        comp.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        comp.set_location(1, 2)
        comp.description = _('Filtrer by name')
        comp.is_default = True
        self.add_component(comp)
        identfilter = []
        if name_filter != "":
            identfilter = [Q(firstname__icontains=name_filter) | Q(lastname__icontains=name_filter)]
        items = Individual.objects.filter(*identfilter).distinct()
        grid = XferCompGrid('individual')
        grid.set_model(items, None, self)
        grid.set_location(1, 3)
        grid.description = _('individual')
        grid.add_action(self.request, ResponsabilityModify.get_action(_("Select"), short_icon='mdi:mdi-check'),
                        modal=FORMTYPE_MODAL, close=CLOSE_YES, unique=SELECT_SINGLE, params={"SAVE": "YES"})
        grid.add_action(self.request, IndividualShow.get_action(_("Show"), short_icon='mdi:mdi-pencil-outline'),
                        modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE)
        grid.add_action(self.request, IndividualAddModify.get_action(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus'),
                        modal=FORMTYPE_MODAL, close=CLOSE_NO)
        self.add_component(grid)


@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('contacts.add_responsability')
class ResponsabilityModify(XferAddEditor):
    caption = _("Modify responsability")
    short_icon = "mdi:mdi-account-circle"
    model = Responsability
    field_id = 'responsability'


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('contacts.delete_responsability')
class ResponsabilityDel(XferDelete):
    caption = _("Delete responsability")
    short_icon = "mdi:mdi-account-circle"
    model = Responsability
    field_id = 'responsability'


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('To find an individual following a set of criteria.'))
class IndividualSearch(XferSavedCriteriaSearchEditor):
    caption = _("Individual search")
    short_icon = "mdi:mdi-account-search-outline"
    model = Individual
    field_id = 'individual'

    def __init__(self, **kwargs):
        XferSavedCriteriaSearchEditor.__init__(self, **kwargs)
        self.size_by_page = Params.getvalue("contacts-size-page")

    def fillresponse(self):
        XferSearchEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 5)
        if WrapAction.is_permission(self.request, 'contacts.add_abstractcontact'):
            self.get_components(self.field_id).add_action(self.request, ObjectMerge.get_action(_("Merge"), short_icon='mdi:mdi-set-merge'),
                                                          close=CLOSE_NO, unique=SELECT_MULTI, params={'modelname': self.model.get_long_name(), 'field_id': self.field_id})
        self.add_action(AbstractContactFindDouble.get_action(_("duplicate"), short_icon='mdi:mdi-content-copy'),
                        params={'modelname': self.model.get_long_name(), 'field_id': self.field_id}, pos_act=0)


@MenuManage.describ('contacts.change_abstractcontact', FORMTYPE_NOMODAL, 'contact.actions', _('To find a legal entity following a set of criteria.'))
class LegalEntitySearch(XferSavedCriteriaSearchEditor):
    caption = _("Legal entity search")
    short_icon = "mdi:mdi-account-search"
    model = LegalEntity
    field_id = 'legal_entity'

    def __init__(self, **kwargs):
        XferSavedCriteriaSearchEditor.__init__(self, **kwargs)
        self.size_by_page = Params.getvalue("contacts-size-page")

    def fillresponse(self):
        XferSearchEditor.fillresponse(self)
        self.item.editor.add_email_selector(self, 0, self.get_max_row() + 1, 5)
        if WrapAction.is_permission(self.request, 'contacts.add_abstractcontact'):
            self.get_components(self.field_id).add_action(self.request, ObjectMerge.get_action(_("Merge"), short_icon='mdi:mdi-set-merge'),
                                                          close=CLOSE_NO, unique=SELECT_MULTI, params={'modelname': self.model.get_long_name(), 'field_id': self.field_id})
        self.add_action(AbstractContactFindDouble.get_action(_("duplicate"), short_icon='mdi:mdi-content-copy'),
                        params={'modelname': self.model.get_long_name(), 'field_id': self.field_id}, pos_act=0)


@MenuManage.describ('contacts.add_abstractcontact')
class AbstractContactFindDouble(XferListEditor):
    caption = _("Contact duplication searching")
    short_icon = 'mdi:mdi-account-outline'
    model = AbstractContact
    field_id = 'abstractcontact'
    readonly = True
    methods_allowed = ('POST', 'PUT')

    def fillresponse_header(self):
        self.filter = self.model.get_query_for_duplicate()

    def fillresponse(self, modelname, field_id):
        if modelname is not None:
            self.model = apps.get_model(modelname)
        self.field_id = field_id
        XferListEditor.fillresponse(self)
        if WrapAction.is_permission(self.request, 'contacts.add_abstractcontact'):
            self.get_components(self.field_id).add_action(self.request, ObjectMerge.get_action(_("Merge"), short_icon='mdi:mdi-set-merge'),
                                                          close=CLOSE_NO, unique=SELECT_MULTI)


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('contacts.change_abstractcontact')
class AbstractContactShow(XferShowEditor):
    short_icon = 'mdi:mdi-account-outline'
    model = AbstractContact
    field_id = 'abstractcontact'
    caption = _("Show contact")

    def fillresponse(self, field_id):
        if field_id is not None:
            self.field_id = field_id
        if hasattr(self.item, 'abstractcontact_ptr_id'):
            XferShowEditor.fillresponse(self)
        else:
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 3)
            self.add_component(img)
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_title(_('this contact is inconstitant, you must to be promote it !'))
            lbl.set_location(1, 0)
            self.add_component(lbl)
            btn = XferCompButton('btn_promote')
            btn.set_location(1, 1)
            btn.set_action(self.request, ObjectPromote.get_action(_('Promote'), short_icon='mdi:mdi-upload-box'), modal=FORMTYPE_MODAL,
                           close=CLOSE_YES, params={'modelname': self.model.get_long_name(), 'field_id': self.field_id})
            self.add_component(btn)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('contacts.delete_abstractcontact')
class AbstractContactDel(XferDelete):
    short_icon = 'mdi:mdi-account-outline'
    model = AbstractContact
    field_id = 'abstractcontact'
    caption = _("Delete contact")


@signal_and_lock.Signal.decorate('post_merge')
def post_merge_contacts(item):
    from django.db.models import Count
    if isinstance(item, LegalEntity):
        individual_list = []
        for ident in item.responsability_set.values('individual').annotate(Count('id')).values('individual').order_by().filter(id__count__gt=1):
            individual_list.append(ident['individual'])
        for individual_id in individual_list:
            resp_list = item.responsability_set.filter(individual_id=individual_id).order_by('id')
            main_resp = resp_list.first()
            if main_resp is not None:
                main_resp.merge_objects(list(resp_list)[1:])


@signal_and_lock.Signal.decorate('situation')
def situation_contacts(xfer):
    if not hasattr(xfer, 'add_component'):
        try:
            Individual.objects.get(user=xfer.user)
            return True
        except Exception:
            return False
    else:
        if not xfer.request.user.is_anonymous:
            try:
                from lucterios.contacts.views import AccountAddModify
                current_individual = Individual.objects.get(user=xfer.request.user)
                row = xfer.get_max_row() + 1
                lab = XferCompLabelForm('contactsidentity')
                lab.set_value_as_header(str(current_individual))
                lab.set_location(0, row, 4)
                xfer.add_component(lab)
                if (current_individual.postal_code == '---'):
                    params = {'individual': current_individual.id, "postal_code": ""}
                    if (current_individual.address == '---'):
                        params['address'] = ""
                    if (current_individual.city == '---'):
                        params['city'] = ""
                    row = xfer.get_max_row() + 1
                    btn = XferCompButton('summarybtn')
                    btn.set_location(0, row + 1, 4)
                    btn.set_action(xfer.request, AccountAddModify.get_action(TITLE_EDIT, short_icon='mdi:mdi-pencil-outline'),
                                   modal=FORMTYPE_MODAL, close=CLOSE_NO, params=params)
                    btn.java_script = """if (typeof Singleton().hide_individual === 'undefined') {
    current.actionPerformed();
    Singleton().hide_individual = 1;
}
"""
                    xfer.add_component(btn)
                lab = XferCompLabelForm('contactsend')
                lab.set_value_center('{[hr/]}')
                lab.set_location(0, row + 2, 4)
                xfer.add_component(lab)
                return True
            except Exception:
                return False


@signal_and_lock.Signal.decorate('summary')
def summary_contacts(xfer):
    if not hasattr(xfer, 'add_component'):
        return WrapAction.is_permission(xfer, 'contacts.change_abstractcontact')
    else:
        if WrapAction.is_permission(xfer.request, 'contacts.change_abstractcontact'):
            row = xfer.get_max_row() + 1
            lab = XferCompLabelForm('contactstitle')
            lab.set_value_as_infocenter(_("Addresses and contacts"))
            lab.set_location(0, row, 4)
            xfer.add_component(lab)
            nb_legal_entities = len(LegalEntity.objects.all())
            lbl_doc = XferCompLabelForm('lbl_nblegalentities')
            lbl_doc.set_location(0, row + 1, 4)
            lbl_doc.set_value_center(_("Total number of legal entities: %d") % nb_legal_entities)
            xfer.add_component(lbl_doc)
            nb_individual = len(Individual.objects.all())
            lbl_doc = XferCompLabelForm('lbl_nbindividuals')
            lbl_doc.set_location(0, row + 2, 4)
            lbl_doc.set_value_center(_("Total number of individuals: %d") % nb_individual)
            xfer.add_component(lbl_doc)
            lab = XferCompLabelForm('contactsend')
            lab.set_value_center('{[hr/]}')
            lab.set_location(0, row + 3, 4)
            xfer.add_component(lab)
            return True
        else:
            return False
