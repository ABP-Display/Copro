from decimal import Decimal
from django.conf import settings
from django.db import models


class CouncilSettings(models.Model):
    mode = models.CharField(max_length=20, default="benevole", choices=[("benevole", "Bénévole"), ("cooperative", "Coopératif")])
    approval_enabled = models.BooleanField(default=False)
    threshold = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    required_approvals = models.PositiveSmallIntegerField(default=1)
    reference = models.CharField(max_length=1000, blank=True)
    proof = models.ForeignKey("documents.Version", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(threshold__gte=0), name="council_threshold_positive"),
            models.CheckConstraint(condition=models.Q(required_approvals__gte=1, required_approvals__lte=10), name="council_approval_count"),
        ]


class Mandate(models.Model):
    class Role(models.TextChoices):
        SYNDIC = "syndic", "Syndic bénévole"
        COOP_SYNDIC = "coop_syndic", "Président du conseil / syndic coopératif"
        PRESIDENT = "president", "Président du conseil syndical"
        VICE = "vice", "Vice-président du conseil"
        COUNCIL = "council", "Membre du conseil syndical"
        TREASURER = "treasurer", "Trésorier / référent comptable"
        CONTROLLER = "controller", "Contrôleur indépendant des comptes"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="council_mandates")
    owner = models.ForeignKey("core.Owner", null=True, blank=True, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices)
    starts_on = models.DateField()
    ends_on = models.DateField()
    authority = models.CharField(max_length=20, choices=[("ag", "Assemblée générale"), ("council", "Conseil syndical"), ("organisation", "Organisation interne")])
    reference = models.CharField(max_length=1000)
    proof = models.ForeignKey("documents.Version", null=True, blank=True, on_delete=models.PROTECT)
    assembly_mandate = models.OneToOneField("governance.AssemblyMandate", null=True, blank=True, on_delete=models.PROTECT)
    seat = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="dependent_mandates")
    eligibility_confirmed = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True)
    revocation_reason = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ["-starts_on", "-id"]
        constraints = [models.CheckConstraint(condition=models.Q(ends_on__gte=models.F("starts_on")), name="council_mandate_dates")]


class ExternalAccess(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="council_identity")
    must_change_password = models.BooleanField(default=True)


class ExpenseDraft(models.Model):
    data = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=15, default="draft")
    expense = models.OneToOneField("finance.Expense", null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-id"]


class ReviewRequest(models.Model):
    kind = models.CharField(max_length=15, choices=[("expense", "Facture"), ("quote", "Devis"), ("draft", "Dépense préparée")])
    expense = models.ForeignKey("finance.Expense", null=True, blank=True, on_delete=models.PROTECT)
    quote = models.ForeignKey("operations.Quote", null=True, blank=True, on_delete=models.PROTECT)
    draft = models.ForeignKey(ExpenseDraft, null=True, blank=True, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    proof = models.ForeignKey("documents.Version", on_delete=models.PROTECT)
    posted_snapshot = models.JSONField(null=True)
    required_approvals = models.PositiveSmallIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True)
    withdrawal_reason = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(fields=["expense"], condition=models.Q(withdrawn_at__isnull=True, expense__isnull=False), name="council_expense_request_unique"),
            models.UniqueConstraint(fields=["quote"], condition=models.Q(withdrawn_at__isnull=True, quote__isnull=False), name="council_quote_request_unique"),
            models.UniqueConstraint(fields=["draft"], condition=models.Q(withdrawn_at__isnull=True, draft__isnull=False), name="council_draft_request_unique"),
        ]


class Review(models.Model):
    request = models.ForeignKey(ReviewRequest, on_delete=models.PROTECT, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mandate = models.ForeignKey(Mandate, on_delete=models.PROTECT)
    decision = models.CharField(max_length=15, choices=[("approved", "Favorable"), ("rejected", "Refusé")])
    reason = models.CharField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["request", "author"], name="council_one_review_per_person")]


class AccountControl(models.Model):
    year = models.ForeignKey("finance.FiscalYear", on_delete=models.PROTECT)
    title = models.CharField(max_length=150)
    observations = models.TextField(max_length=10000)
    checks = models.JSONField(default=dict)
    conclusion = models.CharField(max_length=30, default="draft")
    evidence = models.ManyToManyField("documents.Version", blank=True)
    snapshot = models.JSONField(default=dict)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mandate = models.ForeignKey(Mandate, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["-id"]


class CouncilEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=150)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
