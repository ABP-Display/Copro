from django.conf import settings
from django.db import models


class Credential(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="security_credential")
    enabled = models.BooleanField(default=False)
    secret = models.TextField(blank=True)
    pending_secret = models.TextField(blank=True)
    pending_until = models.DateTimeField(null=True)
    last_counter = models.BigIntegerField(default=-1)
    recovery_hashes = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=0)
    must_change_password = models.BooleanField(default=False)
    enabled_at = models.DateTimeField(null=True)


class Policy(models.Model):
    require_managers = models.BooleanField(default=False)


class Attempt(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)


class SecurityEvent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class BackupRecord(models.Model):
    archive_id = models.UUIDField()
    action = models.CharField(max_length=20)
    filename = models.CharField(max_length=200)
    database_rows = models.PositiveBigIntegerField(default=0)
    files = models.PositiveIntegerField(default=0)
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
