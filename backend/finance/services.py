from decimal import Decimal, InvalidOperation, ROUND_DOWN
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from core.models import Lot
from .models import Account, Entry, Line, FiscalYear, Share, Allocation, Organization, Journal, AuditEvent, ExpensePayment, BankAccount

CHART = {"401": "Fournisseurs", "450": "Copropriétaires", "512": "Banque", "601": "Charges courantes", "701": "Provisions sur opérations courantes", '702':'Provisions sur travaux', '671':'Travaux décidés', '102':'Provisions pour travaux', '105':'Fonds travaux', '1031':'Avances de trésorerie', '120':'Solde en attente sur travaux'}

def financial_today():
    return timezone.localdate()

from pathlib import Path
import csv
with (Path(__file__).parent/'data/init_french-avance.csv').open(encoding='utf-8-sig',newline='') as chart_file:
    CHART.update({row['code']:row['name'] for row in csv.DictReader(chart_file,delimiter=';')})


def amount(value, positive=True):
    try:
        value = Decimal(str(value))
        if not value.is_finite() or value != value.quantize(Decimal("0.01")) or abs(value) >= Decimal("10000000000"):
            raise ValueError("Le montant doit comporter au plus deux décimales et être inférieur à 10 milliards.")
        if value < 0 or (positive and value == 0):
            raise ValueError("Le montant doit être positif.")
        return value
    except (InvalidOperation, TypeError):
        raise ValueError("Montant invalide.")


def open_year(pk, date):
    year = FiscalYear.objects.select_for_update().get(pk=pk)
    if year.closed:
        raise ValueError("Cet exercice est clôturé.")
    if not year.starts_on <= date <= year.ends_on:
        raise ValueError("La date est hors de l’exercice.")
    return year


def post_entry(year, date, journal, label, lines, user, reference="", cost_center=None, reversal_of=None, kind='normal'):
    """Caller holds the fiscal-year row lock inside an atomic transaction."""
    if year.closed or not year.starts_on <= date <= year.ends_on:
        raise ValueError("Exercice fermé ou date hors exercice.")
    if date>financial_today() and not (reversal_of and reversal_of.date==date):raise ValueError('Une opération future reste à préparer ; seules les opérations réalisées sont comptabilisées.')
    if len(lines) < 2:
        raise ValueError("Une écriture nécessite au moins deux lignes.")
    settings, _ = Organization.objects.get_or_create(pk=1)
    from .models import AnnualSettlement
    if kind == 'normal' and AnnualSettlement.objects.filter(year=year,active=True).exists() and any(str(r['code']).startswith(('6','7')) for r in lines):
        raise ValueError('Annulez la régularisation avant de modifier les charges ou produits de cet exercice.')
    if settings.analytic_required and cost_center is None and kind not in ('opening','carry','closing','regularization','project-complete','ownership','advance-refund','advance-use'):
        raise ValueError("Une comptabilité analytique est obligatoire.")
    if cost_center and not cost_center.active:
        raise ValueError("Cette comptabilité analytique est inactive.")
    defaults = {"OD":"Opérations diverses","BQ":"Banque","AC":"Achats","AP":"Appels de fonds",'AN':'À-nouveaux'}
    if journal in defaults:
        Journal.objects.get_or_create(code=journal,defaults={"name":defaults[journal]})
    if not Journal.objects.filter(code=journal,active=True).exists():
        raise ValueError("Journal inconnu ou inactif.")
    normalized = []
    for line in lines:
        debit, credit = amount(line.get("debit") or 0, False), amount(line.get("credit") or 0, False)
        if (debit > 0) == (credit > 0):
            raise ValueError("Chaque ligne doit avoir un débit ou un crédit strictement positif.")
        code = line["code"]
        if code not in CHART and not Account.objects.filter(code=code).exists():
            raise ValueError("Compte inconnu.")
        account, _ = Account.objects.get_or_create(code=code, defaults={"name": CHART.get(code, code)})
        if not account.active:
            raise ValueError("Un compte utilisé est inactif.")
        supplier = line.get('supplier')
        if supplier and (not code.startswith('40') or line.get('owner')):
            raise ValueError('Un fournisseur doit être rattaché à un compte fournisseur sans copropriétaire sur la même ligne.')
        project = line.get('project')
        if project and project.completed_on and kind not in ('carry','closing','project-complete'):
            raise ValueError('Cette opération de travaux est terminée.')
        normalized.append((account, line.get("owner"), debit, credit, supplier, line))
    if sum(row[2] for row in normalized) != sum(row[3] for row in normalized):
        raise ValueError("L’écriture n’est pas équilibrée : débit et crédit doivent être égaux.")
    entry = Entry.objects.create(year=year, number=year.next_entry, date=date, journal=journal,
                                 label=label, reference=reference, created_by=user, cost_center=cost_center, reversal_of=reversal_of,kind=kind)
    year.next_entry += 1; year.save(update_fields=["next_entry"])
    created = Line.objects.bulk_create([Line(entry=entry, account=a, owner=o, debit=d, credit=c, supplier=s,
        key=row.get('key'),project=row.get('project'),lot=row.get('lot'),due_date=(row.get('due_date') or date) if o or s else None) for a,o,d,c,s,row in normalized])
    from .cycle import allocate_charge
    for line in created:
        if line.key_id and line.account.code.startswith('6') and kind == 'normal':
            allocate_charge(line, strict=False)
    AuditEvent.objects.create(actor=user,action="entry.post",target=f"entry:{entry.pk}")
    return entry


def distribute(total, weighted_lots, require_owner=True):
    """Deterministic largest-remainder allocation; totals remain exact cents."""
    total = amount(total)
    weights = [(lot, Decimal(weight)) for lot,weight in weighted_lots if Decimal(weight) > 0]
    if not weights:
        raise ValueError("Aucun tantième positif pour cette clé de répartition.")
    if require_owner and any(lot.owner_id is None for lot,_ in weights):
        raise ValueError("Attribuez un copropriétaire à chaque lot concerné.")
    total_weight = sum(weight for _,weight in weights)
    cents = int(total * 100)
    rows = []
    for lot, weight in weights:
        exact = Decimal(cents) * weight / total_weight
        floor = int(exact.to_integral_value(rounding=ROUND_DOWN))
        rows.append([lot, weight, floor, exact - floor])
    residual = cents - sum(row[2] for row in rows)
    for row in sorted(rows, key=lambda row: (-row[3], row[0].pk))[:residual]:
        row[2] += 1
    return [(lot, weight, Decimal(cents) / 100) for lot,weight,cents,_ in rows]


def key_weights(key, effective_date=None):
    if key.general:
        rows=[(lot,lot.shares) for lot in Lot.objects.select_for_update(of=("self",)).select_related("owner").order_by("id")]
    else:rows=[(share.lot,share.value) for share in key.shares.select_related("lot__owner").order_by("lot_id")]
    if effective_date:
        from .cycle import owner_at
        for lot,weight in rows:lot.owner=owner_at(lot,effective_date)
    return rows


def publish_call(call, user):
    if call.entry_id:
        raise ValueError("Cet appel de fonds est déjà validé.")
    year = open_year(call.year_id, call.date)
    from .funding import validate_call, ADVANCE_CODES
    validate_call(call)
    from .models import ChargeKey
    call.key = ChargeKey.objects.select_for_update().get(pk=call.key_id)
    rows = distribute(call.amount, key_weights(call.key,call.due_date))
    owner_amounts = {}
    for lot,weight,value in rows:
        owner_amounts[lot.owner] = owner_amounts.get(lot.owner, Decimal(0)) + value
    lines = [{"code":"450", "owner":owner, "debit":value,'key':call.key,'project':call.project,'due_date':call.due_date} for owner,value in owner_amounts.items() if value > 0]
    if call.kind == 'works' and (not call.project or not call.decision):
        raise ValueError('Une opération de travaux et sa décision de financement sont nécessaires.')
    code = ADVANCE_CODES[call.advance_type] if call.kind == 'advance' else {'current':'701','works':'102','fund':'105'}[call.kind]
    if call.kind in ('fund','advance'):
        lines.extend({'code':code,'credit':value,'lot':lot,'key':call.key,'owner':lot.owner if call.kind=='advance' else None} for lot,weight,value in rows if value>0)
    else:
        lines.append({'code':code,'credit':call.amount,'key':call.key,'project':call.project})
    call.entry = post_entry(year,call.date,"AP",call.label,lines,user,cost_center=call.cost_center)
    call.save(update_fields=["entry"])
    Allocation.objects.bulk_create([Allocation(call=call,owner=lot.owner,lot=lot,shares=weight,amount=value) for lot,weight,value in rows])


def balance(year):
    rows = Line.objects.filter(entry__year=year).values("account__code", "account__name").annotate(debit=Sum("debit"),credit=Sum("credit")).order_by("account__code")
    return [{"code":row["account__code"],"name":row["account__name"],"debit":str(row["debit"]),"credit":str(row["credit"]),"balance":str(row["debit"]-row["credit"])} for row in rows]


def bank_for_posting(pk=None):
    if pk not in (None, ''):
        if isinstance(pk, bool): raise ValueError('Compte bancaire invalide.')
        bank = BankAccount.objects.select_for_update(of=('self',)).select_related('account').get(pk=pk)
    else:
        bank = BankAccount.objects.select_for_update(of=('self',)).select_related('account').filter(is_default=True).first()
    if bank and (not bank.active or not bank.account.active or not bank.account.code.startswith('512')):
        raise ValueError('Choisissez un compte bancaire actif associé à un compte comptable 512.')
    if not bank and BankAccount.objects.exists():
        raise ValueError('Choisissez un compte bancaire ou définissez un compte par défaut.')
    return bank


def pay_expense(expense, day, value, user, bank_pk=None, year_pk=None):
    """Caller locks expense in an atomic transaction; legacy payments are migrated."""
    from council.services import ensure_approved
    ensure_approved("expense", expense)
    paid = expense.payments.filter(entry__reversal__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0")
    if Entry.objects.filter(reversal_of_id=expense.entry_id).exists():raise ValueError('Cette facture a été annulée.')
    remaining = expense.amount - paid
    if expense.payment_entry_id or remaining <= 0:
        raise ValueError("Cette facture est déjà réglée.")
    value = amount(remaining if value in (None, "") else value)
    if value > remaining:
        raise ValueError(f"Le règlement dépasse le reste à payer ({remaining:.2f} €).")
    if day < expense.date:
        raise ValueError("Le règlement ne peut pas précéder la date de la facture.")
    year = open_year(year_pk or expense.year_id, day)
    if year.starts_on < expense.year.starts_on:
        raise ValueError('Le règlement ne peut pas utiliser un exercice antérieur à la facture.')
    bank = bank_for_posting(bank_pk)
    entry = post_entry(year, day, "BQ", "Règlement fournisseur : " + expense.supplier,
        [{"code":"401","debit":value,'supplier':expense.supplier_record},{"code":bank.account.code if bank else "512","credit":value}], user,
        expense.reference, cost_center=expense.entry.cost_center)
    ExpensePayment.objects.create(expense=expense, amount=value, entry=entry, bank=bank)
    from .cycle import match_lines
    debit = entry.lines.get(account__code='401')
    credit = expense.entry.lines.get(account__code='401')
    match_lines(debit, credit, value, user, allow_unidentified=True)
    if value == remaining:
        expense.payment_entry = entry
        expense.save(update_fields=["payment_entry"])
    return entry


def record_expense(data, user):
    from .forms import ExpenseForm
    from .models import CostCenter
    form = ExpenseForm(data)
    if not form.is_valid():
        raise ValueError(" · ".join(" ".join(v) for v in form.errors.values()))
    item = form.instance
    year = open_year(item.year_id, item.date)
    center = CostCenter.objects.get(pk=data["cost_center"]) if data.get("cost_center") else None
    code = str(data.get("charge_code") or ("671" if item.project_id else "601"))
    if not code.startswith("6") or code.startswith("67") != bool(item.project_id):
        raise ValueError("Choisissez un compte courant 6 ou de travaux 67 avec son opération.")
    item.entry = post_entry(year, item.date, "AC", item.label, [
        {"code": code, "debit": item.amount, "key": item.key, "project": item.project},
        {"code": "401", "credit": item.amount, "supplier": item.supplier_record, "due_date": item.due_date or item.date},
    ], user, item.reference, cost_center=center)
    item.save()
    return item


def public_summary(year):
    rows = balance(year)
    by_code = {row["code"]:row for row in rows}
    income=Line.objects.filter(entry__year=year).exclude(entry__kind='closing').values('account__code').annotate(d=Sum('debit'),c=Sum('credit'))
    return {"year": year.name, "starts_on": str(year.starts_on), "ends_on": str(year.ends_on),
            "treasury_movement": str(sum((Decimal(row['balance']) for row in rows if row['code'].startswith('512')), Decimal(0))),
            "charges": str(sum((row['d']-row['c'] for row in income if row['account__code'].startswith('6')),Decimal(0))),
            "provisions": str(sum((row['c']-row['d'] for row in income if row['account__code'].startswith('7')),Decimal(0))),
            "total_debit":str(sum(Decimal(row["debit"]) for row in rows)),
            "total_credit":str(sum(Decimal(row["credit"]) for row in rows))}
