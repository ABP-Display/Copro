"""Annual funding checks and refundable advances, deliberately separate from the lot's 105 fund."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_CEILING

from django.db.models import Q, Sum
from core.models import Lot, Owner
from documents.models import Version
from .models import FundingPolicy, FundCall, Line, AdvanceRefund, AdvanceUse, FinanceProject
from .services import amount, distribute, post_entry, financial_today, bank_for_posting

ZERO = Decimal('0')
ADVANCE_CODES = {'reserve': '1031', 'ppt': '1032', 'temporary': '1033'}
SOURCES = [
    {'title': 'Fonds travaux : article 14-2-1', 'url': 'https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000043967792'},
    {'title': 'Avances : article 35', 'url': 'https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000053191341'},
    {'title': 'Avances remboursables : article 45-1', 'url': 'https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042078810'},
]


def tenth_anniversary(day):
    try:
        return day.replace(year=day.year + 10)
    except ValueError:
        return day.replace(year=day.year + 10, day=28)


def money(value):
    return str(value.quantize(Decimal('.01')))


def rules(policy, on=None):
    from .cycle import funds
    on = on or min(max(financial_today(), policy.year.starts_on), policy.year.ends_on)
    unknown = policy.housing == 'unknown' or policy.housing == 'housing' and not policy.received_on
    required_from = tenth_anniversary(policy.received_on) if policy.received_on else None
    mandatory = policy.housing == 'housing' and bool(required_from and on >= required_from)
    minimum = (max(policy.annual_budget * Decimal('.05'), policy.ppt_amount * Decimal('.025') if policy.ppt_adopted else ZERO)
               .quantize(Decimal('.01'), rounding=ROUND_CEILING)) if mandatory else ZERO
    paid_balance = sum((max(ZERO, Decimal(r['available'])) for r in funds(on)), ZERO)
    suspension_possible = (paid_balance > policy.annual_budget and
                           (not policy.ppt_adopted or paid_balance > policy.ppt_amount * Decimal('.5')))
    errors, warnings = [], []
    if unknown:
        errors.append('Renseignez la destination et la date de réception de l’immeuble.')
    if not policy.budget_reference or policy.annual_budget <= 0:
        errors.append('Renseignez le budget prévisionnel voté et sa référence.')
    if mandatory and policy.ppt_adopted is None:
        errors.append('Indiquez si un PPT a été adopté.')
    if policy.ppt_adopted and policy.ppt_amount <= 0:
        errors.append('Renseignez le montant des travaux du PPT adopté, sans le diviser par sa durée.')
    if on.year < 2025:
        errors.append('Le calendrier historique antérieur à 2025 nécessite une vérification manuelle.')
    if policy.suspended:
        if not suspension_possible or not policy.suspension_reference or not policy.suspension_proof_id:
            errors.append('La suspension exige les seuils légaux, une décision et sa pièce ; elle n’est jamais automatique.')
    elif policy.fund_contribution:
        if policy.fund_contribution < minimum:
            errors.append('La cotisation annuelle votée est inférieure au minimum calculé.')
        if not policy.fund_reference or not policy.fund_proof_id:
            errors.append('Rattachez la décision de cotisation et sa pièce.')
    elif mandatory:
        errors.append('Une cotisation annuelle doit être décidée ou une suspension justifiée.')
    if policy.housing == 'other':
        warnings.append('Destination sans habitation : pas d’obligation déduite de l’article 14-2-1 ; vérifier toute réserve volontaire séparément.')
    elif required_from and on < required_from:
        warnings.append('Le délai de dix ans n’est pas atteint à la date du contrôle.')
    if policy.received_on and policy.year.starts_on < tenth_anniversary(policy.received_on) <= policy.year.ends_on:
        warnings.append('Le délai de dix ans arrive pendant cet exercice : vérifier le calendrier de constitution ; aucun prorata n’est inventé.')
    warnings.append('Une petite taille ou un DTG sans travaux ne crée pas ici une dispense automatique du régime actuel.')
    return {'as_of': str(on), 'mandatory': mandatory, 'required_from': str(required_from or ''),
            'minimum': money(minimum), 'reserve_ceiling': money((Decimal(policy.annual_budget) / 6).quantize(Decimal('.01'), rounding='ROUND_DOWN')),
            'paid_fund_balance': money(paid_balance), 'suspension_possible': suspension_possible,
            'errors': errors, 'warnings': warnings, 'sources': SOURCES}


def proof(pk):
    item = Version.objects.select_related('document').get(pk=pk)
    if item.document.archived:
        raise ValueError('Choisissez une version documentaire non archivée.')
    return item


def validate_call(call):
    """Existing unconfigured accounts stay usable, visibly marked as unchecked in Funding & advances."""
    policy = FundingPolicy.objects.filter(year=call.year).first()
    if call.kind not in ('fund', 'advance') or not policy:
        return
    if call.kind == 'fund':
        result = rules(policy, call.date)
        if result['errors']:
            raise ValueError(' · '.join(result['errors']))
        if policy.suspended:
            raise ValueError('Les cotisations du fonds sont suspendues par la décision enregistrée.')
        if policy.fund_proof_id:
            proof(policy.fund_proof_id)
        total = FundCall.objects.filter(year=call.year, kind='fund', entry__isnull=False, entry__reversal__isnull=True).exclude(pk=call.pk).aggregate(value=Sum('amount'))['value'] or ZERO
        if total + call.amount > policy.fund_contribution:
            raise ValueError('Les appels publiés dépasseraient la cotisation annuelle votée.')
    else:
        if not policy.advance_reference or not policy.advance_proof_id:
            raise ValueError('Renseignez le fondement de l’avance et sa pièce dans Fonds & avances.')
        proof(policy.advance_proof_id)
        if call.advance_type == 'reserve':
            if not policy.reserve_authorized or not policy.budget_reference or not policy.annual_budget:
                raise ValueError('La réserve doit être prévue par le règlement, avec un budget voté renseigné.')
            balance, peak = ZERO, ZERO
            moves = Line.objects.filter(account__code='1031',entry__date__lte=call.year.ends_on).exclude(entry__kind__in=['carry','closing']).values('entry__date').annotate(c=Sum('credit'),d=Sum('debit')).order_by('entry__date')
            inserted = False
            for move in moves:
                if move['entry__date'] >= call.date and not inserted:
                    balance += call.amount; inserted=True
                    peak = max(peak,balance)
                balance += move['c']-move['d']
                if inserted: peak=max(peak,balance)
            if not inserted: peak=max(peak,balance+call.amount)
            if peak > policy.annual_budget / 6:
                raise ValueError('La réserve de trésorerie dépasserait un sixième du budget prévisionnel ; les soldes antérieurs sont inclus.')
        if call.advance_type == 'ppt' and not policy.ppt_adopted:
            raise ValueError('Une avance PPT nécessite un plan adopté et son échéancier justifié.')
        if call.advance_type != 'reserve' and not call.decision:
            raise ValueError('Indiquez la décision d’AG autorisant cette avance et son échéancier.')


def advance_balances(on=None):
    """Beneficiary is frozen at payment/call, never reassigned to the current lot owner."""
    from .cycle import owner_at
    on = on or financial_today()
    assets, paid, refunded, used = (defaultdict(lambda: ZERO) for _ in range(4))
    rows = Line.objects.filter(account__code__in=ADVANCE_CODES.values(), entry__date__lte=on).exclude(entry__kind__in=['carry','closing']).select_related('lot','owner','entry','account')
    for line in rows:
        if not line.lot_id:
            continue
        owner = line.owner
        if not owner:
            call = FundCall.objects.filter(entry=line.entry, kind='advance').first()
            allocation = call.allocations.filter(lot=line.lot).first() if call else None
            owner = allocation.owner if allocation else owner_at(line.lot, line.entry.date)
        if owner is None:
            continue
        key = (line.lot_id, owner.pk, line.account.code)
        assets[key] += line.credit - line.debit
        if line.entry.kind == 'opening':
            paid[key] += line.credit - line.debit
    calls = FundCall.objects.filter(kind='advance', entry__isnull=False, date__lte=on).filter(Q(entry__reversal__isnull=True) | Q(entry__reversal__date__gt=on)).prefetch_related('allocations__lot')
    for call in calls:
        code = ADVANCE_CODES[call.advance_type]
        allocations = list(call.allocations.all())
        allocated = defaultdict(lambda:ZERO)
        for line in call.entry.lines.filter(account__code__startswith='450', debit__gt=0):
            for match in line.debit_matches.filter(active=True, credit_line__entry__date__lte=on).exclude(credit_line__entry__kind='ownership'):
                eligible = [a for a in allocations if a.owner_id == line.owner_id and not a.transfers.filter(mutation__active=True, entry__created_at__lt=match.created_at).exists()]
                if eligible:
                    for lot, weight, value in distribute(match.amount, [(a.lot,max(ZERO,a.amount-allocated[a.lot_id])) for a in eligible], require_owner=False):
                        paid[(lot.pk, line.owner_id, code)] += value
                        allocated[lot.pk] += value
        for allocation in allocations:
            for transfer in allocation.transfers.filter(mutation__active=True, entry__date__lte=on):
                for line in transfer.entry.lines.filter(account__code__startswith='450', debit__gt=0):
                    matches = line.debit_matches.filter(active=True, credit_line__entry__date__lte=on).exclude(credit_line__entry__kind='ownership').aggregate(value=Sum('amount'))['value'] or ZERO
                    paid[(allocation.lot_id,line.owner_id,code)] += matches
    for item in AdvanceRefund.objects.filter(entry__date__lte=on).filter(Q(entry__reversal__isnull=True) | Q(entry__reversal__date__gt=on)):
        refunded[(item.lot_id,item.owner_id,item.account_code)] += item.amount
    for item in AdvanceUse.objects.filter(entry__date__lte=on).filter(Q(entry__reversal__isnull=True) | Q(entry__reversal__date__gt=on)):
        used[(item.lot_id,item.owner_id,'1032')] += item.amount
    lots = {item.pk:item for item in Lot.objects.all()}
    owners = {item.pk:item for item in Owner.objects.all()}
    return [{'lot':lot, 'lot_number':lots[lot].number, 'owner':owner, 'owner_name':str(owners[owner]), 'code':code,
             'constituted':money(assets[key]), 'paid':money(paid[key]), 'refunded':money(refunded[key]),'used':money(used[key]),
             'refundable':money(max(ZERO,min(assets[key],paid[key]-refunded[key]-used[key]))),
             'inconsistent':assets[key] < 0 or paid[key] - refunded[key] - used[key] < 0}
            for key in sorted(set(assets)|set(paid)|set(refunded)|set(used)) for lot,owner,code in [key]]


def check_advances():
    if any(row['inconsistent'] for row in advance_balances()):
        raise ValueError('Une avance a déjà été restituée ou affectée aux travaux : corrigez son utilisation avant le versement ou la constitution source.')


def refund_advance(year, data, user):
    on = date.fromisoformat(data['date'])
    lot = Lot.objects.select_for_update().get(pk=data['lot'])
    owner = Owner.objects.get(pk=data['owner'])
    code = str(data['code'])
    if code not in ADVANCE_CODES.values():
        raise ValueError('Seules les avances 1031, 1032 et 1033 sont remboursables ; le fonds 105 reste attaché au lot.')
    value = amount(data['amount'])
    row = next((r for r in advance_balances(on) if (r['lot'],r['owner'],r['code']) == (lot.pk,owner.pk,code)), None)
    if not row or value > Decimal(row['refundable']):
        raise ValueError('Le remboursement dépasse l’avance effectivement versée et encore disponible pour ce titulaire.')
    reference = str(data.get('reference','')).strip()
    if not reference or len(reference)>250:
        raise ValueError('Référence de la restitution requise (250 caractères maximum).')
    document = proof(data['proof'])
    method = data.get('method')
    bank = None
    if method == 'bank':
        from .reconciliation import bank_balance
        bank = bank_for_posting(data.get('bank'))
        if not bank or bank.kind == 'works' or bank_balance(bank,on) < value:
            raise ValueError('Choisissez une banque courante disposant de la trésorerie ; le compte dédié aux travaux est exclu.')
        counterpart = {'code':bank.account.code,'credit':value}
    elif method == 'account':
        counterpart = {'code':'450','owner':owner,'lot':lot,'credit':value}
    else:
        raise ValueError('Choisissez crédit du compte ou règlement bancaire enregistré.')
    entry = post_entry(year,on,'OD' if method=='account' else 'BQ','Restitution d’avance — lot '+lot.number,
                       [{'code':code,'owner':owner,'lot':lot,'debit':value},counterpart],user,reference,kind='advance-refund')
    result = AdvanceRefund.objects.create(owner=owner,lot=lot,account_code=code,amount=value,method=method,reference=reference,proof=document,bank=bank,entry=entry)
    check_advances()
    return result


def use_ppt_advance(year,data,user):
    from .cycle import owner_at
    from .services import key_weights
    on=date.fromisoformat(data['date'])
    lot=Lot.objects.get(pk=data['lot'])
    owner=Owner.objects.get(pk=data['owner'])
    if data.get('code')!='1032':
        raise ValueError('Seule une avance du PPT 1032 peut être affectée par ce parcours ; les autres avances restent restituables.')
    current=owner_at(lot,on)
    if not current or current.pk!=owner.pk:
        raise ValueError('Une avance d’un ancien titulaire doit être restituée ; son affectation aux travaux de l’acquéreur n’est pas présumée autorisée.')
    project=FinanceProject.objects.select_for_update().get(pk=data['project'])
    if project.completed_on: raise ValueError('Cette opération est terminée.')
    if not any(l.pk==lot.pk and weight>0 for l,weight in key_weights(project.key,on)):
        raise ValueError('Ce lot n’est pas concerné par la clé des travaux.')
    value=amount(data['amount'])
    row=next((r for r in advance_balances(on) if (r['lot'],r['owner'],r['code'])==(lot.pk,owner.pk,'1032')),None)
    if not row or value>Decimal(row['refundable']):raise ValueError('Le montant dépasse l’avance PPT réellement versée et disponible pour ce titulaire.')
    reference=str(data.get('reference','')).strip()
    if not reference or len(reference)>250:raise ValueError('Référence de décision requise, limitée à 250 caractères.')
    document=proof(data['proof'])
    entry=post_entry(year,on,'OD','Affectation d’avance PPT : '+project.name,
        [{'code':'1032','owner':owner,'lot':lot,'project':project,'key':project.key,'debit':value},
         {'code':'102','project':project,'key':project.key,'credit':value}],user,reference,kind='advance-use')
    result=AdvanceUse.objects.create(owner=owner,lot=lot,project=project,amount=value,reference=reference,proof=document,entry=entry)
    check_advances()
    return result
