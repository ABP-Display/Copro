"""Recorded banking movements only: no connection to a bank or payment initiation."""
import re
import uuid
from datetime import date
from decimal import Decimal
from django import forms
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from core.views import manager_required, payload
from .models import Account, BankAccount, BankTransfer, Line, Organization, CostCenter, AuditEvent
from .services import amount, open_year, post_entry
from .views import errors


class BankForm(forms.ModelForm):
    iban = forms.CharField(max_length=64, required=False)
    class Meta:
        model = BankAccount
        fields = ['name', 'bank_name', 'iban', 'kind', 'active']

    def clean_iban(self):
        iban = ''.join(self.cleaned_data['iban'].split()).upper()
        if iban and not re.fullmatch(r'[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}', iban):
            raise forms.ValidationError('Format IBAN invalide. Le titulaire et les coordonnées restent à vérifier.')
        return iban


def bank_data(bank, balance=None):
    return {'id': bank.pk, 'name': bank.name, 'bank_name': bank.bank_name, 'iban': bank.iban,
            'kind': bank.kind, 'active': bank.active, 'is_default': bank.is_default,
            'account_code': bank.account.code, 'account_active': bank.account.active,
            'balance': str(balance or Decimal(0))}


def transfer_data(item):
    return {'id': item.pk, 'request_id': str(item.operation_id), 'source': item.source_id,
            'source_name': item.source.name, 'destination': item.destination_id, 'destination_name': item.destination.name,
            'amount': str(item.amount), 'date': item.entry.date, 'number': item.entry.number,
            'reference': item.entry.reference, 'label': item.entry.label}


@require_http_methods(['GET', 'POST', 'PATCH'])
@manager_required
@errors
def banks(request, pk=None):
    if request.method == 'GET':
        day = date.fromisoformat(request.GET.get('date') or str(timezone.localdate()))
        balances = {r['account_id']: r['debit'] - r['credit'] for r in
                    Line.objects.filter(account__code__startswith='512', entry__date__lte=day).exclude(entry__kind='carry')
                    .values('account_id').annotate(debit=Sum('debit'), credit=Sum('credit'))}
        items = list(BankAccount.objects.select_related('account'))
        if pk is not None:
            bank = BankAccount.objects.select_related('account').get(pk=pk)
            return JsonResponse(bank_data(bank, balances.get(bank.account_id)))
        linked = {b.account_id for b in items}
        unused = Account.objects.filter(code__startswith='512',line__isnull=False).exclude(pk__in=linked).distinct()
        return JsonResponse({'items': [bank_data(b, balances.get(b.account_id)) for b in items],
                             'unassigned': [{'code': a.code, 'name': a.name, 'active': a.active, 'balance': str(balances.get(a.pk, Decimal(0)))} for a in unused],
                             'date': day, 'note': 'Soldes des écritures disponibles, sans double comptage des reports. Vérifiez les relevés dans Rapprochement bancaire ; une fiche de banque ne certifie pas son solde.'})
    if (pk is None) != (request.method == 'POST'):
        return JsonResponse({'error': 'Adresse incompatible avec la méthode.'}, status=405)
    data = payload(request)
    if set(data) - set(BankForm.Meta.fields) - {'account_code'}:
        raise ValueError('Champ inconnu.')
    if 'active' in data and not isinstance(data['active'], bool):
        raise ValueError('Choix actif invalide.')
    if any(isinstance(v, (list, dict)) for v in data.values()):
        raise ValueError('Champs simples attendus.')
    with transaction.atomic():
        # Same singleton lock for creating/editing default bank metadata.
        Account.objects.get_or_create(code='512', defaults={'name': 'Banque'})
        Account.objects.select_for_update().get(code='512')
        item = BankAccount.objects.select_for_update().get(pk=pk) if pk else None
        initial = {f: getattr(item, f) for f in BankForm.Meta.fields} if item else {'active': True, 'kind': 'current'}
        code = data.get('account_code', item.account.code if item else '')
        if not isinstance(code, str) or not code.isascii() or not code.isdigit() or not code.startswith('512') or len(code) > 20:
            raise ValueError('Le code bancaire doit commencer par 512 et contenir 3 à 20 chiffres.')
        config, _ = Organization.objects.get_or_create(pk=1)
        if len(code) < config.code_length and not Account.objects.filter(code=code).exists():
            raise ValueError('Code trop court pour la configuration comptable.')
        if item and item.account.code != code:
            raise ValueError('Conservez le compte comptable de cette banque ; créez une autre fiche pour un autre compte.')
        if item and item.is_default and data.get('active') is False:
            raise ValueError('Choisissez d’abord une autre banque par défaut.')
        form = BankForm(initial | {k: v for k, v in data.items() if k in BankForm.Meta.fields}, instance=item)
        if not form.is_valid():
            raise ValueError(' · '.join(' '.join(v) for v in form.errors.values()))
        bank = form.save(commit=False)
        if item is None:
            account, _ = Account.objects.get_or_create(code=code, defaults={'name': bank.name})
            if not account.active: raise ValueError('Réactivez ce compte comptable avant de l’associer.')
            if BankAccount.objects.filter(account=account).exists(): raise ValueError('Ce compte comptable est déjà associé à une banque.')
            bank.account = account
            bank.is_default = not BankAccount.objects.filter(is_default=True).exists() and bank.active
        bank.save()
        AuditEvent.objects.create(actor=request.user, action='bank.save', target=str(bank.pk))
    return JsonResponse(bank_data(bank), status=200 if item else 201)


@require_http_methods(['POST'])
@manager_required
@errors
def default_bank(request, pk):
    with transaction.atomic():
        Account.objects.get_or_create(code='512', defaults={'name': 'Banque'})
        Account.objects.select_for_update().get(code='512')
        bank = BankAccount.objects.select_for_update(of=('self',)).select_related('account').get(pk=pk)
        if not bank.active or not bank.account.active:
            raise ValueError('La banque et son compte comptable doivent être actifs.')
        BankAccount.objects.filter(is_default=True).update(is_default=False)
        bank.is_default = True
        bank.save(update_fields=['is_default'])
        AuditEvent.objects.create(actor=request.user, action='bank.default', target=str(pk))
    return JsonResponse({'ok': True})


@require_http_methods(['GET', 'POST'])
@manager_required
@errors
def transfers(request):
    if request.method == 'GET':
        return JsonResponse({'items': [transfer_data(t) for t in BankTransfer.objects.select_related('entry', 'source', 'destination').order_by('-entry__date', '-id')[:100]]})
    data = payload(request)
    if set(data) - {'request_id', 'year', 'date', 'source', 'destination', 'amount', 'reference', 'label', 'cost_center'}:
        raise ValueError('Champ inconnu.')
    operation = uuid.UUID(str(data['request_id']))
    day = date.fromisoformat(data['date'])
    value = amount(data['amount'])
    if isinstance(data['source'], bool) or isinstance(data['destination'], bool): raise ValueError('Banques invalides.')
    source_id, destination_id = int(data['source']), int(data['destination'])
    if source_id == destination_id: raise ValueError('Choisissez deux banques différentes.')
    reference, label = str(data.get('reference', '')).strip(), str(data.get('label') or 'Transfert entre comptes bancaires').strip()
    if len(reference) > 100 or not label or len(label) > 250: raise ValueError('Référence ou libellé invalide.')
    with transaction.atomic():
        year = open_year(data['year'], day)
        previous = BankTransfer.objects.select_for_update().select_related('entry', 'source', 'destination').filter(operation_id=operation).first()
        if previous:
            expected_center = int(data['cost_center']) if data.get('cost_center') else None
            if (previous.source_id, previous.destination_id, previous.amount, previous.entry.date, previous.entry.year_id, previous.entry.reference, previous.entry.label, previous.entry.cost_center_id) != (source_id, destination_id, value, day, year.pk, reference, label, expected_center):
                raise ValueError('Cet identifiant de transfert a déjà été utilisé avec d’autres données.')
            return JsonResponse(transfer_data(previous))
        choices = {b.pk: b for b in BankAccount.objects.select_for_update(of=('self',)).select_related('account').filter(pk__in=[source_id, destination_id]).order_by('pk')}
        if len(choices) != 2: raise ValueError('Banque introuvable.')
        source, destination = choices[source_id], choices[destination_id]
        if any(not b.active or not b.account.active for b in choices.values()): raise ValueError('Les banques et leurs comptes doivent être actifs.')
        center = CostCenter.objects.get(pk=data['cost_center']) if data.get('cost_center') else None
        entry = post_entry(year, day, 'BQ', label, [{'code': source.account.code, 'credit': value}, {'code': destination.account.code, 'debit': value}], request.user, reference, cost_center=center)
        item = BankTransfer.objects.create(operation_id=operation, source=source, destination=destination, amount=value, entry=entry)
        AuditEvent.objects.create(actor=request.user, action='bank.transfer', target=str(item.pk))
    return JsonResponse(transfer_data(item), status=201)
