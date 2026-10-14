"""Accounting cycle. All mutating callers run inside an atomic transaction."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from django.db.models import Sum, Q
from core.models import Owner, Lot
from .models import (
    Account,
    Entry,
    Line,
    FiscalYear,
    FundCall,
    Allocation,
    Expense,
    ChargeKey,
    ChargeAllocation,
    Settlement,
    AnnualSettlement,
    YearClosure,
    FinanceProject,
    ExpensePayment,
    BankAccount,
    BankStatement,
    BankMatch,
    Budget,
    AuditEvent,
    OwnershipChange,
    AllocationTransfer,
    RegularizationTransfer,
)
from .services import (
    amount,
    open_year,
    post_entry,
    distribute,
    key_weights,
    financial_today,
)

ZERO = Decimal("0")


def digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str, ensure_ascii=False).encode()
    ).hexdigest()


def signed(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError("Montant invalide.")
    amount(abs(result), False)
    return result


def audit(user, action, target):
    AuditEvent.objects.create(actor=user, action=action, target=str(target))


def allocate_charge(line, strict=True):
    if line.charge_allocations.exists():
        return
    if not line.key_id:
        if strict:
            raise ValueError("Choisissez une clé de répartition.")
        return
    if line.entry.reversal_of_id:
        original = Line.objects.filter(
            entry_id=line.entry.reversal_of_id,
            account=line.account,
            key_id=line.key_id,
            debit=line.credit,
            credit=line.debit,
        ).first()
        if original and original.charge_allocations.exists():
            ChargeAllocation.objects.bulk_create(
                [
                    ChargeAllocation(
                        line=line,
                        owner=r.owner,
                        lot=r.lot,
                        key=r.key,
                        amount=-r.amount,
                        shares=r.shares,
                    )
                    for r in original.charge_allocations.all()
                ]
            )
        return
    weights = key_weights(line.key)
    if (
        not weights
        or not any(w > 0 for lot, w in weights)
        or any(lot.owner_id is None and w > 0 for lot, w in weights)
    ):
        if strict:
            raise ValueError(
                "Attribuez les lots et renseignez les tantièmes de cette clé."
            )
        return
    value = line.debit - line.credit
    rows = distribute(abs(value), weights)
    ChargeAllocation.objects.bulk_create(
        [
            ChargeAllocation(
                line=line,
                owner=lot.owner,
                lot=lot,
                key=line.key,
                amount=v if value > 0 else -v,
                shares=weight,
            )
            for lot, weight, v in rows
        ]
    )


def line_remaining(line, day=None):
    matches = Settlement.objects.filter(active=True).filter(
        Q(debit_line=line) | Q(credit_line=line)
    )
    if day:
        matches = matches.filter(
            debit_line__entry__date__lte=day, credit_line__entry__date__lte=day
        )
    return (
        line.debit
        + line.credit
        - (matches.aggregate(total=Sum("amount"))["total"] or ZERO)
    )


def match_lines(debit, credit, value, user, allow_unidentified=False):
    locked = {
        l.pk: l
        for l in Line.objects.select_for_update()
        .select_related("entry", "account")
        .filter(pk__in=[debit.pk, credit.pk])
        .order_by("pk")
    }
    debit, credit = locked[debit.pk], locked[credit.pk]
    value = amount(value)
    if not debit.debit or not credit.credit or debit.account_id != credit.account_id:
        raise ValueError("Choisissez un débit et un crédit du même compte.")
    if not debit.account.code.startswith(("450", "40")) or (
        debit.owner_id,
        debit.supplier_id,
    ) != (credit.owner_id, credit.supplier_id):
        raise ValueError(
            "Le lettrage doit concerner le même copropriétaire ou fournisseur."
        )
    if not debit.owner_id and not debit.supplier_id and not allow_unidentified:
        raise ValueError("Identifiez le tiers avant de rapprocher ces lignes.")
    if any(
        l.entry.kind == "carry"
        or l.entry.reversal_of_id
        or Entry.objects.filter(reversal_of=l.entry).exists()
        for l in [debit, credit]
    ):
        raise ValueError(
            "Lettrez les opérations sources, pas leurs reports ou contrepassations."
        )
    if value > min(line_remaining(debit), line_remaining(credit)):
        raise ValueError("Le montant dépasse le reste non lettré.")
    item = Settlement.objects.create(
        debit_line=debit, credit_line=credit, amount=value, created_by=user
    )
    audit(user, "settlement.create", item.pk)
    return item


def outstanding(day):
    query = (
        Line.objects.filter(
            account__code__startswith="450",
            entry__date__lte=day,
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        )
        .exclude(entry__kind="carry")
        .select_related("owner", "entry", "account")
    )
    rows = []
    for line in query.order_by("due_date", "entry__date", "pk"):
        rest = line_remaining(line, day)
        if rest <= 0:
            continue
        due = line.due_date or line.entry.date
        age = max(0, (day - due).days)
        rows.append(
            {
                "id": line.pk,
                "owner": line.owner_id,
                "name": str(line.owner) if line.owner else "Non attribué",
                "date": str(line.entry.date),
                "due_date": str(due),
                "label": line.entry.label,
                "debit": str(line.debit),
                "credit": str(line.credit),
                "remaining": str(rest),
                "age": age,
                "bucket": (
                    "À échoir"
                    if due > day
                    else (
                        "0–30 jours"
                        if age <= 30
                        else (
                            "31–60 jours"
                            if age <= 60
                            else "61–90 jours" if age <= 90 else "Plus de 90 jours"
                        )
                    )
                ),
            }
        )
    return rows


def owner_at(lot, day):
    before = (
        OwnershipChange.objects.filter(lot=lot, active=True, effective_date__lte=day)
        .select_related("new_owner")
        .order_by("-effective_date", "-id")
        .first()
    )
    if before:
        return before.new_owner
    after = (
        OwnershipChange.objects.filter(lot=lot, active=True, effective_date__gt=day)
        .select_related("old_owner")
        .order_by("effective_date", "id")
        .first()
    )
    return after.old_owner if after else lot.owner


def record_mutation(data, user):
    lot = Lot.objects.select_for_update().get(pk=data["lot"])
    new = Owner.objects.get(pk=data["new_owner"])
    day = date.fromisoformat(data["effective_date"])
    reference = str(data.get("reference", "")).strip()
    existing = OwnershipChange.objects.filter(
        lot=lot, active=True, effective_date=day
    ).first()
    if existing:
        if existing.new_owner_id == new.pk and existing.reference == reference:
            return existing
        raise ValueError("Une mutation est déjà enregistrée ce jour pour ce lot.")
    if (
        not lot.owner_id
        or lot.owner_id == new.pk
        or day > financial_today()
        or not reference
        or len(reference) > 250
    ):
        raise ValueError(
            "Ancien propriétaire, acquéreur distinct, date effective passée et référence de notification sont nécessaires."
        )
    if lot.ownership_changes.filter(active=True, effective_date__gte=day).exists():
        raise ValueError(
            "Les mutations doivent être enregistrées dans l’ordre chronologique."
        )
    old = lot.owner
    mutation = OwnershipChange.objects.create(
        lot=lot,
        old_owner=old,
        new_owner=new,
        effective_date=day,
        reference=reference,
        created_by=user,
    )
    lot.owner = new
    lot.save(update_fields=["owner"])
    allocations = Allocation.objects.filter(
        lot=lot,
        call__due_date__gte=day,
        call__entry__isnull=False,
        call__entry__reversal__isnull=True,
    ).select_related("call__year", "owner")
    for allocation in allocations:
        previous = (
            allocation.transfers.filter(mutation__active=True)
            .select_related("mutation", "entry")
            .order_by("-mutation__effective_date", "-id")
            .first()
        )
        liable = previous.mutation.new_owner if previous else allocation.owner
        value = allocation.amount
        if allocation.call.kind == "fund":
            value = max(
                ZERO,
                value
                - fund_paid_allocations(allocation.call, day).get(allocation.pk, ZERO),
            )
        if liable.pk == new.pk or not value:
            continue
        posting_date = max(day, allocation.call.date)
        year = FiscalYear.objects.filter(
            starts_on__lte=posting_date, ends_on__gte=posting_date, closed=False
        ).first()
        if not year:
            posting_date = financial_today()
            year = FiscalYear.objects.filter(
                starts_on__lte=posting_date, ends_on__gte=posting_date, closed=False
            ).first()
        if not year:
            raise ValueError(
                "Créez un exercice ouvert pour les corrections de mutation."
            )
        entry = post_entry(
            year,
            posting_date,
            "OD",
            "Mutation : réattribution d’un appel exigible",
            [
                {
                    "code": "450",
                    "owner": liable,
                    "credit": value,
                    "lot": lot,
                    "due_date": allocation.call.due_date,
                },
                {
                    "code": "450",
                    "owner": new,
                    "debit": value,
                    "lot": lot,
                    "due_date": allocation.call.due_date,
                },
            ],
            user,
            reference[:100],
            kind="ownership",
        )
        AllocationTransfer.objects.create(
            allocation=allocation, mutation=mutation, entry=entry
        )
        mutation.adjustments.add(entry)
        source = (previous.entry if previous else allocation.call.entry).lines.get(
            owner=liable, debit__gt=0
        )
        transferable = min(value, line_remaining(source))
        if transferable:
            match_lines(
                source, entry.lines.get(owner=liable, credit__gt=0), transferable, user
            )
    for settlement in AnnualSettlement.objects.filter(
        active=True, approved_on__gte=day
    ):
        for row in settlement.data["rows"]:
            if row["lot"] != lot.pk or not Decimal(row["adjustment"]):
                continue
            previous = (
                RegularizationTransfer.objects.filter(
                    settlement=settlement, lot=lot, key_id=row["key"], active=True
                )
                .select_related("mutation", "entry", "owner")
                .order_by("-id")
                .first()
            )
            liable = (
                (previous.owner or previous.mutation.new_owner)
                if previous
                else Owner.objects.get(pk=row["owner"])
            )
            if liable.pk == new.pk:
                continue
            posting_date = financial_today()
            year = FiscalYear.objects.filter(
                starts_on__lte=posting_date, ends_on__gte=posting_date, closed=False
            ).first()
            if not year:
                raise ValueError(
                    "Créez un exercice ouvert pour la réattribution de la régularisation."
                )
            value = Decimal(row["adjustment"])
            key = ChargeKey.objects.get(pk=row["key"])
            entry = post_entry(
                year,
                posting_date,
                "OD",
                "Mutation : correction de régularisation approuvée",
                [
                    {
                        "code": "450",
                        "owner": liable,
                        "lot": lot,
                        "key": key,
                        "credit": max(value, ZERO),
                        "debit": max(-value, ZERO),
                    },
                    {
                        "code": "450",
                        "owner": new,
                        "lot": lot,
                        "key": key,
                        "debit": max(value, ZERO),
                        "credit": max(-value, ZERO),
                        "due_date": settlement.approved_on,
                    },
                ],
                user,
                reference[:100],
                kind="ownership",
            )
            RegularizationTransfer.objects.create(
                settlement=settlement,
                lot=lot,
                key=key,
                mutation=mutation,
                entry=entry,
                owner=new,
            )
            mutation.adjustments.add(entry)
            source = (
                (previous.entry if previous else settlement.entry)
                .lines.filter(owner=liable, lot=lot, key=key)
                .first()
            )
            opposite = entry.lines.get(owner=liable)
            if source and min(line_remaining(source), abs(value)) > 0:
                if source.debit:
                    match_lines(
                        source, opposite, min(line_remaining(source), abs(value)), user
                    )
                else:
                    match_lines(
                        opposite, source, min(line_remaining(source), abs(value)), user
                    )
    audit(user, "lot.mutation", mutation.pk)
    return mutation


def cancel_mutation(mutation, user):
    from django.utils import timezone

    if (
        not mutation.active
        or OwnershipChange.objects.filter(
            lot=mutation.lot, active=True, effective_date__gt=mutation.effective_date
        ).exists()
    ):
        raise ValueError(
            "Seule la dernière mutation active d’un lot peut être corrigée."
        )
    if Allocation.objects.filter(
        lot=mutation.lot,
        owner=mutation.new_owner,
        call__entry__created_at__gte=mutation.created_at,
        call__entry__reversal__isnull=True,
    ).exists():
        raise ValueError(
            "Corrigez d’abord les nouveaux appels publiés depuis cette mutation."
        )
    year = FiscalYear.objects.filter(
        starts_on__lte=financial_today(), ends_on__gte=financial_today(), closed=False
    ).first()
    if mutation.adjustments.exists() and not year:
        raise ValueError(
            "Créez un exercice ouvert pour conserver les écritures inverses de cette correction."
        )
    for original in mutation.adjustments.all().prefetch_related(
        "lines__account", "lines__owner", "lines__supplier", "lines__key", "lines__lot"
    ):
        if Entry.objects.filter(reversal_of=original).exists():
            raise ValueError("Une correction existe déjà pour cette mutation.")
        Settlement.objects.filter(active=True, credit_line__entry=original).update(
            active=False
        )
        rows = [
            {
                "code": l.account.code,
                "owner": l.owner,
                "supplier": l.supplier,
                "key": l.key,
                "lot": l.lot,
                "debit": l.credit,
                "credit": l.debit,
                "due_date": l.due_date,
            }
            for l in original.lines.all()
        ]
        post_entry(
            year,
            financial_today(),
            "OD",
            "Correction de mutation",
            rows,
            user,
            reversal_of=original,
            kind="ownership",
        )
    mutation.active = False
    mutation.cancelled_by = user
    mutation.cancelled_at = timezone.now()
    mutation.save(update_fields=["active", "cancelled_by", "cancelled_at"])
    RegularizationTransfer.objects.filter(mutation=mutation).update(active=False)
    mutation.lot.owner = mutation.old_owner
    mutation.lot.save(update_fields=["owner"])
    # Correct a regularization approved after this mistaken ownership change,
    # without altering the approved source or any closed fiscal-year entries.
    for settlement in AnnualSettlement.objects.filter(
        active=True, approved_on__gte=mutation.effective_date
    ):
        for row in settlement.data["rows"]:
            if row["lot"] != mutation.lot_id or not Decimal(row["adjustment"]):
                continue
            previous = (
                RegularizationTransfer.objects.filter(
                    settlement=settlement,
                    lot=mutation.lot,
                    key_id=row["key"],
                    active=True,
                )
                .select_related("owner", "mutation")
                .order_by("-id")
                .first()
            )
            liable = (
                (previous.owner or previous.mutation.new_owner)
                if previous
                else Owner.objects.get(pk=row["owner"])
            )
            actual = owner_at(mutation.lot, settlement.approved_on)
            if not actual or actual.pk == liable.pk:
                continue
            if not year:
                raise ValueError(
                    "Un exercice ouvert est nécessaire pour corriger la régularisation conservée."
                )
            value = Decimal(row["adjustment"])
            entry = post_entry(
                year,
                financial_today(),
                "OD",
                "Mutation annulée : correction de régularisation",
                [
                    {
                        "code": "450",
                        "owner": liable,
                        "lot": mutation.lot,
                        "credit": max(value, ZERO),
                        "debit": max(-value, ZERO),
                    },
                    {
                        "code": "450",
                        "owner": actual,
                        "lot": mutation.lot,
                        "debit": max(value, ZERO),
                        "credit": max(-value, ZERO),
                    },
                ],
                user,
                kind="ownership",
            )
            RegularizationTransfer.objects.create(
                settlement=settlement,
                lot=mutation.lot,
                key_id=row["key"],
                mutation=mutation,
                entry=entry,
                owner=actual,
            )
    audit(user, "lot.mutation.cancel", mutation.pk)
    return mutation


def regularization_data(year, approved_on=None):
    costs = (
        Line.objects.filter(
            entry__year=year,
            account__code__startswith="6",
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        )
        .exclude(account__code__startswith="67")
        .exclude(entry__kind__in=["closing", "regularization"])
    )
    errors = []
    totals = defaultdict(lambda: ZERO)
    details = defaultdict(lambda: {"actual": ZERO, "provisions": ZERO})
    fingerprint = []
    for line in costs.select_related("account", "entry"):
        allocations = list(line.charge_allocations.all())
        if sum((r.amount for r in allocations), ZERO) != line.debit - line.credit:
            errors.append(
                f"Écriture {line.entry.number}, compte {line.account.code} : répartition des charges à vérifier."
            )
        for row in allocations:
            details[(row.key_id, row.lot_id, row.owner_id)]["actual"] += row.amount
        fingerprint.append(
            (
                line.pk,
                str(line.debit),
                str(line.credit),
                [(r.lot_id, r.owner_id, str(r.amount)) for r in allocations],
            )
        )
    calls = FundCall.objects.filter(
        year=year, kind="current", entry__isnull=False, entry__reversal__isnull=True
    ).prefetch_related("allocations")
    for call in calls:
        for row in call.allocations.all():
            details[(call.key_id, row.lot_id, row.owner_id)]["provisions"] += row.amount
        fingerprint.append(
            (
                "call",
                call.pk,
                str(call.amount),
                [(r.lot_id, r.owner_id, str(r.amount)) for r in call.allocations.all()],
            )
        )
    ledger_provisions = (
        Line.objects.filter(entry__year=year, account__code="701")
        .exclude(entry__kind__in=["closing", "regularization"])
        .aggregate(d=Sum("debit"), c=Sum("credit"))
    )
    total_provisions = (ledger_provisions["c"] or ZERO) - (
        ledger_provisions["d"] or ZERO
    )
    if total_provisions != sum((v["provisions"] for v in details.values()), ZERO):
        errors.append(
            "Le compte 701 contient des provisions sans appel identifié. Reprenez/corrigez ces écritures avant la régularisation."
        )
    other = (
        Line.objects.filter(
            entry__year=year,
            account__code__startswith="7",
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        )
        .exclude(account__code__in=["701", "702"])
        .exclude(entry__kind="closing")
    )
    for line in other.select_related("account", "entry"):
        # Other income must be explicitly allocated to the benefiting charge key.
        allocations = list(line.charge_allocations.all())
        if sum((r.amount for r in allocations), ZERO) != line.debit - line.credit:
            errors.append(
                f"Produit {line.account.code}, écriture {line.entry.number} : ventilez le produit par clé."
            )
        for row in allocations:
            details[(row.key_id, row.lot_id, row.owner_id)]["actual"] += row.amount
        fingerprint.append(
            (
                line.pk,
                str(line.debit),
                str(line.credit),
                [(r.lot_id, r.owner_id, str(r.amount)) for r in allocations],
            )
        )
    day = approved_on or financial_today()
    by_lot = defaultdict(lambda: {"actual": ZERO, "provisions": ZERO})
    for (key, lot, owner), values in details.items():
        by_lot[(key, lot)]["actual"] += values["actual"]
        by_lot[(key, lot)]["provisions"] += values["provisions"]
    owners = {o.pk: str(o) for o in Owner.objects.all()}
    lots = {l.pk: l for l in Lot.objects.all()}
    keys = {k.pk: k.name for k in ChargeKey.objects.all()}
    rows = []
    for (key, lot), values in sorted(by_lot.items()):
        liable = owner_at(lots[lot], day)
        if not liable:
            errors.append(
                f"Lot {lots[lot].number} : propriétaire manquant à la date d’approbation."
            )
            continue
        owner = liable.pk
        fingerprint.append(("liable", lot, owner))
        delta = values["actual"] - values["provisions"]
        rows.append(
            {
                "key": key,
                "key_name": keys[key],
                "lot": lot,
                "lot_number": lots[lot].number,
                "owner": owner,
                "name": owners[owner],
                "actual": str(values["actual"]),
                "provisions": str(values["provisions"]),
                "adjustment": str(delta),
            }
        )
    return {
        "rows": rows,
        "errors": errors,
        "source_hash": digest(fingerprint),
        "total": str(sum((Decimal(r["adjustment"]) for r in rows), ZERO)),
    }


def apply_regularization(year, data, user):
    if AnnualSettlement.objects.filter(year=year, active=True).exists():
        raise ValueError("Une régularisation est déjà enregistrée.")
    approved = date.fromisoformat(data["approved_on"])
    preview = regularization_data(year, approved)
    if preview["errors"]:
        raise ValueError(" · ".join(preview["errors"]))
    if data.get("source_hash") != preview["source_hash"]:
        raise ValueError("Les données ont changé : rechargez l’aperçu.")
    decision = str(data.get("decision", "")).strip()
    if (
        not decision
        or len(decision) > 250
        or approved < year.ends_on
        or approved > financial_today()
    ):
        raise ValueError(
            "Indiquez une décision d’approbation déjà intervenue, entre la fin d’exercice et aujourd’hui."
        )
    lines = []
    counter = defaultdict(lambda: ZERO)
    for row in preview["rows"]:
        value = Decimal(row["adjustment"])
        if not value:
            continue
        key = ChargeKey.objects.get(pk=row["key"])
        owner = Owner.objects.get(pk=row["owner"])
        lines.append(
            {
                "code": "450",
                "owner": owner,
                "key": key,
                "lot": Lot.objects.get(pk=row["lot"]),
                "due_date": approved,
                "debit": max(value, ZERO),
                "credit": max(-value, ZERO),
            }
        )
        counter[key] += value
    for key, value in counter.items():
        if value:
            lines.append(
                {
                    "code": "701",
                    "key": key,
                    "debit": max(-value, ZERO),
                    "credit": max(value, ZERO),
                }
            )
    # Balanced owner-to-owner adjustments may have no 701 counterpart.
    entry = (
        post_entry(
            year,
            year.ends_on,
            "OD",
            "Régularisation annuelle des charges",
            lines,
            user,
            decision,
            kind="regularization",
        )
        if lines
        else None
    )
    item = AnnualSettlement.objects.create(
        year=year,
        data=preview,
        source_hash=preview["source_hash"],
        decision=decision,
        approved_on=approved,
        entry=entry,
    )
    audit(user, "regularization.apply", item.pk)
    return item


def opening_balance(year, data, user):
    if Entry.objects.filter(
        year=year,
        kind__in=["opening", "carry"],
        reversal_of__isnull=True,
        reversal__isnull=True,
    ).exists():
        raise ValueError("Une reprise ou un report existe déjà.")
    if Entry.objects.filter(year__ends_on__lt=year.starts_on).exists():
        raise ValueError(
            "Clôturez l’exercice précédent pour reporter ses soldes ; aucune double reprise."
        )
    raw = data.get("lines", [])
    if not isinstance(raw, list) or not 2 <= len(raw) <= 1000:
        raise ValueError("Entre 2 et 1 000 lignes de reprise sont attendues.")
    from operations.models import Supplier

    lines = []
    for row in raw:
        code = str(row["code"])
        if not code.startswith(tuple("12345")):
            raise ValueError("Les soldes initiaux portent sur les classes 1 à 5.")
        owner = Owner.objects.get(pk=row["owner"]) if row.get("owner") else None
        supplier = (
            Supplier.objects.get(pk=row["supplier"]) if row.get("supplier") else None
        )
        lot = Lot.objects.get(pk=row["lot"]) if row.get("lot") else None
        if code.startswith("450") and not owner:
            raise ValueError("Identifiez chaque copropriétaire de la reprise.")
        if code.startswith("105") and not lot:
            raise ValueError("Affectez le fonds travaux à un lot.")
        lines.append(
            dict(
                code=code,
                owner=owner,
                supplier=supplier,
                lot=lot,
                debit=row.get("debit", 0),
                credit=row.get("credit", 0),
                due_date=(
                    date.fromisoformat(row["due_date"])
                    if row.get("due_date")
                    else year.starts_on
                ),
            )
        )
    return post_entry(
        year,
        year.starts_on,
        "AN",
        "Reprise des soldes initiaux",
        lines,
        user,
        str(data.get("reference", ""))[:100],
        kind="opening",
    )


def fund_paid_allocations(call, day):
    allocations = list(call.allocations.select_related("lot"))
    paid = defaultdict(lambda: ZERO)
    for line in call.entry.lines.filter(owner__isnull=False, debit__gt=0):
        for match in (
            line.debit_matches.filter(active=True, credit_line__entry__date__lte=day)
            .exclude(credit_line__entry__kind="ownership")
            .select_related("credit_line__entry")
        ):
            eligible = [
                r
                for r in allocations
                if r.owner_id == line.owner_id
                and not r.transfers.filter(
                    mutation__active=True, entry__created_at__lt=match.created_at
                ).exists()
            ]
            if not eligible:
                continue
            portions = distribute(
                match.amount, [(r.lot, r.amount) for r in eligible], require_owner=False
            )
            amounts = {lot.pk: value for lot, w, value in portions}
            for r in eligible:
                paid[r.pk] += amounts.get(r.lot_id, ZERO)
    for allocation in allocations:
        for transfer in allocation.transfers.filter(
            mutation__active=True
        ).select_related("entry"):
            for line in transfer.entry.lines.filter(debit__gt=0, owner__isnull=False):
                result = (
                    line.debit_matches.filter(
                        active=True, credit_line__entry__date__lte=day
                    )
                    .exclude(credit_line__entry__kind="ownership")
                    .aggregate(total=Sum("amount"))
                )
                paid[allocation.pk] += result["total"] or ZERO
    return paid


def funds(day=None):
    day = day or financial_today()
    movements = Line.objects.filter(
        account__code="105",
        entry__date__lte=day,
        entry__reversal_of__isnull=True,
        entry__reversal__isnull=True,
    ).exclude(entry__kind="carry")
    called = defaultdict(lambda: ZERO)
    used = defaultdict(lambda: ZERO)
    paid = defaultdict(lambda: ZERO)
    for row in movements:
        called[row.lot_id] += row.credit
        used[row.lot_id] += row.debit
        if row.entry.kind == "opening":
            paid[row.lot_id] += row.credit - row.debit
    for call in FundCall.objects.filter(
        kind="fund", date__lte=day, entry__isnull=False, entry__reversal__isnull=True
    ).prefetch_related("allocations", "entry__lines"):
        contributions = fund_paid_allocations(call, day)
        for allocation in call.allocations.all():
            paid[allocation.lot_id] += contributions[allocation.pk]
    return [
        {
            "lot": lot.pk,
            "lot_number": lot.number,
            "called": str(called[lot.pk]),
            "paid": str(paid[lot.pk]),
            "used": str(used[lot.pk]),
            "available": str(paid[lot.pk] - used[lot.pk]),
            "account_balance": str(called[lot.pk] - used[lot.pk]),
        }
        for lot in Lot.objects.all()
    ]


def use_fund(project, year, data, user):
    decision = str(data.get("decision", "")).strip()
    if not decision or len(decision) > 250:
        raise ValueError("Renseignez la décision d’affectation du fonds.")
    rows = distribute(amount(data["amount"]), key_weights(project.key))
    from .reconciliation import bank_balance

    dedicated = list(
        BankAccount.objects.filter(kind="works", active=True).select_related("account")
    )
    if not dedicated or sum(
        (bank_balance(b, date.fromisoformat(data["date"])) for b in dedicated), ZERO
    ) < sum(v for lot, w, v in rows):
        raise ValueError(
            "Configurez le compte dédié au fonds travaux et vérifiez que son solde comptable couvre cette affectation."
        )
    balances = {
        row["lot"]: Decimal(row["available"])
        for row in funds(date.fromisoformat(data["date"]))
    }
    if any(value > balances.get(lot.pk, ZERO) for lot, weight, value in rows):
        raise ValueError(
            "Fonds versés insuffisants sur au moins un lot selon la clé des travaux."
        )
    lines = [
        {
            "code": "105",
            "lot": lot,
            "owner": lot.owner,
            "debit": value,
            "project": project,
            "key": project.key,
        }
        for lot, weight, value in rows
        if value
    ]
    lines.append(
        {
            "code": "102",
            "credit": sum(v for lot, w, v in rows),
            "project": project,
            "key": project.key,
        }
    )
    from .models import CostCenter

    centre = (
        CostCenter.objects.get(pk=data["cost_center"])
        if data.get("cost_center")
        else None
    )
    return post_entry(
        year,
        date.fromisoformat(data["date"]),
        "OD",
        "Affectation du fonds : " + project.name,
        lines,
        user,
        decision[:100],
        cost_center=centre,
    )


def finish_project(project, year, data, user):
    if project.completed_on:
        raise ValueError("Opération déjà terminée.")
    day = date.fromisoformat(data["date"])
    if not str(data.get("decision", "")).strip():
        raise ValueError("Indiquez la décision d’approbation des travaux.")
    source = (
        Line.objects.filter(
            project=project,
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        )
        .exclude(entry__kind__in=["carry", "closing"])
        .select_related("account")
    )
    held = sum((l.credit - l.debit for l in source if l.account.code == "102"), ZERO)
    carried = Line.objects.filter(
        entry__year=year, project=project, account__code="120"
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    prior_cost = (carried["d"] or ZERO) - (carried["c"] or ZERO)
    charges = defaultdict(lambda: ZERO)
    provisions = defaultdict(lambda: ZERO)
    for allocation in ChargeAllocation.objects.filter(line__project=project).exclude(
        line__entry__kind__in=["closing", "carry"]
    ):
        charges[(allocation.lot_id, allocation.owner_id)] += allocation.amount
    for call in FundCall.objects.filter(
        project=project, entry__isnull=False, entry__reversal__isnull=True
    ):
        for allocation in call.allocations.all():
            provisions[(allocation.lot_id, allocation.owner_id)] += allocation.amount
    for l in source:
        if l.account.code == "105" and l.debit:
            owner = l.owner_id
            if not owner:
                raise ValueError(
                    "Attribuez le lot concerné par l’affectation du fonds."
                )
            provisions[(l.lot_id, owner)] += l.debit
    # Like annual charges, the final adjustment belongs to the owner at the
    # approval date; historical payment debts remain with their original owner.
    by_lot_charges = defaultdict(lambda: ZERO)
    by_lot_provisions = defaultdict(lambda: ZERO)
    for (lot, owner), value in charges.items():
        by_lot_charges[lot] += value
    for (lot, owner), value in provisions.items():
        by_lot_provisions[lot] += value
    charges = {}
    provisions = {}
    for lot_id in set(by_lot_charges) | set(by_lot_provisions):
        liable = owner_at(Lot.objects.get(pk=lot_id), day)
        if not liable:
            raise ValueError(
                "Identifiez le propriétaire des travaux à leur approbation."
            )
        charges[(lot_id, liable.pk)] = by_lot_charges[lot_id]
        provisions[(lot_id, liable.pk)] = by_lot_provisions[lot_id]
    total_cost = sum(charges.values(), ZERO)
    ledger_cost = sum(
        (l.debit - l.credit for l in source if l.account.code.startswith("67")), ZERO
    )
    if total_cost != ledger_cost:
        raise ValueError("Ventilez toutes les charges de travaux avant de terminer.")
    lines = []
    if prior_cost:
        lines.extend(
            [
                {
                    "code": "671",
                    "debit": max(prior_cost, ZERO),
                    "credit": max(-prior_cost, ZERO),
                    "project": project,
                },
                {
                    "code": "120",
                    "credit": max(prior_cost, ZERO),
                    "debit": max(-prior_cost, ZERO),
                    "project": project,
                },
            ]
        )
    if held:
        lines.extend(
            [
                {"code": "102", "debit": held, "project": project},
                {"code": "702", "credit": held, "project": project},
            ]
        )
    adjustment = ZERO
    for lot, owner in set(charges) | set(provisions):
        value = charges[(lot, owner)] - provisions[(lot, owner)]
        if value:
            lines.append(
                {
                    "code": "450",
                    "owner": Owner.objects.get(pk=owner),
                    "lot": Lot.objects.get(pk=lot),
                    "project": project,
                    "due_date": day,
                    "debit": max(value, ZERO),
                    "credit": max(-value, ZERO),
                }
            )
        adjustment += value
    if adjustment:
        lines.append(
            {
                "code": "702",
                "project": project,
                "credit": max(adjustment, ZERO),
                "debit": max(-adjustment, ZERO),
            }
        )
    if held < 0:
        raise ValueError("Le solde des provisions travaux est incohérent.")
    entry = (
        post_entry(
            year,
            day,
            "OD",
            "Solde des travaux : " + project.name,
            lines,
            user,
            str(data["decision"])[:100],
            kind="project-complete",
        )
        if lines
        else None
    )
    project.completed_on = day
    project.completion_entry = entry
    project.save()
    audit(user, "project.complete", project.pk)
    return entry


def annexes(year):
    query = Line.objects.filter(entry__year=year).exclude(entry__kind="closing")
    groups = (
        query.values(
            "account__code",
            "account__name",
            "owner_id",
            "owner__first_name",
            "owner__last_name",
            "supplier__name",
        )
        .annotate(d=Sum("debit"), c=Sum("credit"))
        .order_by("account__code", "owner_id")
    )
    state = []
    income = []
    for row in groups:
        code = row["account__code"]
        value = row["d"] - row["c"]
        target = income if code.startswith(("6", "7")) else state
        target.append(
            {
                "code": code,
                "label": row["account__name"],
                "third_party": row["supplier__name"]
                or " ".join(
                    [row["owner__first_name"] or "", row["owner__last_name"] or ""]
                ).strip(),
                "debit": str(row["d"]),
                "credit": str(row["c"]),
                "balance": str(value),
            }
        )
    saved_reg = AnnualSettlement.objects.filter(year=year, active=True).first()
    reg = saved_reg.data if saved_reg else regularization_data(year)
    consolidated = {}
    for row in state:
        identity = (
            row["code"],
            row["third_party"] if row["code"].startswith(("450", "40")) else "",
        )
        if identity not in consolidated:
            consolidated[identity] = {
                **row,
                "third_party": identity[1],
                "debit": "0",
                "credit": "0",
                "balance": "0",
            }
        target = consolidated[identity]
        target["debit"] = str(Decimal(target["debit"]) + Decimal(row["debit"]))
        target["credit"] = str(Decimal(target["credit"]) + Decimal(row["credit"]))
        target["balance"] = str(Decimal(target["debit"]) - Decimal(target["credit"]))
    state = list(consolidated.values())
    previous = (
        FiscalYear.objects.filter(ends_on__lt=year.starts_on)
        .order_by("-ends_on")
        .first()
    )
    following = list(
        FiscalYear.objects.filter(starts_on__gt=year.ends_on).order_by("starts_on")[:2]
    )

    def actual_by_key(selected_year):
        if not selected_year:
            return {}
        values = (
            Line.objects.filter(entry__year=selected_year)
            .exclude(entry__kind="closing")
            .filter(Q(account__code__startswith="6") | Q(account__code__startswith="7"))
            .exclude(account__code__startswith="67")
            .exclude(account__code__startswith="702")
            .values("account__code", "key_id")
            .annotate(d=Sum("debit"), c=Sum("credit"))
        )
        return {
            (r["account__code"], r["key_id"]): (r["d"] - r["c"])
            * (1 if r["account__code"].startswith("6") else -1)
            for r in values
        }

    def budget_by_key(selected_year):
        if not selected_year:
            return {}
        result = {}
        centres = defaultdict(lambda: ZERO)
        for b in Budget.objects.filter(year=selected_year).select_related("account"):
            identity = (b.account.code, b.key_id)
            if b.cost_center_id is None:
                result[identity] = b.amount
            else:
                centres[identity] += b.amount
        return {
            identity: result.get(identity, centres.get(identity))
            for identity in set(result) | set(centres)
        }

    now = actual_by_key(year)
    before = actual_by_key(previous)
    planned = budget_by_key(year)
    future = [
        budget_by_key(following[i]) if len(following) > i else {} for i in range(2)
    ]
    names = {a.code: a.name for a in Account.objects.all()}
    key_names = {k.pk: k.name for k in ChargeKey.objects.all()}
    current = []
    for identity in sorted(
        set(now) | set(before) | set(planned) | set(future[0]) | set(future[1]),
        key=lambda x: (x[1] or 0, x[0]),
    ):
        code, key = identity
        current.append(
            {
                "code": code,
                "label": names[code],
                "key_name": key_names.get(key, "Non ventilé par clé"),
                "actual_previous": (
                    str(before.get(identity, ZERO)) if previous else None
                ),
                "budget_current": (
                    str(planned[identity]) if identity in planned else None
                ),
                "actual_current": str(now.get(identity, ZERO)),
                "budget_next": (
                    str(future[0][identity]) if identity in future[0] else None
                ),
                "budget_following": (
                    str(future[1][identity]) if identity in future[1] else None
                ),
            }
        )
    completed = []
    pending = []
    for p in FinanceProject.objects.all():
        lines = Line.objects.filter(
            project=p,
            entry__date__lte=year.ends_on,
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        ).exclude(entry__kind__in=["carry", "closing"])
        cost = sum(
            (
                l.debit - l.credit
                for l in lines
                if l.account.code.startswith("67")
                and l.entry.kind != "project-complete"
            ),
            ZERO,
        )
        provision = sum(
            (
                l.credit - l.debit
                for l in lines
                if l.account.code == "102" and l.entry.kind != "project-complete"
            ),
            ZERO,
        )
        paid = sum(
            (
                pay.amount
                for pay in ExpensePayment.objects.filter(
                    expense__project=p,
                    entry__date__lte=year.ends_on,
                    entry__reversal__isnull=True,
                )
            ),
            ZERO,
        )
        received = ZERO
        for call in FundCall.objects.filter(
            project=p,
            date__lte=year.ends_on,
            entry__isnull=False,
            entry__reversal__isnull=True,
        ):
            for line in call.entry.lines.filter(owner__isnull=False):
                received += line.debit - line_remaining(line, year.ends_on)
        row = {
            "project": p.name,
            "decision": p.decision,
            "budget": str(p.budget),
            "expenses": str(cost),
            "funding": str(provision),
            "paid": str(paid),
            "received": str(received),
            "difference": str(provision - cost),
            "completed_on": str(p.completed_on or ""),
        }
        if p.completed_on and year.starts_on <= p.completed_on <= year.ends_on:
            completed.append(row)
        elif not p.completed_on or p.completed_on > year.ends_on:
            pending.append(row)
    journal = json.loads(
        json.dumps(
            list(
                query.order_by("entry__number", "id").values(
                    "id",
                    "entry__number",
                    "entry__date",
                    "entry__journal",
                    "entry__label",
                    "entry__reference",
                    "entry__kind",
                    "entry__created_at",
                    "entry__created_by_id",
                    "account__code",
                    "owner_id",
                    "supplier_id",
                    "key_id",
                    "lot_id",
                    "project_id",
                    "debit",
                    "credit",
                )
            ),
            default=str,
        )
    )
    bank_proofs = [
        {
            "bank": s.bank.name,
            "starts_on": str(s.starts_on),
            "ends_on": str(s.ends_on),
            "closing_balance": str(s.closing_balance),
            "transit": s.transit,
        }
        for s in BankStatement.objects.filter(
            validated=True, ends_on__lte=year.ends_on, ends_on__gte=year.starts_on
        ).select_related("bank")
    ]
    return {
        "year": year.name,
        "starts_on": str(year.starts_on),
        "ends_on": str(year.ends_on),
        "journal": journal,
        "reconciliations": bank_proofs,
        "annexes": [
            {
                "number": 1,
                "title": "État financier et comptes individuels",
                "rows": state,
            },
            {"number": 2, "title": "Compte de gestion général", "rows": income},
            {"number": 3, "title": "Opérations courantes et budget", "rows": current},
            {
                "number": 4,
                "title": "Travaux et opérations exceptionnelles terminés",
                "rows": completed,
            },
            {
                "number": 5,
                "title": "Travaux et opérations exceptionnelles non terminés",
                "rows": pending,
            },
        ],
        "individual_allocations": reg["rows"],
        "comparison_years": {
            "previous": previous.name if previous else None,
            "next": following[0].name if following else None,
            "following": following[1].name if len(following) > 1 else None,
        },
        "note": "États de préparation calculés depuis les données saisies. Budgets saisis, sans certification de vote ni de conformité des modèles réglementaires. Vérifiez les pièces et décisions avant approbation.",
    }


def close_checks(year):
    errors = []
    if year.closed:
        errors.append("Exercice déjà clôturé.")
    if year.ends_on > financial_today():
        errors.append(
            "L’exercice n’est pas encore terminé ; sa clôture reste à préparer."
        )
    if FiscalYear.objects.filter(ends_on__lt=year.starts_on, closed=False).exists():
        errors.append("Clôturez d’abord les exercices précédents.")
    if FundCall.objects.filter(year=year, entry__isnull=True).exists():
        errors.append("Des appels de fonds sont encore en brouillon.")
    if (
        regularization_data(year)["rows"]
        and not AnnualSettlement.objects.filter(year=year, active=True).exists()
    ):
        errors.append("Validez la régularisation annuelle après approbation.")
    errors += regularization_data(year)["errors"]
    if any(Decimal(r["available"]) < 0 for r in funds()):
        errors.append(
            "Une affectation du fonds dépasse les versements lettrés d’un lot."
        )
    if Line.objects.filter(
        entry__year=year,
        entry__reversal_of__isnull=True,
        entry__reversal__isnull=True,
        account__code__startswith="450",
        owner__isnull=True,
    ).exists():
        errors.append("Des comptes 450 sont sans copropriétaire.")
    if Line.objects.filter(
        entry__year=year,
        entry__reversal_of__isnull=True,
        entry__reversal__isnull=True,
        account__code="105",
        lot__isnull=True,
    ).exists():
        errors.append("Le fonds travaux comporte des lignes sans lot.")
    if Line.objects.filter(entry__year=year, account__code__startswith="47").exists():
        waiting = Line.objects.filter(
            entry__year=year, account__code__startswith="47"
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        if waiting["d"] != waiting["c"]:
            errors.append(
                "Soldez ou régularisez les comptes d’attente 47 avant clôture."
            )
    bank_lines = Line.objects.filter(
        entry__year=year,
        account__code__startswith="512",
        entry__reversal_of__isnull=True,
        entry__reversal__isnull=True,
    ).exclude(entry__kind__in=["opening", "carry"])
    approved_transit = {
        row["line_id"]
        for statement in BankStatement.objects.filter(
            validated=True, ends_on=year.ends_on
        )
        for row in statement.transit
    }
    unmatched = (
        bank_lines.filter(
            Q(bank_match__isnull=True)
            | Q(bank_match__statement_line__date__gt=year.ends_on)
        )
        .exclude(pk__in=approved_transit)
        .count()
    )
    if unmatched:
        errors.append(f"{unmatched} mouvement(s) bancaire(s) restent à rapprocher.")
    for account_id in (
        Line.objects.filter(entry__year=year, account__code__startswith="512")
        .values_list("account_id", flat=True)
        .distinct()
    ):
        bank = BankAccount.objects.filter(account_id=account_id).first()
        if not bank:
            errors.append("Associez chaque compte 512 utilisé à une fiche bancaire.")
        else:
            from .reconciliation import bank_balance, pending_at

            statement = BankStatement.objects.filter(
                bank=bank, validated=True, ends_on=year.ends_on
            ).first()
            if (
                not statement
                and not bank.active
                and bank_balance(bank, year.ends_on) == 0
                and not pending_at(bank, year.ends_on).exists()
            ):
                statement = (
                    BankStatement.objects.filter(
                        bank=bank,
                        validated=True,
                        closing_balance=0,
                        ends_on__lte=year.ends_on,
                    )
                    .order_by("-ends_on")
                    .first()
                )
            if not statement:
                errors.append(
                    f"{bank.name} : validez le relevé à la date de clôture (ou le dernier relevé à zéro pour un compte désactivé)."
                )
                continue
            transit = sum(
                (l.debit - l.credit for l in pending_at(bank, year.ends_on)), ZERO
            )
            if bank_balance(bank, year.ends_on) - transit != statement.closing_balance:
                errors.append(
                    f"{bank.name} : le rapprochement doit être revérifié après les nouvelles écritures."
                )
    if Line.objects.filter(
        entry__year=year,
        entry__reversal_of__isnull=True,
        entry__reversal__isnull=True,
        account__code__startswith="67",
        project__isnull=True,
    ).exists():
        errors.append("Reliez les charges exceptionnelles 67 à leurs opérations.")
    return list(dict.fromkeys(errors))


def close_year(year, next_year, data, user):
    if next_year.starts_on != year.ends_on + timedelta(days=1) or next_year.closed:
        raise ValueError(
            "Choisissez l’exercice ouvert qui commence le lendemain de la clôture."
        )
    errors = close_checks(year)
    if errors:
        raise ValueError(" · ".join(errors))
    if Entry.objects.filter(year=next_year, kind__in=["opening", "carry"]).exists():
        raise ValueError(
            "Un report ou une reprise existe déjà dans l’exercice suivant."
        )
    snapshot = annexes(year)
    if data.get("source_hash") != digest(snapshot):
        raise ValueError("Le dossier a changé : rechargez les contrôles de clôture.")
    # Clear current operating accounts. Incomplete works move to 120 by project.
    income = (
        Line.objects.filter(entry__year=year)
        .filter(Q(account__code__startswith="6") | Q(account__code__startswith="7"))
        .values("account__code", "project_id")
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    lines = []
    work_results = defaultdict(lambda: ZERO)
    for row in income:
        value = row["d"] - row["c"]
        if not value:
            continue
        project = (
            FinanceProject.objects.get(pk=row["project_id"])
            if row["project_id"]
            else None
        )
        lines.append(
            {
                "code": row["account__code"],
                "debit": max(-value, ZERO),
                "credit": max(value, ZERO),
                "project": project,
            }
        )
        if project and not project.completed_on:
            work_results[project] += value
    for project, value in work_results.items():
        if value:
            lines.append(
                {
                    "code": "120",
                    "debit": max(value, ZERO),
                    "credit": max(-value, ZERO),
                    "project": project,
                }
            )
    if sum(
        (signed(r.get("debit", 0)) - signed(r.get("credit", 0)) for r in lines), ZERO
    ):
        raise ValueError(
            "Le résultat courant n’est pas soldé. Vérifiez la régularisation et les produits."
        )
    closing = (
        post_entry(
            year,
            year.ends_on,
            "OD",
            "Clôture des comptes de gestion",
            lines,
            user,
            kind="closing",
        )
        if lines
        else None
    )
    balances = (
        Line.objects.filter(entry__year=year)
        .exclude(account__code__startswith="6")
        .exclude(account__code__startswith="7")
        .values(
            "account__code", "owner_id", "supplier_id", "lot_id", "key_id", "project_id"
        )
        .annotate(d=Sum("debit"), c=Sum("credit"))
    )
    from operations.models import Supplier

    carries = []
    for row in balances:
        value = row["d"] - row["c"]
        if not value:
            continue
        carries.append(
            {
                "code": row["account__code"],
                "debit": max(value, ZERO),
                "credit": max(-value, ZERO),
                "owner": (
                    Owner.objects.get(pk=row["owner_id"]) if row["owner_id"] else None
                ),
                "supplier": (
                    Supplier.objects.get(pk=row["supplier_id"])
                    if row["supplier_id"]
                    else None
                ),
                "lot": Lot.objects.get(pk=row["lot_id"]) if row["lot_id"] else None,
                "key": (
                    ChargeKey.objects.get(pk=row["key_id"]) if row["key_id"] else None
                ),
                "project": (
                    FinanceProject.objects.get(pk=row["project_id"])
                    if row["project_id"]
                    else None
                ),
            }
        )
    opening = (
        post_entry(
            next_year,
            next_year.starts_on,
            "AN",
            "Report des soldes : " + year.name,
            carries,
            user,
            kind="carry",
        )
        if carries
        else None
    )
    item = YearClosure.objects.create(
        year=year,
        next_year=next_year,
        closing_entry=closing,
        opening_entry=opening,
        snapshot=snapshot,
        digest=digest(snapshot),
        closed_by=user,
    )
    year.closed = True
    year.save(update_fields=["closed"])
    audit(user, "year.close", item.pk)
    return item
