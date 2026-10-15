"""Manager-only annual decisions, funding checks and documented advance refunds."""
from datetime import date
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.views import manager_required, payload
from core.models import Lot
from documents.models import Version
from .models import FundingPolicy, FiscalYear, AdvanceRefund, AdvanceUse, FinanceProject, Line, BankMatch, Settlement, BankAccount
from .funding import rules, proof, refund_advance, use_ppt_advance, advance_balances, ADVANCE_CODES
from .services import amount, open_year, post_entry, financial_today
from .cycle import audit
from .views import errors
from .idempotency import idempotent


def policy_data(item):
    names = ['housing','received_on','annual_budget','budget_reference','ppt_adopted','ppt_amount',
             'fund_contribution','fund_reference','fund_proof_id','suspended','suspension_reference',
             'suspension_proof_id','reserve_authorized','advance_reference','advance_proof_id']
    return {name.removesuffix('_id'): getattr(item, name) for name in names}


@require_http_methods(['GET','POST'])
@manager_required
@errors
@idempotent
@transaction.atomic
def funding(request, resource):
    if request.method == 'GET':
        year = FiscalYear.objects.get(pk=request.GET['year'])
        policy = FundingPolicy.objects.filter(year=year).first()
        result = rules(policy or FundingPolicy(year=year))
        if not policy:
            result['warnings'].insert(0, 'Décisions annuelles non configurées : les appels historiques ne sont pas contrôlés par ce paramétrage. Enregistrez-le pour contrôler les prochains appels.')
        unattributed = Line.objects.filter(account__code__in=ADVANCE_CODES.values()).filter(lot__isnull=True).exists()
        if unattributed:
            result['errors'].append('Des avances du grand livre ne sont pas attribuées à un lot : faites corriger leur ventilation avant restitution.')
        return JsonResponse({'year':year.pk, 'closed':year.closed, 'configured':bool(policy),
            'policy': policy_data(policy or FundingPolicy(year=year)), 'rules':result,
            'years':list(FiscalYear.objects.values('id','name','closed')),
            'versions':[{'id':v.pk,'label':v.document.title+' · '+v.filename} for v in Version.objects.filter(document__archived=False).select_related('document')],
            'banks':list(BankAccount.objects.filter(active=True).values('id','name','kind')),
            'projects':list(FinanceProject.objects.filter(completed_on__isnull=True).values('id','name')),
            'advances':advance_balances(),
            'uses':[{'id':r.pk,'owner':str(r.owner),'lot':r.lot.number,'project':r.project.name,
                     'amount':str(r.amount),'date':str(r.entry.date),'reference':r.reference,
                     'cancelled':hasattr(r.entry,'reversal')} for r in AdvanceUse.objects.select_related('owner','lot','project','entry').order_by('-id')],
            'refunds':[{'id':r.pk,'owner':str(r.owner),'lot':r.lot.number,'code':r.account_code,
                        'amount':str(r.amount),'date':str(r.entry.date),'reference':r.reference,
                        'method':r.method,'cancelled':hasattr(r.entry,'reversal'),'proof':r.proof_id}
                       for r in AdvanceRefund.objects.select_related('owner','lot','entry').order_by('-id')]})
    data = payload(request)
    # Same global fiscal-year / lot locking order as all posting and mutation endpoints.
    list(FiscalYear.objects.select_for_update().order_by('id'))
    list(Lot.objects.select_for_update().order_by('id'))
    year = FiscalYear.objects.get(pk=data['year'])
    if year.closed:
        raise ValueError('Cet exercice est clôturé ; ses décisions annuelles sont conservées.')
    if resource == 'policy':
        item = FundingPolicy.objects.filter(year=year).first() or FundingPolicy(year=year)
        for name in ['annual_budget','ppt_amount','fund_contribution']:
            setattr(item,name,amount(data.get(name,0),False))
        for name in ['budget_reference','fund_reference','suspension_reference','advance_reference']:
            value = str(data.get(name,'')).strip()
            if len(value)>250: raise ValueError('Référence limitée à 250 caractères.')
            setattr(item,name,value)
        item.housing = data.get('housing','unknown')
        if item.housing not in ('unknown','housing','other'): raise ValueError('Destination invalide.')
        item.received_on = date.fromisoformat(data['received_on']) if data.get('received_on') else None
        if item.received_on and item.received_on > financial_today(): raise ValueError('La réception ne peut être future.')
        for name in ['ppt_adopted','suspended','reserve_authorized']:
            value = data.get(name, None if name=='ppt_adopted' else False)
            if type(value) is not bool and not (name=='ppt_adopted' and value is None): raise ValueError('Choix oui/non attendu.')
            setattr(item,name,value)
        for name in ['fund_proof','suspension_proof','advance_proof']:
            setattr(item,name,proof(data[name]) if data.get(name) else None)
        item.updated_by = request.user
        item.save()
        audit(request.user,'funding.policy',item.pk)
        return JsonResponse({'ok':True,'rules':rules(item)})
    if resource == 'refund':
        item = refund_advance(year,data,request.user)
        audit(request.user,'advance.refund',item.pk)
        return JsonResponse({'id':item.pk},status=201)
    if resource == 'use':
        item = use_ppt_advance(year,data,request.user)
        audit(request.user,'advance.use',item.pk)
        return JsonResponse({'id':item.pk},status=201)
    if resource in ('cancel-refund','cancel-use'):
        item = (AdvanceUse if resource=='cancel-use' else AdvanceRefund).objects.select_related('entry').get(pk=data['id'])
        if resource=='cancel-use' and item.project.completed_on:raise ValueError('Cette avance finance une opération terminée ; sa correction nécessite de traiter les comptes des travaux.')
        original = item.entry
        if hasattr(original,'reversal'): raise ValueError('Cette restitution est déjà corrigée.')
        if BankMatch.objects.filter(line__entry=original).exists() or Settlement.objects.filter(active=True,credit_line__entry=original).exists():
            raise ValueError('Dissociez d’abord les rapprochements et lettrages de la restitution.')
        on = date.fromisoformat(data['date'])
        if on < original.date: raise ValueError('La correction ne peut précéder la restitution.')
        open_year(year.pk,on)
        post_entry(year,on,original.journal,'Correction : '+original.label,
            [{'code':l.account.code,'owner':l.owner,'lot':l.lot,'project':l.project,'key':l.key,'debit':l.credit,'credit':l.debit}
             for l in original.lines.select_related('account','owner','lot','project','key')],request.user,
             reversal_of=original,kind=original.kind)
        audit(request.user,'advance.use.cancel' if resource=='cancel-use' else 'advance.refund.cancel',item.pk)
        return JsonResponse({'ok':True})
    raise ValueError('Action inconnue.')
