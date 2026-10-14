from django import forms
from .models import FiscalYear, ChargeKey, FundCall, Expense

class YearForm(forms.ModelForm):
    class Meta:
        model=FiscalYear; fields=["name","starts_on","ends_on"]
    def clean(self):
        data=super().clean()
        start,end=data.get("starts_on"),data.get("ends_on")
        if start and end:
            if end < start: raise forms.ValidationError("La fin doit suivre le début.")
            if FiscalYear.objects.filter(starts_on__lte=end,ends_on__gte=start).exists():
                raise forms.ValidationError("Un exercice existe déjà sur cette période.")
        return data

class KeyForm(forms.ModelForm):
    class Meta:
        model=ChargeKey; fields=["name","general","annual_budget"]

class CallForm(forms.ModelForm):
    class Meta:
        model=FundCall; fields=["year","key","label","date","due_date","amount","cost_center","kind","project","decision"]
    def clean(self):
        data=super().clean()
        if data.get("amount",0)<=0: raise forms.ValidationError("Le montant doit être positif.")
        if data.get("date") and data.get("due_date") and data["due_date"]<data["date"]:
            raise forms.ValidationError("L’échéance doit suivre la date de l’appel.")
        if data.get('kind') == 'works' and (not data.get('project') or not data.get('decision')):
            raise forms.ValidationError('Choisissez les travaux et indiquez la décision de financement.')
        if data.get('project') and (data['project'].key_id != getattr(data.get('key'),'pk',None) or data['project'].completed_on):
            raise forms.ValidationError('La clé doit être celle des travaux encore ouverts.')
        if data.get('kind') != 'works' and data.get('project'):
            raise forms.ValidationError('Une opération de travaux concerne uniquement un appel de type travaux.')
        return data

class ExpenseForm(forms.ModelForm):
    supplier = forms.CharField(max_length=150, required=False)
    class Meta:
        model=Expense; fields=["year","key","supplier","supplier_record","document","reference","label","date","due_date","amount","project"]

    def clean(self):
        data = super().clean()
        supplier = data.get('supplier_record')
        if supplier:
            from operations.models import Supplier
            supplier = Supplier.objects.select_for_update().get(pk=supplier.pk)
            if supplier.archived:
                self.add_error('supplier_record', 'Réactivez ce fournisseur avant de lui ajouter une facture.')
            data['supplier'] = supplier.name
        elif not data.get('supplier'):
            self.add_error('supplier', 'Choisissez un fournisseur ou renseignez son nom.')
        document = data.get('document')
        if document and document.archived:
            self.add_error('document', 'Restaurez le document avant de le joindre à la facture.')
        if data.get('project') and (data['project'].completed_on or data['project'].key_id != getattr(data.get('key'),'pk',None)):
            self.add_error('project','Travaux ouverts et clé correspondante requis.')
        if data.get('due_date') and data.get('date') and data['due_date']<data['date']:
            self.add_error('due_date','L’échéance ne peut précéder la facture.')
        return data
    def clean_amount(self):
        value=self.cleaned_data["amount"]
        if value<=0: raise forms.ValidationError("Le montant doit être positif.")
        return value
