# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from lucterios.framework.xferadvance import TITLE_MODIFY, TITLE_ADD, TITLE_DELETE, TITLE_PRINT, TITLE_OK, TITLE_CANCEL, \
    XferSave
from lucterios.framework.xferadvance import XferListEditor
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompImage, XferCompSelect
from lucterios.framework.tools import ActionsManage, MenuManage, CLOSE_YES, WrapAction
from lucterios.framework.tools import SELECT_SINGLE
from lucterios.framework.signal_and_lock import Signal
from lucterios.CORE.xferprint import XferPrintAction

from diacamma.accounting.tools import current_system_account, format_with_devise
from diacamma.accounting.models import Budget, CostAccounting, FiscalYear, ChartsAccount, EntryLineAccount
from django.db.models.aggregates import Sum


@MenuManage.describ('accounting.change_budget')
class BudgetList(XferListEditor):
    short_icon = "mdi:mdi-bank-transfer"
    model = Budget
    field_id = 'budget'
    caption = _("Prévisionnal budget")

    def fillresponse_header(self):
        row_id = self.get_max_row() + 1
        if self.getparam('year', 0) != 0:
            year = FiscalYear.get_current(self.getparam('year'))
            lbl = XferCompLabelForm('title_year')
            lbl.set_italic()
            lbl.set_value("{[b]}%s{[/b]} : %s" % (_('fiscal year'), year))
            lbl.set_location(1, row_id, 2)
            self.add_component(lbl)
        row_id += 1
        if self.getparam('cost_accounting') is not None:
            cost = CostAccounting.objects.get(id=self.getparam('cost_accounting', 0))
            lbl = XferCompLabelForm('title_cost')
            lbl.set_italic()
            lbl.set_value("{[b]}%s{[/b]} : %s" % (_('cost accounting'), cost))
            lbl.set_location(1, row_id, 2)
            self.add_component(lbl)
        Signal.call_signal('editbudget', self)
        self.filter = Q()
        if self.getparam('year', 0) != 0:
            self.filter &= Q(year_id=self.getparam('year'))
        if self.getparam('cost_accounting') is not None:
            self.filter &= Q(cost_accounting_id=self.getparam('cost_accounting'))

    def fill_grid(self, row, model, field_id, items):
        XferListEditor.fill_grid(self, row, model, field_id, items)
        if self.getparam('cost_accounting') is None:
            grid = self.get_components(field_id)
            grid.record_ids = []
            grid.records = {}
            last_code = ''
            value = 0
            for current_budget in items:
                if last_code != current_budget.code:
                    if last_code != '':
                        chart = ChartsAccount.get_chart_account(last_code)
                        grid.set_value('C' + last_code, 'budget', str(chart))
                        grid.set_value('C' + last_code, 'montant', value)
                        value = 0
                    last_code = current_budget.code
                value += current_budget.credit_debit_way() * current_budget.amount
            if last_code != '':
                chart = ChartsAccount.get_chart_account(last_code)
                grid.set_value('C' + last_code, 'budget', str(chart))
                grid.set_value('C' + last_code, 'montant', value)
            grid.nb_lines = len(grid.records)
            grid.order_list = None
            grid.page_max = 1
            grid.page_num = 0

    def fillresponse_body(self):
        self.get_components("title").colspan = 2
        row_id = self.get_max_row() + 1

        expense_filter = Q(code__regex=current_system_account().get_expence_mask()) | (Q(code__regex=current_system_account().get_annexe_mask()) & Q(amount__lt=0))
        self.fill_grid(row_id, self.model, 'budget_expense', self.model.objects.filter(self.filter & expense_filter).distinct())
        self.get_components("budget_expense").colspan = 3
        self.get_components("budget_expense").description = _("Expense")

        revenue_filter = Q(code__regex=current_system_account().get_revenue_mask()) | (Q(code__regex=current_system_account().get_annexe_mask()) & Q(amount__gte=0))
        self.fill_grid(row_id + 1, self.model, 'budget_revenue', self.model.objects.filter(self.filter & revenue_filter).distinct())
        self.get_components("budget_revenue").colspan = 3
        self.get_components("budget_revenue").description = _("Revenue")

        resultat_budget = Budget.get_total(self.getparam('year'), self.getparam('cost_accounting'))
        if abs(resultat_budget) > 0.0001:
            row_id = self.get_max_row() + 1
            lbl = XferCompLabelForm('result')
            lbl.set_value(resultat_budget)
            lbl.set_format(format_with_devise(5))
            lbl.set_location(0, row_id, 2)
            if resultat_budget > 0:
                lbl.description = _('result (profit)')
            else:
                lbl.description = _('result (deficit)')
            self.add_component(lbl)


@MenuManage.describ('accounting.change_budget')
@ActionsManage.affect_list(TITLE_PRINT, short_icon='mdi:mdi-printer-outline')
class BudgetPrint(XferPrintAction):
    short_icon = "mdi:mdi-bank-transfer"
    model = Budget
    field_id = 'budget'
    caption = _("Print previsionnal budget")
    with_text_export = True
    action_class = BudgetList


def condition_changebudget(xfer, gridname=''):
    return not xfer.getparam('readonly', False)


@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE, condition=condition_changebudget)
@ActionsManage.affect_list(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', condition=condition_changebudget)
@MenuManage.describ('accounting.add_budget')
class BudgetAddModify(XferAddEditor):
    short_icon = "mdi:mdi-bank-transfer"
    model = Budget
    field_id = 'budget'
    caption_add = _("Add budget line")
    caption_modify = _("Modify budget line")

    class XferSaveBudget(XferSave):

        def _load_unique_record(self, itemid):
            if itemid[0] == 'C':
                self.item = Budget()
                self.item.id = itemid
                self.item.year_id = self.getparam('year', 0)
                self.item.code = itemid[1:]
                self.fill_simple_fields()
            else:
                XferSave._load_unique_record(self, itemid)

    def run_save(self, request, *args, **kwargs):
        save = BudgetAddModify.XferSaveBudget()
        save.is_view_right = self.is_view_right
        save.locked = self.locked
        save.model = self.model
        save.field_id = self.field_id
        save.caption = self.caption
        return save.request_handling(request, *args, **kwargs)

    def _load_unique_record(self, itemid):
        if itemid[0] == 'C':
            self.item = Budget()
            self.item.id = itemid
            self.item.code = itemid[1:]
            val = Budget.objects.filter(code=self.item.code, year_id=self.getparam('year', 0)).aggregate(Sum('amount'))
            self.item.amount = val['amount__sum']
        else:
            XferAddEditor._load_unique_record(self, itemid)

    def _search_model(self):
        if self.getparam("budget_revenue") is not None:
            self.field_id = 'budget_revenue'
        if self.getparam("budget_expense") is not None:
            self.field_id = 'budget_expense'
        XferAddEditor._search_model(self)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_SINGLE, condition=condition_changebudget)
@MenuManage.describ('accounting.delete_budget')
class BudgetDel(XferDelete):
    short_icon = "mdi:mdi-bank-transfer"
    model = Budget
    field_id = 'budget'
    caption = _("Delete Budget line")

    def _load_unique_record(self, itemid):
        if itemid[0] == 'C':
            self.item = Budget()
            self.item.id = itemid
            self.item.year_id = self.getparam('year', 0)
            self.item.code = itemid[1:]
        else:
            XferAddEditor._load_unique_record(self, itemid)

    def _search_model(self):
        if self.getparam("budget_revenue") is not None:
            self.field_id = 'budget_revenue'
        if self.getparam("budget_expense") is not None:
            self.field_id = 'budget_expense'
        XferAddEditor._search_model(self)


@ActionsManage.affect_grid(_("Budget"), short_icon="mdi:mdi-bank-transfer", unique=SELECT_SINGLE)
@MenuManage.describ('accounting.change_budget')
class CostAccountingBudget(XferContainerAcknowledge):
    short_icon = "mdi:mdi-bank-transfer"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Budget")
    readonly = True
    methods_allowed = ('GET', )

    def fillresponse(self):
        read_only = (self.item.status == CostAccounting.STATUS_CLOSED) or self.item.is_protected
        self.redirect_action(BudgetList.get_action(), close=CLOSE_YES, params={'cost_accounting': self.item.id, 'readonly': read_only})


@ActionsManage.affect_list(_("Import"), short_icon="mdi:mdi-upload-box-outline", condition=lambda xfer: not xfer.getparam('readonly', False))
@MenuManage.describ('accounting.add_budget')
class BudgetImport(XferContainerAcknowledge):
    short_icon = "mdi:mdi-bank-transfer"
    model = Budget
    field_id = 'budget'
    caption = _("Import budget")

    def add_sel(self, costaccounting):
        res = []
        if costaccounting is not None:
            res.append((costaccounting.id, str(costaccounting)))
            res.extend(self.add_sel(costaccounting.last_costaccounting))
        return res

    def fillresponse(self, year=0, cost_accounting=0):
        if self.getparam("CONFIRME", "") != "YES":
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0, 1, 3)
            dlg.add_component(img)
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_title(self.caption)
            lbl.set_location(1, 0, 6)
            dlg.add_component(lbl)

            if cost_accounting == 0:
                year = FiscalYear.get_current(year)
                sel = XferCompSelect('currentyear')
                sel.set_needed(True)
                sel.set_select_query(FiscalYear.objects.filter(end__lt=year.begin))
                sel.description = _('fiscal year')
                sel.set_location(1, 1)
                dlg.add_component(sel)
            else:
                current_cost = CostAccounting.objects.get(id=cost_accounting)
                sel = XferCompSelect('costaccounting')
                sel.set_needed(True)
                sel.set_select(self.add_sel(current_cost.last_costaccounting))
                sel.set_location(1, 1)
                sel.description = _('cost accounting')
                dlg.add_component(sel)
            lbl = XferCompLabelForm('lbl_info')
            lbl.set_value_as_header(_('All budget lines will be delete and income statement of select item will be import as new budget.'))
            lbl.set_location(1, 2, 2)
            dlg.add_component(lbl)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'), close=CLOSE_YES, params={'CONFIRME': 'YES'})
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            currentyear = self.getparam('currentyear', 0)
            costaccounting = self.getparam('costaccounting', 0)
            if cost_accounting == 0:
                budget_filter = Q(year_id=year)
            else:
                budget_filter = Q(cost_accounting_id=cost_accounting)
            for budget_line in Budget.objects.filter(budget_filter).distinct():
                if (cost_accounting != 0) or (budget_line.cost_accounting_id is None):
                    budget_line.delete()
            if cost_accounting == 0:
                for chart in ChartsAccount.objects.filter(Q(year_id=currentyear) & Q(type_of_account__in=(3, 4))).distinct():
                    value = chart.get_current_total(with_correction=False)
                    for current_budget in Budget.objects.filter(year_id=year, code=chart.code):
                        value -= current_budget.amount
                    if abs(value) > 0.001:
                        Budget.objects.create(code=chart.code, amount=value, year_id=year)
            else:
                if year == 0:
                    year = None
                values = {}
                for line in EntryLineAccount.objects.filter(account__type_of_account__in=(3, 4), costaccounting_id=costaccounting).distinct():
                    if line.account.code not in values.keys():
                        values[line.account.code] = 0.0
                    values[line.account.code] += line.amount
                for code, value in values.items():
                    if abs(value) > 0.001:
                        Budget.objects.create(code=code, amount=value, year_id=year, cost_accounting_id=cost_accounting)


@ActionsManage.affect_list(_("Budget"), short_icon="mdi:mdi-bank-transfer")
@MenuManage.describ('accounting.change_budget')
class FiscalYearBudget(XferContainerAcknowledge):
    short_icon = "mdi:mdi-bank-transfer"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Budget")
    readonly = True
    methods_allowed = ('GET', )

    def fillresponse(self, year):
        fiscal_year = FiscalYear.get_current(year)
        read_only = (fiscal_year.status == FiscalYear.STATUS_FINISHED)
        self.redirect_action(BudgetList.get_action(), close=CLOSE_YES, params={'year': fiscal_year.id, 'readonly': read_only})
