from django.conf import settings

from django.db import models


class Meeting(models.Model):

    title = models.CharField(max_length=150)

    scheduled_at = models.DateTimeField()

    location = models.CharField(max_length=250, blank=True)

    notes = models.TextField(blank=True, max_length=5000)

    archived = models.BooleanField(default=False)

    roster = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ["-scheduled_at", "-id"]


class Resolution(models.Model):

    meeting = models.ForeignKey(
        Meeting, on_delete=models.PROTECT, related_name="resolutions"
    )

    position = models.PositiveIntegerField()

    title = models.CharField(max_length=150)

    text = models.TextField(blank=True, max_length=10000)

    majority = models.CharField(
        max_length=12,
        choices=[
            ("24", "Article 24"),
            ("25", "Article 25"),
            ("26", "Article 26"),
            ("unanimity", "Unanimité"),
        ],
        default="24",
    )

    notes = models.TextField(blank=True, max_length=5000)

    analysis = models.JSONField(null=True, blank=True)

    class Meta:

        ordering = ["position", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["meeting", "position"],
                name="resolution_meeting_position_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(position__gt=0), name="resolution_position_positive"
            ),
        ]


class AssemblyWorkflow(models.Model):
    meeting = models.OneToOneField(
        Meeting, on_delete=models.PROTECT, related_name="workflow"
    )
    phase = models.CharField(max_length=20, default="draft")
    config = models.JSONField(default=dict)
    packet = models.JSONField(default=dict)
    participants = models.JSONField(default=list)
    bureau = models.JSONField(default=dict)
    minutes = models.JSONField(default=dict)
    digest = models.CharField(max_length=64, blank=True)
    frozen_at = models.DateTimeField(null=True)
    closed_at = models.DateTimeField(null=True)
    evidence = models.ManyToManyField("documents.Version", blank=True)


class AssemblyDelivery(models.Model):
    workflow = models.ForeignKey(
        AssemblyWorkflow, on_delete=models.PROTECT, related_name="deliveries"
    )
    kind = models.CharField(max_length=20)
    elector = models.CharField(max_length=220)
    recipient = models.JSONField(default=dict)
    method = models.CharField(max_length=20)
    sent_on = models.DateField()
    effective_on = models.DateField()
    reference = models.CharField(max_length=250)
    proof = models.ForeignKey("documents.Version", on_delete=models.PROTECT)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "kind", "elector"], name="assembly_delivery_unique"
            )
        ]


class AssemblyVote(models.Model):
    workflow = models.ForeignKey(
        AssemblyWorkflow, on_delete=models.PROTECT, related_name="votes"
    )
    resolution = models.ForeignKey(
        Resolution, on_delete=models.PROTECT, related_name="recorded_votes"
    )
    tour = models.PositiveSmallIntegerField(default=1)
    data = models.JSONField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    void_reason = models.CharField(max_length=500, blank=True)
    voided_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ["resolution__position", "tour", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["resolution", "tour"],
                condition=models.Q(voided_at__isnull=True),
                name="assembly_active_vote_unique",
            )
        ]


class AssemblyEvent(models.Model):
    workflow = models.ForeignKey(
        AssemblyWorkflow, on_delete=models.PROTECT, related_name="events"
    )
    action = models.CharField(max_length=50)
    data = models.JSONField(default=dict)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class AssemblyDecision(models.Model):
    vote = models.OneToOneField(
        AssemblyVote, on_delete=models.PROTECT, related_name="execution"
    )
    kind = models.CharField(max_length=30)
    data = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class AssemblyMandate(models.Model):
    decision = models.OneToOneField(
        AssemblyDecision, on_delete=models.PROTECT, related_name="mandate"
    )
    owner = models.ForeignKey(
        "core.Owner", on_delete=models.PROTECT, related_name="assembly_mandates"
    )
    kind = models.CharField(max_length=20)
    starts_on = models.DateField()
    ends_on = models.DateField()
    notes = models.CharField(max_length=1000, blank=True)


class AssemblyAppeal(models.Model):
    workflow = models.ForeignKey(
        AssemblyWorkflow, on_delete=models.PROTECT, related_name="appeals"
    )
    elector = models.CharField(max_length=220)
    resolution = models.ForeignKey(Resolution, on_delete=models.PROTECT)
    filed_on = models.DateField()
    reference = models.CharField(max_length=250)
    notes = models.TextField(max_length=5000, blank=True)
    status = models.CharField(max_length=20, default="filed")
    proof = models.ForeignKey("documents.Version", on_delete=models.PROTECT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "elector", "resolution", "reference"],
                name="assembly_appeal_reference_unique",
            )
        ]
