from decimal import Decimal
import uuid
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from core.models import Owner, Lot


class FiscalYear(models.Model):
    name = models.CharField(max_length=100)
    starts_on = models.DateField()
    ends_on = models.DateField()
    closed = models.BooleanField(default=False)
    next_entry = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-starts_on"]
        constraints = [models.CheckConstraint(condition=models.Q(ends_on__gte=models.F("starts_on")), name="year_dates_valid")]


class Account(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ["code"]


class BankAccount(models.Model):
    name = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=150, blank=True)
    iban = models.CharField(max_length=34, blank=True)
    kind = models.CharField(max_length=15, choices=[('current', 'Compte courant'), ('savings', 'Épargne'), ('works', 'Fonds travaux')], default='current')
    account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name='bank')
    active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['name', 'id']
        constraints = [
            models.UniqueConstraint(fields=['is_default'], condition=models.Q(is_default=True), name='one_default_bank'),
            models.CheckConstraint(condition=models.Q(is_default=False) | models.Q(active=True), name='default_bank_active'),
        ]


class Entry(models.Model):
    kind = models.CharField(max_length=20, default='normal')
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    number = models.PositiveIntegerField()
    date = models.DateField()
    journal = models.CharField(max_length=10)
    label = models.CharField(max_length=250)
    reference = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    cost_center = models.ForeignKey("CostCenter", on_delete=models.PROTECT, null=True, blank=True)
    reversal_of = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversal")
    class Meta:
        ordering = ["-date", "-number"]
        constraints = [models.UniqueConstraint(fields=["year", "number"], name="entry_year_number_unique")]


class Line(models.Model):
    key = models.ForeignKey('ChargeKey', on_delete=models.PROTECT, null=True, blank=True)
    project = models.ForeignKey('FinanceProject', on_delete=models.PROTECT, null=True, blank=True)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    entry = models.ForeignKey(Entry, on_delete=models.PROTECT, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT, null=True, blank=True)
    supplier = models.ForeignKey('operations.Supplier', on_delete=models.PROTECT, null=True, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(debit__gt=0, credit=0) | models.Q(credit__gt=0, debit=0)), name="line_one_positive_side")]


class ChargeKey(models.Model):
    name = models.CharField(max_length=150, unique=True)
    general = models.BooleanField(default=True)
    annual_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(Decimal("0"))])
    class Meta:
        ordering = ["name"]
        constraints = [models.CheckConstraint(condition=models.Q(annual_budget__gte=0), name="key_budget_positive")]


class Share(models.Model):
    key = models.ForeignKey(ChargeKey, on_delete=models.CASCADE, related_name="shares")
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    class Meta:
        constraints = [models.UniqueConstraint(fields=["key", "lot"], name="key_lot_unique"),
                       models.CheckConstraint(condition=models.Q(value__gte=0), name="key_share_positive")]


class FundCall(models.Model):
    advance_type = models.CharField(max_length=12, default='reserve', choices=[('reserve','Réserve de trésorerie'),('ppt','Avance du PPT'),('temporary','Manque temporaire de trésorerie')])
    schedule = models.ForeignKey('CallSchedule', on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=12, default='current', choices=[('current','Budget courant'),('works','Travaux votés'),('fund','Fonds travaux'),('advance','Avance de trésorerie')])
    project = models.ForeignKey('FinanceProject', on_delete=models.PROTECT, null=True, blank=True)
    decision = models.CharField(max_length=250, blank=True)
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    key = models.ForeignKey(ChargeKey, on_delete=models.PROTECT)
    label = models.CharField(max_length=150)
    date = models.DateField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT, null=True)
    cost_center = models.ForeignKey("CostCenter", on_delete=models.PROTECT, null=True, blank=True)
    class Meta:
        ordering = ["-date", "-id"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="call_amount_positive")]


class Allocation(models.Model):
    call = models.ForeignKey(FundCall, on_delete=models.PROTECT, related_name="allocations")
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    shares = models.DecimalField(max_digits=12, decimal_places=2)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["call", "lot"], name="call_lot_unique")]


class Expense(models.Model):
    due_date = models.DateField(null=True, blank=True)
    project = models.ForeignKey('FinanceProject', on_delete=models.PROTECT, null=True, blank=True)
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    key = models.ForeignKey(ChargeKey, on_delete=models.PROTECT)
    supplier = models.CharField(max_length=150)
    supplier_record = models.ForeignKey('operations.Supplier', on_delete=models.PROTECT, null=True, blank=True, related_name='expenses')
    document = models.ForeignKey('documents.Document', on_delete=models.PROTECT, null=True, blank=True)
    reference = models.CharField(max_length=100)
    label = models.CharField(max_length=150)
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT, related_name="expense")
    payment_entry = models.OneToOneField(Entry, on_delete=models.PROTECT, related_name="paid_expense", null=True)
    class Meta:
        ordering = ["-date", "-id"]
        constraints = [models.UniqueConstraint(fields=["year", "supplier", "reference"], name="expense_reference_unique"),
                       models.UniqueConstraint(fields=['year', 'supplier_record', 'reference'], condition=models.Q(supplier_record__isnull=False), name='expense_supplier_reference_unique'),
                       models.CheckConstraint(condition=models.Q(amount__gt=0), name="expense_amount_positive")]


class ExpensePayment(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT, related_name="expense_payment")
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True)
    class Meta:
        ordering = ["entry__date", "id"]
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="expense_payment_positive")]


class Receipt(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT)
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name="receipt_amount_positive")]


class BankTransfer(models.Model):
    operation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    source = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='transfers_out')
    destination = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='transfers_in')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='transfer_amount_positive'),
            models.CheckConstraint(condition=~models.Q(source=models.F('destination')), name='transfer_distinct_banks'),
        ]


class PublishedReport(models.Model):
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    title = models.CharField(max_length=150)
    data = models.JSONField()
    published_at = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta:
        ordering = ["-published_at"]


class Organization(models.Model):
    name = models.CharField(max_length=150, default="Ma copropriété")
    address = models.TextField(blank=True, max_length=1000)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    registration = models.CharField(max_length=100, blank=True)
    code_length = models.PositiveSmallIntegerField(default=3)
    analytic_required = models.BooleanField(default=False)
    report_prefix = models.CharField(max_length=20, blank=True)
    default_today = models.BooleanField(default=True)


class Journal(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["is_default"], condition=models.Q(is_default=True), name="one_default_journal")]


class CostCenter(models.Model):
    name = models.CharField(max_length=150, unique=True)
    active = models.BooleanField(default=True)
    class Meta:
        ordering = ["name"]


class Budget(models.Model):
    key = models.ForeignKey(ChargeKey, on_delete=models.PROTECT, null=True, blank=True)
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    cost_center = models.ForeignKey(CostCenter, on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    variance_note = models.TextField(max_length=2000, blank=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gte=0), name="budget_amount_positive"),
            models.UniqueConstraint(fields=["year","account","cost_center"],condition=models.Q(cost_center__isnull=False,key__isnull=True),name="budget_center_unique"),
            models.UniqueConstraint(fields=["year","account"],condition=models.Q(cost_center__isnull=True,key__isnull=True),name="budget_general_unique"),
            models.UniqueConstraint(fields=['year','account','key'],condition=models.Q(key__isnull=False,cost_center__isnull=True),name='budget_key_unique'),
            models.UniqueConstraint(fields=['year','account','key','cost_center'],condition=models.Q(key__isnull=False,cost_center__isnull=False),name='budget_key_center_unique')]


class EntryTemplate(models.Model):
    name = models.CharField(max_length=150, unique=True)
    journal = models.CharField(max_length=10, default="OD")
    lines = models.JSONField()
    class Meta:
        ordering = ["name"]


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-created_at","-id"]


class FinanceProject(models.Model):
    name = models.CharField(max_length=150)
    key = models.ForeignKey(ChargeKey, on_delete=models.PROTECT)
    budget = models.DecimalField(max_digits=14, decimal_places=2)
    decision = models.CharField(max_length=250)
    decided_on = models.DateField(null=True, blank=True)
    completed_on = models.DateField(null=True, blank=True)
    completion_entry = models.OneToOneField(Entry, on_delete=models.PROTECT, null=True, blank=True)


class ChargeAllocation(models.Model):
    line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name='charge_allocations')
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    key = models.ForeignKey(ChargeKey, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    shares = models.DecimalField(max_digits=12, decimal_places=2)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['line','lot'], name='charge_line_lot_unique')]


class Settlement(models.Model):
    debit_line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name='debit_matches')
    credit_line = models.ForeignKey(Line, on_delete=models.PROTECT, related_name='credit_matches')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='settlement_positive')]


class BankStatement(models.Model):
    transit = models.JSONField(default=list, blank=True)
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT)
    starts_on = models.DateField()
    ends_on = models.DateField()
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = models.DecimalField(max_digits=14, decimal_places=2)
    fingerprint = models.CharField(max_length=64, unique=True)
    validated = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta:
        ordering = ['-ends_on','-id']


class StatementLine(models.Model):
    statement = models.ForeignKey(BankStatement, on_delete=models.PROTECT, related_name='rows')
    date = models.DateField()
    label = models.CharField(max_length=250)
    reference = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)


class BankMatch(models.Model):
    statement_line = models.ForeignKey(StatementLine, on_delete=models.PROTECT, related_name='matches')
    line = models.OneToOneField(Line, on_delete=models.PROTECT, related_name='bank_match')


class AnnualSettlement(models.Model):
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    data = models.JSONField()
    source_hash = models.CharField(max_length=64)
    decision = models.CharField(max_length=250)
    approved_on = models.DateField()
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT, null=True, blank=True)
    active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['year'], condition=models.Q(active=True), name='one_active_regularization')]


class YearClosure(models.Model):
    year = models.OneToOneField(FiscalYear, on_delete=models.PROTECT, related_name='closure')
    next_year = models.OneToOneField(FiscalYear, on_delete=models.PROTECT, related_name='previous_closure')
    closing_entry = models.OneToOneField(Entry, on_delete=models.PROTECT, null=True, blank=True, related_name='year_closing')
    opening_entry = models.OneToOneField(Entry, on_delete=models.PROTECT, null=True, blank=True, related_name='year_opening')
    snapshot = models.JSONField()
    digest = models.CharField(max_length=64)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    closed_at = models.DateTimeField(auto_now_add=True)


class CallSchedule(models.Model):
    request_id = models.UUIDField(unique=True)
    source_hash = models.CharField(max_length=64)
    year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class OwnershipChange(models.Model):
    active = models.BooleanField(default=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='cancelled_mutations')
    adjustments = models.ManyToManyField(Entry, related_name='ownership_adjustments')
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name='ownership_changes')
    old_owner = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name='sold_lots')
    new_owner = models.ForeignKey(Owner, on_delete=models.PROTECT, related_name='bought_lots')
    effective_date = models.DateField()
    reference = models.CharField(max_length=250)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['lot','effective_date'],condition=models.Q(active=True),name='lot_mutation_date_unique')]
        ordering = ['effective_date','id']


class AllocationTransfer(models.Model):
    allocation = models.ForeignKey(Allocation, on_delete=models.PROTECT, related_name='transfers')
    mutation = models.ForeignKey(OwnershipChange, on_delete=models.PROTECT)
    entry = models.ForeignKey(Entry, on_delete=models.PROTECT)


class RegularizationTransfer(models.Model):
    active = models.BooleanField(default=True)
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT, null=True, blank=True)
    settlement = models.ForeignKey(AnnualSettlement, on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    key = models.ForeignKey(ChargeKey, on_delete=models.PROTECT)
    mutation = models.ForeignKey(OwnershipChange, on_delete=models.PROTECT)
    entry = models.ForeignKey(Entry, on_delete=models.PROTECT)


class OperationTicket(models.Model):
    request_id = models.UUIDField(unique=True)
    path = models.CharField(max_length=250)
    source_hash = models.CharField(max_length=64)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    response = models.JSONField(null=True)
    status = models.PositiveSmallIntegerField(default=201)
    created_at = models.DateTimeField(auto_now_add=True)


class FundingPolicy(models.Model):
    year = models.OneToOneField(FiscalYear, on_delete=models.PROTECT, related_name='funding_policy')
    housing = models.CharField(max_length=12, default='unknown', choices=[('unknown','À renseigner'),('housing','Habitation totale ou partielle'),('other','Autre destination')])
    received_on = models.DateField(null=True, blank=True)
    annual_budget = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    budget_reference = models.CharField(max_length=250, blank=True)
    ppt_adopted = models.BooleanField(null=True)
    ppt_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fund_contribution = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fund_reference = models.CharField(max_length=250, blank=True)
    fund_proof = models.ForeignKey('documents.Version', on_delete=models.PROTECT, null=True, blank=True, related_name='fund_policies')
    suspended = models.BooleanField(default=False)
    suspension_reference = models.CharField(max_length=250, blank=True)
    suspension_proof = models.ForeignKey('documents.Version', on_delete=models.PROTECT, null=True, blank=True, related_name='fund_suspensions')
    reserve_authorized = models.BooleanField(default=False)
    advance_reference = models.CharField(max_length=250, blank=True)
    advance_proof = models.ForeignKey('documents.Version', on_delete=models.PROTECT, null=True, blank=True, related_name='advance_policies')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(annual_budget__gte=0, ppt_amount__gte=0, fund_contribution__gte=0), name='funding_policy_nonnegative')]


class AdvanceRefund(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    account_code = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=12)
    reference = models.CharField(max_length=250)
    proof = models.ForeignKey('documents.Version', on_delete=models.PROTECT)
    bank = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='advance_refund_positive')]


class AdvanceUse(models.Model):
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT)
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT)
    project = models.ForeignKey(FinanceProject, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=250)
    proof = models.ForeignKey('documents.Version', on_delete=models.PROTECT)
    entry = models.OneToOneField(Entry, on_delete=models.PROTECT)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(amount__gt=0), name='advance_use_positive')]
