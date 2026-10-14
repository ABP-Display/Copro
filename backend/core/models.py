from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings
from django.db.models.functions import Lower


class Owner(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="owner_profile")
    must_change_password = models.BooleanField(default=False)

    class Meta:
        ordering = ["last_name", "first_name", "id"]
        constraints = [models.UniqueConstraint(Lower("email"), condition=~models.Q(email=""), name="owner_email_unique")]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Lot(models.Model):
    class Kind(models.TextChoices):
        APARTMENT = "apartment", "Appartement"
        PARKING = "parking", "Parking"
        CELLAR = "cellar", "Cave"
        COMMERCIAL = "commercial", "Local commercial"
        OTHER = "other", "Autre"

    number = models.CharField(max_length=30, unique=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.APARTMENT)
    floor = models.CharField(max_length=30, blank=True)
    area = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True,
                               validators=[MinValueValidator(Decimal("0"))])
    shares = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                 validators=[MinValueValidator(Decimal("0"))])
    owner = models.ForeignKey(Owner, on_delete=models.PROTECT, null=True, blank=True, related_name="lots")

    class Meta:
        ordering = ["number", "id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(shares__gte=0), name="lot_shares_positive"),
            models.CheckConstraint(condition=models.Q(area__gte=0) | models.Q(area__isnull=True), name="lot_area_positive"),
        ]
