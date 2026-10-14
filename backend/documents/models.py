import uuid
from pathlib import Path
from django.conf import settings
from django.db import models


def asset_path(instance, filename):
    return f"documents/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Folder(models.Model):
    name = models.CharField(max_length=150, unique=True)
    class Meta:
        ordering = ["name"]


class Document(models.Model):
    title = models.CharField(max_length=150)
    folder = models.ForeignKey(Folder, on_delete=models.PROTECT, null=True, blank=True)
    published = models.BooleanField(default=False)
    archived = models.BooleanField(default=False)
    current = models.OneToOneField("Version", on_delete=models.PROTECT, null=True, related_name="current_for")
    class Meta:
        ordering = ["title", "id"]


class Version(models.Model):
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="versions")
    file = models.FileField(upload_to=asset_path, max_length=200)
    filename = models.CharField(max_length=200)
    size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    checksum = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    class Meta:
        ordering = ["-id"]
