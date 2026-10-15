"""Versioned presentation and cross-checks for the five annual statements.

No journal is rewritten by a report. Presentation regroupings are disclosed;
closed dossiers keep their original snapshot, including older report versions.
"""
from collections import defaultdict
from decimal import Decimal
from django.db.models import Q
from .models import Line, FiscalYear, Budget, FinanceProject, AnnualSettlement, Organization, ExpensePayment

ZERO = Decimal('0')
SOURCE = 'https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000258200/'


def m(value):
    return str(value.quantize(Decimal('.01')))


def project_states(year):
    completed, pending = [], []
    for p in FinanceProject.objects.select_related('key').all():
        if p.decided_on and p.decided_on > year.ends_on:
            continue
        lines = list(Line.objects.filter(project=p,entry__date__lte=year.ends_on)
            .exclude(entry__kind__in=['carry','closing']).select_related('account','entry'))
        # Include inverse entries: their accounting date determines the period of correction.
        actual = [l for l in lines if l.account.code.startswith('67') and l.entry.kind!='project-complete']
        provisions = [l for l in lines if l.account.code=='102' and l.entry.kind!='project-complete']
        received = [l for l in lines if l.account.code.startswith('13')]
        receivable = [l for l in lines if l.account.code.startswith('441')]
        cash = [l for l in lines if l.account.code.startswith(('512','514','531')) and l.credit]
        amount = lambda items, sign=1: sum(((l.debit-l.credit)*sign for l in items),ZERO)
        costs, funding = amount(actual), amount(provisions,-1)
        row = {'id':p.pk,'project':p.name,'key':p.key.name,'decision':p.decision,
               'voted_on':str(p.decided_on or ''),'voted':m(p.budget),'expenses':m(costs),
               'paid':m(sum((pay.amount for pay in ExpensePayment.objects.filter(expense__project=p,entry__date__lte=year.ends_on)
                    .exclude(entry__reversal__date__lte=year.ends_on)),ZERO)+sum((l.credit-l.debit for l in cash if not hasattr(l.entry,'expense_payment')),ZERO)),
               'funding':m(funding),'subsidies':m(amount(received,-1)),
               'receivable':m(amount(receivable)), 'waiting':m(funding+amount(received,-1)-costs),
               'completed_on':str(p.completed_on or ''),
               'details': [{'date':str(l.entry.date),'number':l.entry.number,'label':l.entry.label,
                            'code':l.account.code,'debit':m(l.debit),'credit':m(l.credit)} for l in lines]}
        if p.completed_on and year.starts_on <= p.completed_on <= year.ends_on:
            completed.append(row)
        elif (not p.completed_on or p.completed_on>year.ends_on) and (lines or p.decided_on):
            pending.append(row)
    return completed,pending


def financial_state(year, reg, pending):
    balances = defaultdict(lambda:ZERO)
    labels, names = {}, {}
    query = Line.objects.filter(entry__year=year).exclude(entry__kind='closing').select_related('account','owner','supplier','entry')
    for line in query:
        code = line.account.code
        if code.startswith(('6','7')):
            continue
        identity = (code, line.owner_id, line.supplier_id)
        balances[identity] += line.debit-line.credit
        labels[identity] = line.account.name
        names[identity] = str(line.owner) if line.owner_id else line.supplier.name if line.supplier_id else ''
    simulated = not AnnualSettlement.objects.filter(year=year,active=True).exists()
    if simulated:
        for row in reg['rows']:
            identity = ('450',row['owner'],None)
            balances[identity] += Decimal(row['adjustment'])
            labels[identity] = 'Copropriétaires après répartition proposée'
            names[identity] = row.get('owner_name',row.get('name',str(row['owner'])))
    pending_ids = [r['id'] for r in pending]
    # Legacy journals retain 102 financing and 120 prior costs separately. Regroup
    # these in the pending-operation balance (12) for the annual presentation.
    for line in query.filter(project_id__in=pending_ids).filter(Q(account__code__in=['102','120']) | Q(account__code__startswith='13')):
        balances[(line.account.code,line.owner_id,line.supplier_id)] -= line.debit-line.credit
    waiting = sum((Decimal(r['waiting']) for r in pending),ZERO)
    if waiting:
        balances[('12',None,None)] -= waiting
        labels[('12',None,None)] = 'Solde en attente sur travaux (annexe 5)'
        names[('12',None,None)] = ''
    result = []
    for identity,value in sorted(balances.items(),key=lambda x:(x[0][0],x[0][1] or 0,x[0][2] or 0)):
        if not value: continue
        code,owner,supplier = identity
        category = 'Trésorerie' if code.startswith('5') else 'Avances, provisions et fonds' if code.startswith('1') else 'Créances et dettes'
        # Distinct tiers with identical names are kept distinct before summing.
        result.append({'identity':f'{code}:{owner or 0}:{supplier or 0}','code':code,'label':labels[identity],
            'third_party':names[identity],'group':category,'debit':m(max(value,ZERO)),
            'credit':m(max(-value,ZERO))})
    return result,simulated


def build(year, reg):
    from .cycle import regularization_data, digest
    previous = FiscalYear.objects.filter(ends_on__lt=year.starts_on).order_by('-ends_on').first()
    following = list(FiscalYear.objects.filter(starts_on__gt=year.ends_on).order_by('starts_on')[:2])
    completed,pending = project_states(year)
    state,simulated = financial_state(year,reg,pending)
    before = []
    if previous:
        saved = getattr(previous,'closure',None) if hasattr(previous,'closure') else None
        # Older closures are deliberately not regenerated as a new certified pack.
        if saved and saved.snapshot.get('regulatory'):
            before = saved.snapshot['regulatory']['annexes'][0]['rows']
        else:
            _,old_pending = project_states(previous)
            old_reg = AnnualSettlement.objects.filter(year=previous,active=True).first()
            before,_ = financial_state(previous,old_reg.data if old_reg else regularization_data(previous),old_pending)
    old = {r['identity']:r for r in before}
    now = {r['identity']:r for r in state}
    state = [{**(now.get(key) or old[key]),'debit':now.get(key,{}).get('debit','0.00'),
              'credit':now.get(key,{}).get('credit','0.00'),
              'previous_debit':old.get(key,{}).get('debit') if previous else None,
              'previous_credit':old.get(key,{}).get('credit') if previous else None} for key in sorted(set(old)|set(now))]
    def current(selected):
        result = defaultdict(lambda:ZERO)
        if selected:
            for l in Line.objects.filter(entry__year=selected).exclude(entry__kind__in=['closing','regularization']).select_related('account'):
                if l.account.code.startswith(('6','7')) and not l.account.code.startswith('67') and l.account.code not in ('702','706'):
                    result[(l.account.code,l.key_id)] += (l.debit-l.credit)*(1 if l.account.code.startswith('6') else -1)
        return result
    def budgets(selected):
        specific,centres = {},defaultdict(lambda:ZERO)
        if selected:
            for b in Budget.objects.filter(year=selected).select_related('account'):
                key = (b.account.code,b.key_id)
                if b.cost_center_id is None: specific[key] = b.amount
                else: centres[key] += b.amount
        return {key:specific.get(key,centres.get(key)) for key in set(specific)|set(centres)}
    from .models import Account, ChargeKey
    names = dict(Account.objects.values_list('code','name'))
    keys = dict(ChargeKey.objects.values_list('id','name'))
    actual, prior, planned = current(year),current(previous),budgets(year)
    future = [budgets(following[i] if len(following)>i else None) for i in range(2)]
    rows = []
    for identity in sorted(set(actual)|set(prior)|set(planned)|set(future[0])|set(future[1]),key=lambda x:(x[1] or 0,x[0])):
        code,key = identity
        rows.append({'code':code,'label':names.get(code,code),'key':keys.get(key,'Non ventilé'),
            'side':'Charges' if code.startswith('6') else 'Produits',
            'actual_previous':m(prior.get(identity,ZERO)) if previous else None,
            'budget_current':m(planned[identity]) if identity in planned else None,
            'actual_current':m(actual.get(identity,ZERO)),
            'budget_next':m(future[0][identity]) if identity in future[0] else None,
            'budget_following':m(future[1][identity]) if identity in future[1] else None})
    general = {}
    for r in rows:
        if r['code'] not in general:
            general[r['code']] = {**r,'key':'Toutes clés',**{k:None for k in ['actual_previous','budget_current','actual_current','budget_next','budget_following']}}
        g = general[r['code']]
        for k in ['actual_previous','budget_current','actual_current','budget_next','budget_following']:
            if r[k] is not None: g[k] = m(Decimal(g[k] or '0')+Decimal(r[k]))
    expenses = sum((Decimal(r['expenses']) for r in completed),ZERO)
    products = sum((Decimal(r['funding'])+Decimal(r['subsidies']) for r in completed),ZERO)
    annex2 = [dict(r,activity='Opérations courantes') for r in general.values()]
    for code,label,value in [('671','Travaux et opérations exceptionnelles terminés',expenses),('702','Financement des opérations terminées',products)]:
        annex2.append({'code':code,'label':label,'side':'Charges' if code=='671' else 'Produits','activity':'Travaux terminés','actual_current':m(value),
                       'actual_previous':None,'budget_current':None,'budget_next':None,'budget_following':None})
    errors = list(reg.get('errors',[]))
    warnings = []
    totals = {k:sum((Decimal(r[k]) for r in state),ZERO) for k in ['debit','credit']}
    delta = totals['debit']-totals['credit']
    checks = [{'label':'Annexe 1 : équilibre après répartition','left':m(totals['debit']),'right':m(totals['credit']),'ok':delta==0},
              {'label':'Annexes 2 et 4 : charges des opérations terminées','left':m(expenses),'right':m(sum((Decimal(r['expenses']) for r in completed),ZERO)),'ok':True},
              {'label':'Annexes 1 et 5 : solde en attente des travaux','left':m(sum((Decimal(r['credit'])-Decimal(r['debit']) for r in state if r['code']=='12'),ZERO)),
               'right':m(sum((Decimal(r['waiting']) for r in pending),ZERO)),'ok':True}]
    ledger_works = Line.objects.filter(entry__year=year,account__code__startswith='67').exclude(entry__kind='closing')
    pending_ids = [r['id'] for r in pending]
    recognized = sum((l.debit-l.credit for l in ledger_works.exclude(project_id__in=pending_ids)),ZERO)
    checks.append({'label':'Annexe 4 et grand livre : travaux terminés ou non attribués','left':m(expenses),'right':m(recognized),'ok':expenses==recognized})
    current_totals = {side:sum((Decimal(r['actual_current']) for r in rows if r['side']==side),ZERO) for side in ['Charges','Produits']}
    for side in ['Charges','Produits']:
        check = sum((Decimal(r['actual_current']) for r in annex2 if r['activity']=='Opérations courantes' and r['side']==side),ZERO)
        checks.append({'label':f'Annexes 2 et 3 : {side.lower()} courants','left':m(check),'right':m(current_totals[side]),'ok':check==current_totals[side]})
    for c in checks:
        c['ok'] = c['left']==c['right']
        if not c['ok']: errors.append(c['label']+' : écart à expliquer.')
    if simulated: warnings.append('État financier après répartition proposée : la régularisation n’est pas comptabilisée. Faire approuver les comptes avant de l’appliquer.')
    if not previous: warnings.append('Aucun exercice précédent : comparatif N−1 non disponible, les cases restent vides.')
    if len(following)<2: warnings.append('Créer les exercices et saisir les budgets futurs pour compléter les colonnes N+1 et N+2.')
    if any(r['key']=='Non ventilé' and Decimal(r['actual_current']) for r in rows): errors.append('Des opérations courantes ne sont pas ventilées par clé.')
    for p in completed+pending:
        if not p['voted_on']: errors.append('Travaux « '+p['project']+' » : date de la décision manquante.')
    if Line.objects.filter(entry__year=year,account__code__in=['1031','1032','1033'],lot__isnull=True).exists():
        errors.append('Des avances ne sont pas ventilées par lot et titulaire.')
    if Line.objects.filter(entry__year=year,account__code__startswith='16').exists():
        errors.append('Emprunt collectif présent : compléter et faire valider son échéancier et ses états spécifiques avant utilisation de ce modèle en AG.')
    if Line.objects.filter(entry__date__lte=year.ends_on,project_id__in=[r['id'] for r in completed+pending]).filter(Q(account__code__startswith='13')|Q(account__code__in=['711','712','713'])).exists():
        errors.append('Une opération comporte une aide, un emprunt ou une indemnité : rapprocher ses engagements, versements et imputations dans un état complémentaire avant utilisation en AG.')
    org,_ = Organization.objects.get_or_create(pk=1)
    pack = {'version':'2026.10','organization':org.name,'address':org.address,'year':year.name,
        'period':{'start':str(year.starts_on),'end':str(year.ends_on)},
        'comparison':{'previous':previous.name if previous else None,'next':following[0].name if following else None,'following':following[1].name if len(following)>1 else None},
        'after_allocation':'proposed' if simulated else 'posted','checks':checks,'errors':list(dict.fromkeys(errors)),'warnings':warnings,
        'notes':['Soldes débiteurs et créditeurs séparés par tiers identifié, sans compensation entre personnes distinctes.',
                 'La présentation du compte 12 regroupe les financements 102 et coûts en attente 120 des opérations non terminées, avec leurs charges de l’exercice. Elle ne modifie aucune écriture.',
                 'Une case vide désigne une donnée non renseignée, pas un montant nul. Les engagements non comptabilisés et prêts collectifs nécessitent leurs pièces complémentaires.'],
        'sources':[{'title':'Décret n° 2005-240 — comptes et annexes','url':SOURCE}],
        'annexes':[
            {'number':1,'title':'État financier après répartition','columns':['group','code','label','third_party','previous_debit','previous_credit','debit','credit'],'rows':state},
            {'number':2,'title':'Compte de gestion général','columns':['activity','side','code','label','actual_previous','budget_current','actual_current','budget_next','budget_following'],'rows':annex2},
            {'number':3,'title':'Opérations courantes par clé de répartition','columns':['key','side','code','label','actual_previous','budget_current','actual_current','budget_next','budget_following'],'rows':rows},
            {'number':4,'title':'Travaux et opérations exceptionnelles terminés','columns':['project','key','voted_on','voted','expenses','funding','subsidies','completed_on'],'rows':completed},
            {'number':5,'title':'Travaux et opérations exceptionnelles non terminés','columns':['project','key','voted_on','voted','paid','expenses','funding','subsidies','waiting','receivable'],'rows':pending}]}
    pack['source_hash'] = digest(pack)
    return pack
