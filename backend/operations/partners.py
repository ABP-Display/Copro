from core.access import is_manager
"""Manual supplier/contract follow-up. Dates do not constitute legal validation."""
import csv
import io
from datetime import timedelta
from decimal import Decimal

from django import forms
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from core.access import member_required
from core.views import manager_required, payload
from finance.models import AuditEvent
from finance.views import errors, safe_csv
from .models import Supplier, Contract, SupplierCertificate, Notice


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'trade', 'siret', 'contact', 'email', 'phone', 'address', 'notes', 'archived']

    def clean_siret(self):
        value = self.cleaned_data['siret'].replace(' ', '')
        if value and (len(value) != 14 or not value.isascii() or not value.isdigit()):
            raise forms.ValidationError('Le SIRET doit contenir 14 chiffres ; son existence reste à vérifier.')
        return value


class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = ['supplier', 'title', 'reference', 'starts_on', 'ends_on', 'notice_days', 'tacit_renewal', 'annual_cost', 'status', 'notes', 'documents']

    def clean(self):
        data = super().clean()
        supplier = data.get('supplier')
        if supplier and supplier.archived and supplier.pk != self.instance.supplier_id:
            self.add_error('supplier', 'Réactivez le fournisseur avant de lui ajouter un contrat.')
        start, end, notice = data.get('starts_on'), data.get('ends_on'), data.get('notice_days', 0)
        if notice is not None and notice > 3650:
            self.add_error('notice_days', 'Le préavis doit être compris entre 0 et 3650 jours.')
        if not end and (notice or data.get('tacit_renewal')):
            self.add_error('ends_on', 'Renseignez une date de fin pour suivre un préavis ou une reconduction.')
        if start and end and notice is not None:
            if end < start:
                self.add_error('ends_on', 'La fin doit suivre le début du contrat.')
            elif (end - start).days < notice:
                self.add_error('notice_days', 'Le préavis ne peut pas dépasser la durée du contrat.')
        return data

    def clean_documents(self):
        documents = self.cleaned_data['documents']
        previous = set(self.instance.documents.values_list('pk', flat=True)) if self.instance.pk else set()
        if any(d.archived and d.pk not in previous for d in documents):
            raise forms.ValidationError('Restaurez le document avant de le lier à ce contrat.')
        return documents


class CertificateForm(forms.ModelForm):
    class Meta:
        model = SupplierCertificate
        fields = ['supplier', 'kind', 'title', 'valid_until', 'document', 'archived']

    def clean_supplier(self):
        supplier = self.cleaned_data['supplier']
        if supplier.archived and supplier.pk != self.instance.supplier_id:
            raise forms.ValidationError('Réactivez le fournisseur avant de lui ajouter une attestation.')
        return supplier

    def clean_document(self):
        document = self.cleaned_data['document']
        if document and document.archived and document.pk != self.instance.document_id:
            raise forms.ValidationError('Restaurez le document avant de le lier à cette attestation.')
        return document


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'text']


def save_form(form_class, data, actor, instance=None):
    allowed = set(form_class.Meta.fields)
    if set(data) - allowed:
        raise ValueError('Champ inconnu.')
    # Explicit merging preserves document links, false booleans and historical suppliers.
    initial = {field: form_class.Meta.model._meta.get_field(field).get_default()
               for field in allowed if form_class.Meta.model._meta.get_field(field).has_default()} if instance is None else {}
    if instance:
        for field in allowed:
            model_field = instance._meta.get_field(field)
            if model_field.many_to_many:
                initial[field] = list(getattr(instance, field).values_list('pk', flat=True))
            elif model_field.many_to_one:
                initial[field] = getattr(instance, field + '_id')
            else:
                initial[field] = getattr(instance, field)
    merged = initial | data
    for key, value in merged.items():
        if key == 'documents':
            if not isinstance(value, list) or any(isinstance(v, (list, dict, bool)) for v in value):
                raise ValueError('La liste des documents est invalide.')
        elif isinstance(value, (list, dict)):
            raise ValueError('Les champs doivent être simples.')
        if key in ['archived', 'tacit_renewal'] and not isinstance(value, bool):
            raise ValueError('Les choix doivent être vrais ou faux.')
    form = form_class(merged, instance=instance)
    if not form.is_valid():
        raise ValueError(' · '.join(f'{key} : {" ".join(values)}' for key, values in form.errors.items()))
    item = form.save(commit=False)
    if instance is None:
        item.created_by = actor
    item.save()
    form.save_m2m()
    AuditEvent.objects.create(actor=actor, action=f'{item._meta.model_name}.{"update" if instance else "create"}', target=str(item.pk))
    return item


def supplier_data(item):
    active = [c for c in item.contracts.all() if c.status == 'active']
    return {'id': item.pk, **{f: getattr(item, f) for f in SupplierForm.Meta.fields},
            'active_contracts': len(active),
            'annual_cost': str(sum((c.annual_cost for c in active if c.annual_cost is not None), Decimal(0))),
            'unknown_costs': sum(c.annual_cost is None for c in active)}


def contract_data(item):
    today = timezone.localdate()
    return {'id': item.pk, **{f: getattr(item, f) for f in ContractForm.Meta.fields if f not in ['supplier', 'documents']},
            'supplier': item.supplier_id, 'supplier_name': item.supplier.name,
            'documents': [d.pk for d in item.documents.all()], 'notice_on': item.notice_on,
            'attention': 'expired' if item.ends_on and item.ends_on < today else
                         'notice' if item.notice_days and item.notice_on and item.notice_on <= today + timedelta(days=30) else
                         'ending' if item.ends_on and item.ends_on <= today + timedelta(days=30) else ''}


def certificate_data(item):
    return {'id': item.pk, 'supplier': item.supplier_id, 'supplier_name': item.supplier.name,
            'kind': item.kind, 'title': item.title, 'valid_until': item.valid_until,
            'document': item.document_id, 'archived': item.archived}


def notice_data(item):
    return {'id': item.pk, 'title': item.title, 'text': item.text, 'status': item.status,
            'published_at': item.published_at}


@require_http_methods(['GET', 'POST', 'PATCH'])
@manager_required
@errors
def partners(request, resource, pk=None):
    model, form, serialize = {
        'suppliers': (Supplier, SupplierForm, supplier_data),
        'contracts': (Contract, ContractForm, contract_data),
        'certificates': (SupplierCertificate, CertificateForm, certificate_data),
    }[resource]
    if request.method == 'GET':
        if pk is not None:
            return JsonResponse(serialize(model.objects.get(pk=pk)))
        query = model.objects.all()
        if resource == 'suppliers':
            query = query.prefetch_related('contracts')
        elif resource == 'contracts':
            query = query.select_related('supplier').prefetch_related('documents')
        else:
            query = query.select_related('supplier')
        items = [serialize(item) for item in query]
        if resource == 'contracts' and request.GET.get('format') == 'csv':
            stream = io.StringIO()
            writer = csv.writer(stream, delimiter=';')
            writer.writerow(['Contrat', 'Fournisseur', 'Référence', 'Début', 'Fin', 'Date limite de préavis', 'Reconduction déclarée', 'Coût annuel indicatif', 'Statut'])
            for item in items:
                writer.writerow([safe_csv(str(item[key]) if item.get(key) is not None else '') for key in
                                 ['title', 'supplier_name', 'reference', 'starts_on', 'ends_on', 'notice_on', 'tacit_renewal', 'annual_cost', 'status']])
            response = HttpResponse('\ufeff' + stream.getvalue(), content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="contrats.csv"'
            return response
        return JsonResponse({'items': items})
    if (request.method == 'POST' and pk is not None) or (request.method == 'PATCH' and pk is None):
        return JsonResponse({'error': 'Méthode non disponible pour cette adresse.'}, status=405)
    with transaction.atomic():
        instance = model.objects.select_for_update().get(pk=pk) if pk is not None else None
        item = save_form(form, payload(request), request.user, instance)
    return JsonResponse(serialize(item), status=201 if instance is None else 200)


@require_http_methods(['GET', 'POST'])
@member_required
@errors
def notices(request):
    if request.method == 'GET':
        query = Notice.objects.all()
        if not is_manager(request.user):
            query = query.filter(status='published')
        return JsonResponse({'items': [notice_data(item) for item in query]})
    with transaction.atomic():
        item = save_form(NoticeForm, payload(request), request.user)
    return JsonResponse(notice_data(item), status=201)


@require_http_methods(['PATCH'])
@manager_required
@errors
def notice(request, pk):
    data = payload(request)
    with transaction.atomic():
        item = Notice.objects.select_for_update().get(pk=pk)
        if set(data) == {'status'}:
            status = data['status']
            allowed = {'draft': ['published', 'archived'], 'published': ['draft', 'archived'], 'archived': ['draft']}
            if status not in allowed[item.status]:
                raise ValueError('Transition invalide. Rétablissez un brouillon avant de republier.')
            item.status = status
            if status == 'published':
                item.published_at = timezone.now()
            item.save()
            AuditEvent.objects.create(actor=request.user, action=f'notice.{status}', target=str(item.pk))
        else:
            if item.status != 'draft':
                raise ValueError('Retirez la publication avant de modifier le texte.')
            item = save_form(NoticeForm, data, request.user, item)
    return JsonResponse(notice_data(item))


def contract_alerts(today):
    horizon = today + timedelta(days=30)
    alerts = []
    for item in Contract.objects.filter(status='active', starts_on__lte=horizon, ends_on__isnull=False).select_related('supplier'):
        if item.ends_on < today:
            title, day = 'Contrat arrivé à échéance', item.ends_on
        elif item.notice_days and item.notice_on <= horizon:
            title, day = 'Préavis de contrat à vérifier', item.notice_on
        elif item.ends_on <= horizon:
            title, day = 'Contrat bientôt à échéance', item.ends_on
        else:
            continue
        alerts.append({'title': f'{title} : {item.title}', 'detail': f'{item.supplier.name} — {day}. Vérifiez les modalités du contrat.',
                       'level': 'warning' if day < today else 'info', 'page': 'operations', 'section': 'contracts'})
    for item in SupplierCertificate.objects.filter(archived=False, supplier__archived=False, valid_until__lte=horizon).select_related('supplier'):
        alerts.append({'title': f'Attestation à vérifier : {item.title}', 'detail': f'{item.supplier.name} — validité saisie jusqu’au {item.valid_until}.',
                       'level': 'warning' if item.valid_until < today else 'info', 'page': 'operations', 'section': 'certificates'})
    return alerts
