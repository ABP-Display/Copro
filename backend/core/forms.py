from django.forms import ModelForm
from .models import Owner, Lot
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


class OwnerForm(ModelForm):
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if email:
            if Owner.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("Ce courriel est déjà associé à un copropriétaire.")
            users = get_user_model().objects.filter(email__iexact=email)
            if self.instance.user_id:
                users = users.exclude(pk=self.instance.user_id)
            if users.exists():
                raise ValidationError("Ce courriel est déjà utilisé par un autre compte.")
        return email

    class Meta:
        model = Owner
        fields = ["first_name", "last_name", "email", "phone"]


class LotForm(ModelForm):
    def clean_owner(self):
        owner=self.cleaned_data.get('owner')
        if self.instance.pk and self.instance.owner_id and self.instance.owner_id!=getattr(owner,'pk',None):
            from finance.models import Allocation, ChargeAllocation, Line, OwnershipChange
            if Allocation.objects.filter(lot=self.instance).exists() or ChargeAllocation.objects.filter(lot=self.instance).exists() or Line.objects.filter(owner_id=self.instance.owner_id).exists() or OwnershipChange.objects.filter(lot=self.instance).exists():
                raise ValidationError('Utilisez Gestion comptable → Mutations pour conserver la date, les comptes et l’historique du changement de propriétaire.')
        return owner
    class Meta:
        model = Lot
        fields = ["number", "kind", "floor", "area", "shares", "owner"]
