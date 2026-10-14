# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from lucterios.framework.xferadvance import XferDelete, XferShowEditor, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_EDIT, TITLE_CANCEL, TITLE_OK, TITLE_CREATE
from lucterios.framework.tools import FORMTYPE_NOMODAL, SELECT_SINGLE, FORMTYPE_REFRESH, SELECT_MULTI, SELECT_NONE, CLOSE_NO, CLOSE_YES
from lucterios.framework.tools import ActionsManage, MenuManage, WrapAction
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompDate
from lucterios.framework.xferadvance import XferListEditor
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XFER_DBOX_WARNING
from lucterios.framework.error import LucteriosException, IMPORTANT

from diacamma.accounting.models import CostAccounting, ModelLineEntry, ModelEntry, FiscalYear
from diacamma.accounting.views_reports import CostAccountingIncomeStatement


@MenuManage.describ('accounting.change_entryaccount', FORMTYPE_NOMODAL, 'bookkeeping', _('Edition of costs accounting'))
class CostAccountingList(XferListEditor):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Costs accounting")

    def fillresponse_header(self):
        self.filter = Q()

        status_filter = self.getparam('status', 0)
        if status_filter != -1:
            self.filter &= Q(status=status_filter)
        self.status = status_filter

        select_year = self.getparam('year', 0)
        if select_year > 0:
            self.filter &= Q(year_id=select_year)
        if select_year == -1:
            self.filter &= Q(year__isnull=True)
        self.fill_from_model(0, 4, False, ['status', 'year'])
        comp_year = self.get_components('year')
        comp_year.select_list.append((-1, _('- without fiscal year -')))
        comp_year.set_value(select_year)
        comp_year.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        comp_year.colspan = 2
        comp_status = self.get_components('status')
        comp_status.select_list.insert(0, (-1, None))
        comp_status.set_value(status_filter)
        comp_status.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        comp_status.colspan = 2

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.get_components('title').colspan += 1
        self.get_components('costaccounting').colspan += 1


@ActionsManage.affect_list(_("By date"), short_icon='mdi:mdi-printer-outline')
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingReportByDate(XferContainerAcknowledge):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Print by date")

    def fillresponse(self):
        begin_date = self.getparam('begin_date')
        end_date = self.getparam('end_date')
        if (begin_date is None) or (end_date is None):
            year = FiscalYear.get_current()
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0)
            dlg.add_component(img)
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_title(_('Define date range to determine accounting cost list.'))
            lbl.set_location(1, 0, 2)
            begin_filter = XferCompDate('begin_date')
            begin_filter.set_location(1, 1)
            begin_filter.set_needed(True)
            begin_filter.set_value(year.begin)
            begin_filter.description = _('begin')
            dlg.add_component(begin_filter)
            end_filter = XferCompDate('end_date')
            end_filter.set_location(2, 1)
            end_filter.set_needed(True)
            end_filter.set_value(year.end)
            end_filter.description = _('end')
            dlg.add_component(end_filter)
            dlg.add_component(lbl)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'))
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            list_cost = []
            for cost_item in CostAccounting.objects.filter(Q(entrylineaccount__entry__date_value__gte=begin_date) & Q(entrylineaccount__entry__date_value__lte=end_date)).distinct():
                list_cost.append(str(cost_item.id))
            list_cost = set(list_cost)
            if len(list_cost) == 0:
                raise LucteriosException(IMPORTANT, _("No cost accounting finds for this range !"))
            self.redirect_action(CostAccountingIncomeStatement.get_action(), modal=FORMTYPE_NOMODAL, close=CLOSE_YES, params={'begin_date': begin_date, 'end_date': end_date, 'datereadonly': True, 'costaccounting': ";".join(list_cost)})


@ActionsManage.affect_grid(_("Default"), short_icon='mdi:mdi-star-outline', unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingDefault(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-star-outline'
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Default")
    readonly = True

    def fillresponse(self):
        self.item.change_has_default()


@ActionsManage.affect_grid(_("Close"), short_icon="mdi:mdi-check", unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingClose(XferContainerAcknowledge):
    short_icon = "mdi:mdi-check"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Close")
    readonly = True

    def fillresponse(self):
        if self.item.status == CostAccounting.STATUS_OPENED:
            if self.item.is_protected:
                raise LucteriosException(IMPORTANT, _("This cost accounting is protected by other modules!"))
            self.item.check_before_close()
            if self.confirme(_("Do you want to close this cost accounting?")):
                self.item.close()


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', unique=SELECT_NONE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.add_entryaccount')
class CostAccountingAddModify(XferAddEditor):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption_add = _("Add cost accounting")
    caption_modify = _("Modify cost accounting")

    def fillresponse(self):
        if 'status' in self.params.keys():
            del self.params['status']
        if (self.item.id is not None) and self.item.is_protected:
            raise LucteriosException(IMPORTANT, _("This cost accounting is protected by other modules!"))
        XferAddEditor.fillresponse(self)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.delete_entryaccount')
class CostAccountingDel(XferDelete):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Delete cost accounting")


def condition_recreate(xfer):
    select_year = xfer.getparam('year', 0)
    if select_year <= 0:
        return False
    last_year = FiscalYear.objects.get(id=select_year).last_fiscalyear
    if last_year is None:
        return False
    cost_list = CostAccounting.objects.filter(year=last_year, year__next_fiscalyear__status=FiscalYear.STATUS_BUILDING, is_protected=False, next_costaccounting__isnull=True)
    return len(cost_list) > 0


@ActionsManage.affect_list(_("Recreate"), short_icon='mdi:mdi-pencil-plus-outline', condition=condition_recreate)
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingRecreate(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-pencil-plus-outline'
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Recreate")
    readonly = True

    def fillresponse(self, year=0):
        current_year = FiscalYear.objects.get(id=year)
        cost_nb = CostAccounting.objects.filter(year__next_fiscalyear__in=(current_year,), year__next_fiscalyear__status=FiscalYear.STATUS_BUILDING, is_protected=False, next_costaccounting__isnull=True).count()
        if self.confirme(_('Do you want to try to import %d old cost accounting in this fiscal year ?') % cost_nb):
            error = CostAccounting.create_costs_from_lastyear(year)
            if len(error) > 0:
                self.message(_('Some last cost accounting have not be imported:{[br]}%s') % "{[br]}".join(error), XFER_DBOX_WARNING)
            else:
                self.message(_('All last cost accounting have be imported.'))


@MenuManage.describ('accounting.change_entryaccount', FORMTYPE_NOMODAL, 'bookkeeping', _('Edition of entry model'),)
class ModelEntryList(XferListEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption = _("Models of entry")


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus', unique=SELECT_NONE)
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', close=CLOSE_YES)
@MenuManage.describ('accounting.add_entryaccount')
class ModelEntryAddModify(XferAddEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption_add = _("Add model of entry")
    caption_modify = _("Modify model of entry")


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.change_entryaccount')
class ModelEntryShow(XferShowEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption = _("Show Model of entry")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.delete_entryaccount')
class ModelEntryDel(XferDelete):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption = _("Delete Model of entry")


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', unique=SELECT_NONE)
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_entryaccount')
class ModelLineEntryAddModify(XferAddEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelLineEntry
    field_id = 'modellineentry'
    caption_add = _("Add model line  of entry")
    caption_modify = _("Modify model line  of entry")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.delete_entryaccount')
class ModelLineEntryDel(XferDelete):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelLineEntry
    field_id = 'modellineentry'
    caption = _("Delete Model line  of entry")
