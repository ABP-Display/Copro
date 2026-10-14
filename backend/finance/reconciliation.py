import csv
import io
from datetime import date, datetime
from decimal import Decimal
from django.db.models import Q, Sum
from .models import (
    Line,
    Entry,
    BankAccount,
    BankStatement,
    StatementLine,
    BankMatch,
    FiscalYear,
)
from .cycle import ZERO, signed, digest, audit


def parse_day(value):
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        try:
            return datetime.strptime(value.strip(), "%d/%m/%Y").date()
        except ValueError:
            raise ValueError("Date attendue : AAAA-MM-JJ ou JJ/MM/AAAA.")


def import_statement(data, user):
    bank = BankAccount.objects.select_for_update().get(pk=data["bank"])
    start = parse_day(data["starts_on"])
    end = parse_day(data["ends_on"])
    if start > end:
        raise ValueError("La période du relevé est inversée.")
    if FiscalYear.objects.filter(
        closed=True, starts_on__lte=end, ends_on__gte=start
    ).exists():
        raise ValueError("Le relevé touche un exercice clôturé.")
    opening = signed(data["opening_balance"])
    closing = signed(data["closing_balance"])
    content = str(data.get("csv", "")).lstrip("\ufeff")
    if len(content.encode()) > 2_000_000:
        raise ValueError("Le fichier dépasse 2 Mo.")
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    if reader.fieldnames != ["date", "libelle", "montant", "reference"]:
        raise ValueError(
            "En-tête attendu : date;libelle;montant;reference. Montant signé : crédit bancaire positif, débit négatif."
        )
    rows = []
    for index, row in enumerate(reader, 1):
        if index > 2000:
            raise ValueError("Un relevé contient au maximum 2 000 lignes.")
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"Ligne {index} : colonnes incorrectes.")
        day = parse_day(row["date"])
        value = signed(
            row["montant"].replace(" ", "").replace("\u00a0", "").replace(",", ".")
        )
        if (
            not start <= day <= end
            or not value
            or not row["libelle"].strip()
            or len(row["libelle"]) > 250
            or len(row["reference"]) > 100
        ):
            raise ValueError(f"Ligne {index} : date, montant ou libellé invalide.")
        rows.append(
            {
                "date": day,
                "label": row["libelle"].strip(),
                "amount": value,
                "reference": row["reference"].strip(),
            }
        )
    if opening + sum((r["amount"] for r in rows), ZERO) != closing:
        raise ValueError(
            "Solde initial + mouvements ne correspond pas au solde final déclaré."
        )
    fingerprint = digest(
        {
            "bank": bank.pk,
            "start": start,
            "end": end,
            "opening": opening,
            "closing": closing,
            "rows": rows,
        }
    )
    existing = BankStatement.objects.filter(fingerprint=fingerprint).first()
    if existing:
        return existing, False
    if BankStatement.objects.filter(
        bank=bank, starts_on__lte=end, ends_on__gte=start
    ).exists():
        raise ValueError(
            "Un relevé de cette banque couvre déjà une partie de la période."
        )
    statement = BankStatement.objects.create(
        bank=bank,
        starts_on=start,
        ends_on=end,
        opening_balance=opening,
        closing_balance=closing,
        fingerprint=fingerprint,
        created_by=user,
    )
    StatementLine.objects.bulk_create(
        [StatementLine(statement=statement, **row) for row in rows]
    )
    audit(user, "statement.import", statement.pk)
    return statement, True


def base_bank_lines(bank):
    return Line.objects.filter(account=bank.account).exclude(entry__kind="carry")


def bank_balance(bank, day):
    result = (
        base_bank_lines(bank)
        .filter(entry__date__lte=day)
        .aggregate(d=Sum("debit"), c=Sum("credit"))
    )
    return (result["d"] or ZERO) - (result["c"] or ZERO)


def pending_at(bank, day):
    return (
        base_bank_lines(bank)
        .filter(
            entry__date__lte=day,
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        )
        .exclude(entry__kind="opening")
        .filter(
            Q(bank_match__isnull=True) | Q(bank_match__statement_line__date__gt=day)
        )
        .select_related("entry")
    )


def statement_data(statement):
    rows = []
    available = (
        base_bank_lines(statement.bank)
        .filter(
            bank_match__isnull=True,
            entry__reversal_of__isnull=True,
            entry__reversal__isnull=True,
        )
        .exclude(entry__kind="opening")
        .select_related("entry")
    )
    for row in statement.rows.prefetch_related("matches").order_by("date", "id"):
        matches = list(row.matches.all())
        candidates = [
            l.pk
            for l in available
            if l.debit - l.credit == row.amount
            and abs((l.entry.date - row.date).days) <= 7
        ]
        rows.append(
            {
                "id": row.pk,
                "date": str(row.date),
                "label": row.label,
                "reference": row.reference,
                "amount": str(row.amount),
                "matched": bool(matches),
                "line_ids": [m.line_id for m in matches],
                "suggestions": candidates,
            }
        )
    ledger = bank_balance(statement.bank, statement.ends_on)
    return {
        "id": statement.pk,
        "bank": statement.bank_id,
        "bank_name": statement.bank.name,
        "starts_on": str(statement.starts_on),
        "ends_on": str(statement.ends_on),
        "opening_balance": str(statement.opening_balance),
        "closing_balance": str(statement.closing_balance),
        "ledger_balance": str(ledger),
        "difference": str(statement.closing_balance - ledger),
        "validated": statement.validated,
        "rows": rows,
        "transit": statement.transit,
        "transit_candidates": [
            {
                "id": l.pk,
                "date": str(l.entry.date),
                "label": l.entry.label,
                "amount": str(l.debit - l.credit),
            }
            for l in pending_at(statement.bank, statement.ends_on)
        ],
    }


def match_bank(row, ids, user):
    statement = BankStatement.objects.select_for_update().get(pk=row.statement_id)
    if statement.validated:
        raise ValueError("Déverrouillez le relevé avant de modifier son rapprochement.")
    if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
        raise ValueError("Choisissez des lignes comptables distinctes.")
    lines = list(
        Line.objects.select_for_update()
        .select_related("entry")
        .filter(pk__in=ids)
        .order_by("id")
    )
    if len(lines) != len(ids) or any(
        l.account_id != statement.bank.account_id
        or l.entry.kind in ("carry", "opening")
        or l.entry.reversal_of_id
        or Entry.objects.filter(reversal_of=l.entry).exists()
        for l in lines
    ):
        raise ValueError("Lignes bancaires incompatibles.")
    if row.matches.exists() or BankMatch.objects.filter(line__in=lines).exists():
        raise ValueError("Au moins une ligne est déjà rapprochée.")
    if sum((l.debit - l.credit for l in lines), ZERO) != row.amount:
        raise ValueError(
            "La somme des écritures doit être exactement égale au mouvement bancaire."
        )
    if any(l.entry.date > statement.ends_on for l in lines):
        raise ValueError("Une écriture future ne peut être rapprochée de ce relevé.")
    BankMatch.objects.bulk_create(
        [BankMatch(statement_line=row, line=l) for l in lines]
    )
    audit(user, "statement.match", row.pk)


def validate_statement(statement, user, data=None):
    if statement.validated:
        raise ValueError("Relevé déjà validé.")
    if any(not r.matches.exists() for r in statement.rows.all()):
        raise ValueError("Rapprochez toutes les lignes du relevé.")
    pending = list(pending_at(statement.bank, statement.ends_on))
    reasons = (data or {}).get("transit_reasons", {})
    if not isinstance(reasons, dict):
        raise ValueError("Motifs de transit invalides.")
    if any(
        not isinstance(reasons.get(str(l.pk)), str)
        or not 5 <= len(reasons[str(l.pk)].strip()) <= 500
        for l in pending
    ):
        raise ValueError(
            "Rapprochez chaque mouvement ou justifiez explicitement son transit (chèque non présenté, virement en cours…)."
        )
    transit = sum((l.debit - l.credit for l in pending), ZERO)
    if (
        bank_balance(statement.bank, statement.ends_on) - transit
        != statement.closing_balance
    ):
        raise ValueError(
            "Le solde comptable, corrigé des seuls mouvements en transit justifiés, ne correspond pas au relevé."
        )
    prior = (
        base_bank_lines(statement.bank)
        .filter(
            Q(entry__date__lt=statement.starts_on)
            | Q(entry__kind="opening", entry__date=statement.starts_on)
        )
        .aggregate(d=Sum("debit"), c=Sum("credit"))
    )
    previous = (
        BankStatement.objects.filter(
            bank=statement.bank, validated=True, ends_on__lt=statement.starts_on
        )
        .order_by("-ends_on")
        .first()
    )
    if previous:
        from datetime import timedelta

        if previous.ends_on + timedelta(days=1) != statement.starts_on:
            raise ValueError("Complétez la période manquante entre ces relevés.")
        expected = previous.closing_balance
    else:
        expected = (prior["d"] or ZERO) - (prior["c"] or ZERO)
    if expected != statement.opening_balance:
        raise ValueError(
            "Le solde de départ ne correspond pas à la reprise ou au relevé précédent."
        )
    statement.transit = [
        {
            "line_id": l.pk,
            "amount": str(l.debit - l.credit),
            "reason": reasons[str(l.pk)].strip(),
        }
        for l in pending
    ]
    statement.validated = True
    statement.save(update_fields=["validated", "transit"])
    audit(user, "statement.validate", statement.pk)
