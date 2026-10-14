import csv
import io
import calendar
from types import SimpleNamespace
from uuid import UUID
from datetime import date
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from core.views import manager_required, payload
from core.models import Owner, Lot
from .models import *
from .services import (
    amount,
    open_year,
    post_entry,
    distribute,
    key_weights,
    bank_for_posting,
    CHART,
)
from .views import errors, safe_csv
from .cycle import (
    ZERO,
    digest,
    allocate_charge,
    line_remaining,
    match_lines,
    outstanding,
    regularization_data,
    apply_regularization,
    opening_balance,
    funds,
    use_fund,
    finish_project,
    annexes,
    close_checks,
    close_year,
    audit,
    record_mutation,
    cancel_mutation,
)
from .reconciliation import (
    import_statement,
    statement_data,
    match_bank,
    validate_statement,
)
from .idempotency import idempotent


def line_data(line):
    return {
        "id": line.pk,
        "year": line.entry.year_id,
        "date": str(line.entry.date),
        "number": line.entry.number,
        "label": line.entry.label,
        "kind": line.entry.kind,
        "code": line.account.code,
        "owner": line.owner_id,
        "supplier": line.supplier_id,
        "key": line.key_id,
        "project": line.project_id,
        "debit": str(line.debit),
        "credit": str(line.credit),
        "remaining": str(line_remaining(line)),
        "third_party": (
            str(line.owner)
            if line.owner
            else line.supplier.name if line.supplier else "Non identifié"
        ),
    }


def preview_mutation(data, user):
    with transaction.atomic():
        mutation = record_mutation(data, user)
        rows = [
            {
                "date": str(e.date),
                "year": e.year.name,
                "label": e.label,
                "lines": [
                    {
                        "name": str(l.owner),
                        "code": l.account.code,
                        "debit": str(l.debit),
                        "credit": str(l.credit),
                    }
                    for l in e.lines.select_related("account", "owner")
                ],
            }
            for e in mutation.adjustments.select_related("year").all()
        ]
        balances = []
        for owner in [mutation.old_owner, mutation.new_owner]:
            from .services import financial_today

            totals = (
                Line.objects.filter(
                    owner=owner,
                    account__code__startswith="450",
                    entry__date__lte=financial_today(),
                )
                .exclude(entry__kind="carry")
                .aggregate(d=Sum("debit"), c=Sum("credit"))
            )
            balances.append(
                {
                    "name": str(owner),
                    "balance": str((totals["d"] or ZERO) - (totals["c"] or ZERO)),
                }
            )
        value = {
            "old_owner": str(mutation.old_owner),
            "new_owner": str(mutation.new_owner),
            "lot": mutation.lot.number,
            "effective_date": str(mutation.effective_date),
            "reference": mutation.reference,
            "adjustments": rows,
            "balances": balances,
        }
        value["source_hash"] = digest(value)
        transaction.set_rollback(True)
    return value


@require_http_methods(["GET", "POST"])
@manager_required
@errors
@idempotent
def cycle(request, resource, pk=None):
    if request.method == "GET":
        if resource == "context":
            from operations.models import Supplier

            return JsonResponse(
                {
                    "years": list(
                        FiscalYear.objects.values(
                            "id", "name", "starts_on", "ends_on", "closed"
                        )
                    ),
                    "owners": [
                        {"id": o.pk, "name": str(o)} for o in Owner.objects.all()
                    ],
                    "lots": list(Lot.objects.values("id", "number", "owner_id")),
                    "suppliers": list(
                        Supplier.objects.values("id", "name", "archived")
                    ),
                    "keys": list(ChargeKey.objects.values("id", "name")),
                    "centres": list(
                        CostCenter.objects.filter(active=True).values("id", "name")
                    ),
                    "accounts": [
                        {"code": code, "name": name}
                        for code, name in sorted(
                            {
                                **CHART,
                                **{
                                    a.code: (
                                        CHART.get(a.code, a.name)
                                        if a.name == "Charges courantes"
                                        else a.name
                                    )
                                    for a in Account.objects.filter(active=True)
                                },
                            }.items()
                        )
                    ],
                    "banks": list(
                        BankAccount.objects.select_related("account").values(
                            "id", "name", "account__code"
                        )
                    ),
                    "projects": list(
                        FinanceProject.objects.values(
                            "id", "name", "key_id", "budget", "decision", "completed_on"
                        )
                    ),
                }
            )
        if resource == "funds":
            return JsonResponse({"rows": funds()})
        if resource == "outstanding":
            return JsonResponse(
                {
                    "rows": outstanding(
                        date.fromisoformat(request.GET.get("date") or str(date.today()))
                    )
                }
            )
        if resource == "statements":
            return JsonResponse(
                {
                    "items": [
                        statement_data(s)
                        for s in BankStatement.objects.select_related("bank").all()
                    ]
                }
            )
        if resource == "bank-lines":
            query = Line.objects.filter(
                account__code__startswith="512",
                bank_match__isnull=True,
                entry__reversal_of__isnull=True,
                entry__reversal__isnull=True,
            ).exclude(entry__kind__in=["carry", "opening"])
            if request.GET.get("bank"):
                query = query.filter(account__bank__id=int(request.GET["bank"]))
            return JsonResponse(
                {
                    "rows": [
                        line_data(l)
                        for l in query.select_related(
                            "account", "entry", "owner", "supplier"
                        )
                    ]
                }
            )
        if resource == "lettering":
            query = (
                Line.objects.filter(
                    Q(account__code__startswith="450")
                    | Q(account__code__startswith="40"),
                    entry__reversal_of__isnull=True,
                    entry__reversal__isnull=True,
                )
                .exclude(entry__kind="carry")
                .select_related("account", "entry", "owner", "supplier")
            )
            return JsonResponse(
                {
                    "rows": [line_data(l) for l in query if line_remaining(l) > 0],
                    "matches": list(
                        Settlement.objects.filter(active=True).values(
                            "id", "debit_line_id", "credit_line_id", "amount"
                        )
                    ),
                }
            )
        if resource == "corrections":
            query = Entry.objects.filter(
                year_id=request.GET["year"],
                kind="normal",
                reversal_of__isnull=True,
                reversal__isnull=True,
            ).order_by("-date", "-number")[:200]
            return JsonResponse(
                {
                    "rows": [
                        {
                            "id": e.pk,
                            "number": e.number,
                            "date": str(e.date),
                            "label": e.label,
                            "journal": e.journal,
                        }
                        for e in query
                    ]
                }
            )
        if resource == "mutations":
            return JsonResponse(
                {
                    "rows": [
                        {
                            "id": m.pk,
                            "lot_number": m.lot.number,
                            "old_owner": str(m.old_owner),
                            "new_owner": str(m.new_owner),
                            "effective_date": str(m.effective_date),
                            "reference": m.reference,
                            "active": m.active,
                            "adjustments": m.adjustments.count(),
                        }
                        for m in OwnershipChange.objects.select_related(
                            "lot", "old_owner", "new_owner"
                        ).order_by("-effective_date", "-id")
                    ]
                }
            )
        year = FiscalYear.objects.get(pk=request.GET["year"])
        if resource == "opening":
            originals = Entry.objects.filter(
                year=year,
                kind="opening",
                reversal_of__isnull=True,
                reversal__isnull=True,
            )
            return JsonResponse(
                {
                    "entries": [
                        {
                            "id": e.pk,
                            "date": str(e.date),
                            "reference": e.reference,
                            "rows": [
                                line_data(l)
                                for l in e.lines.select_related(
                                    "entry", "account", "owner", "supplier"
                                )
                            ],
                        }
                        for e in originals
                    ]
                }
            )
        if resource == "allocation":
            query = (
                Line.objects.filter(entry__year=year)
                .filter(
                    Q(account__code__startswith="6") | Q(account__code__startswith="7")
                )
                .exclude(account__code__in=["701", "702"])
                .exclude(
                    entry__kind__in=["closing", "regularization", "project-complete"]
                )
            )
            return JsonResponse(
                {
                    "rows": [
                        line_data(l)
                        for l in query.select_related(
                            "account", "entry", "owner", "supplier"
                        )
                        if sum((r.amount for r in l.charge_allocations.all()), ZERO)
                        != l.debit - l.credit
                    ]
                }
            )
        if resource == "regularization":
            saved = AnnualSettlement.objects.filter(year=year, active=True).first()
            selected_date = (
                date.fromisoformat(request.GET["approved_on"])
                if request.GET.get("approved_on")
                else saved.approved_on if saved else None
            )
            return JsonResponse(
                {
                    "preview": regularization_data(year, selected_date),
                    "saved": (
                        {
                            "id": saved.pk,
                            "decision": saved.decision,
                            "approved_on": str(saved.approved_on),
                            "data": saved.data,
                        }
                        if saved
                        else None
                    ),
                }
            )
        if resource in ("annexes", "close"):
            saved = YearClosure.objects.filter(year=year).first()
            pack = saved.snapshot if saved else annexes(year)
            return JsonResponse(
                {
                    "data": pack,
                    "source_hash": saved.digest if saved else digest(pack),
                    "errors": close_checks(year),
                    "closed": bool(saved),
                }
            )
        if resource == "archive":
            saved = YearClosure.objects.filter(year=year).first()
            value = {
                "closed": bool(saved),
                "digest": saved.digest if saved else None,
                "data": saved.snapshot if saved else annexes(year),
            }
            response = JsonResponse(
                value, json_dumps_params={"ensure_ascii": False, "indent": 2}
            )
            response["Content-Disposition"] = (
                f'attachment; filename="dossier-comptable-{year.pk}.json"'
            )
            return response
        if resource == "fec":
            return fec(year)
        return JsonResponse({"error": "Ressource inconnue."}, status=404)

    data = payload(request)
    with transaction.atomic():
        # Keep a consistent lock order across closing, matching and allocations.
        list(FiscalYear.objects.select_for_update().order_by("id"))
        if resource == "statements":
            statement, created = import_statement(data, request.user)
            return JsonResponse(
                {"id": statement.pk, "created": created}, status=201 if created else 200
            )
        if resource in ("bank-match", "bank-unmatch"):
            row = (
                StatementLine.objects.select_for_update()
                .select_related("statement")
                .get(pk=pk)
            )
            if FiscalYear.objects.filter(
                closed=True,
                starts_on__lte=row.statement.ends_on,
                ends_on__gte=row.statement.starts_on,
            ).exists():
                raise ValueError("Période clôturée.")
            if resource == "bank-match":
                match_bank(row, data["line_ids"], request.user)
            else:
                if row.statement.validated:
                    raise ValueError(
                        "Déverrouillez le relevé avant de modifier le rapprochement."
                    )
                row.matches.all().delete()
                audit(request.user, "statement.unmatch", pk)
            return JsonResponse({"ok": True})
        if resource in ("validate-statement", "unlock-statement"):
            statement = BankStatement.objects.select_for_update().get(pk=pk)
            if FiscalYear.objects.filter(
                closed=True,
                starts_on__lte=statement.ends_on,
                ends_on__gte=statement.starts_on,
            ).exists():
                raise ValueError("Période clôturée.")
            if resource == "validate-statement":
                validate_statement(statement, request.user, data)
            else:
                statement.validated = False
                statement.save(update_fields=["validated"])
                audit(request.user, "statement.unlock", pk)
            return JsonResponse({"ok": True})
        if resource == "lettering":
            if (
                Line.objects.get(pk=data["credit_line"]).entry.year.closed
                and Line.objects.get(pk=data["debit_line"]).entry.year.closed
            ):
                raise ValueError(
                    "Le lettrage doit comporter une opération d’un exercice ouvert."
                )
            item = match_lines(
                Line.objects.get(pk=data["debit_line"]),
                Line.objects.get(pk=data["credit_line"]),
                data["amount"],
                request.user,
            )
            return JsonResponse({"id": item.pk}, status=201)
        if resource == "unletter":
            item = (
                Settlement.objects.select_for_update()
                .select_related("credit_line__entry__year")
                .get(pk=pk)
            )
            if item.credit_line.entry.kind == "ownership":
                raise ValueError(
                    "Ce lettrage accompagne une mutation ; utilisez sa correction dédiée."
                )
            if item.credit_line.entry.year.closed and item.debit_line.entry.year.closed:
                raise ValueError(
                    "Les deux mouvements appartiennent à des exercices clôturés."
                )
            item.active = False
            item.save(update_fields=["active"])
            if any(Decimal(row["available"]) < 0 for row in funds()):
                raise ValueError(
                    "Cette affectation finance déjà des travaux : corrigez d’abord l’affectation du fonds."
                )
            audit(request.user, "settlement.cancel", pk)
            return JsonResponse({"ok": True})
        if resource == "project":
            name = str(data["name"]).strip()
            decision = str(data["decision"]).strip()
            if not name or len(name) > 150 or not decision or len(decision) > 250:
                raise ValueError("Nom et décision requis.")
            project = FinanceProject.objects.create(
                name=name,
                key=ChargeKey.objects.get(pk=data["key"]),
                budget=amount(data["budget"], False),
                decision=decision,
            )
            audit(request.user, "project.create", project.pk)
            return JsonResponse({"id": project.pk}, status=201)
        if resource == "mutation":
            if (
                data.get("source_hash")
                != preview_mutation(data, request.user)["source_hash"]
            ):
                raise ValueError(
                    "Les comptes ou propriétaires ont changé : vérifiez de nouveau l’aperçu."
                )
            item = record_mutation(data, request.user)
            return JsonResponse({"id": item.pk}, status=201)
        if resource == "preview-mutation":
            return JsonResponse(preview_mutation(data, request.user))
        if resource == "cancel-mutation":
            item = cancel_mutation(
                OwnershipChange.objects.select_for_update().get(pk=pk), request.user
            )
            return JsonResponse({"id": item.pk})
        year = FiscalYear.objects.select_for_update().get(pk=data["year"])
        if resource == "legacy-reopen":
            if (
                not year.closed
                or YearClosure.objects.filter(Q(year=year) | Q(next_year=year)).exists()
            ):
                raise ValueError(
                    "Seul un ancien verrouillage technique, sans clôture définitive ou report, peut être repris."
                )
            year.closed = False
            year.save(update_fields=["closed"])
            audit(request.user, "year.legacy_reopen", year.pk)
            return JsonResponse({"ok": True})
        if year.closed:
            raise ValueError(
                "Exercice clôturé : utilisez une correction dans un exercice ouvert."
            )
        if resource == "opening":
            item = opening_balance(year, data, request.user)
        elif resource == "undo-opening":
            original = Entry.objects.select_for_update(of=("self",)).get(
                pk=pk,
                year=year,
                kind="opening",
                reversal_of__isnull=True,
                reversal__isnull=True,
            )
            if (
                Settlement.objects.filter(active=True)
                .filter(Q(debit_line__entry=original) | Q(credit_line__entry=original))
                .exists()
            ):
                raise ValueError(
                    "Annulez les lettrages de la reprise avant sa correction."
                )
            rows = [
                {
                    "code": l.account.code,
                    "owner": l.owner,
                    "supplier": l.supplier,
                    "lot": l.lot,
                    "debit": l.credit,
                    "credit": l.debit,
                    "due_date": l.due_date,
                }
                for l in original.lines.select_related(
                    "account", "owner", "supplier", "lot"
                )
            ]
            item = post_entry(
                year,
                year.starts_on,
                "AN",
                "Correction de la reprise initiale",
                rows,
                request.user,
                reversal_of=original,
                kind="opening",
            )
            if any(Decimal(r["available"]) < 0 for r in funds()):
                raise ValueError(
                    "Corrigez d’abord les affectations du fonds provenant de cette reprise."
                )
            audit(request.user, "opening.cancel", original.pk)
        elif resource == "allocation":
            line = (
                Line.objects.select_for_update()
                .select_related("entry", "account")
                .get(pk=pk, entry__year=year)
            )
            if (
                AnnualSettlement.objects.filter(year=year, active=True).exists()
                or line.charge_allocations.exists()
                or not line.account.code.startswith(("6", "7"))
                or line.account.code in ("701", "702")
            ):
                raise ValueError(
                    "Cette répartition est figée ou concerne un appel ; corrigez l’opération source."
                )
            if line.entry.kind != "normal":
                raise ValueError(
                    "Cette écriture système ne se répartit pas manuellement."
                )
            line.key = ChargeKey.objects.get(pk=data["key"])
            if data.get("project"):
                line.project = FinanceProject.objects.get(pk=data["project"])
            if line.account.code.startswith("67") and not line.project_id:
                raise ValueError("Identifiez les travaux pour cette charge 67.")
            if line.project_id and line.project.key_id != line.key_id:
                raise ValueError("La clé doit être celle des travaux.")
            line.save(update_fields=["key", "project"])
            allocate_charge(line)
            audit(request.user, "line.allocate", line.pk)
            item = line
        elif resource == "regularization":
            item = apply_regularization(year, data, request.user)
        elif resource == "undo-regularization":
            item = AnnualSettlement.objects.select_for_update().get(
                pk=pk, year=year, active=True
            )
            if item.entry_id:
                rows = [
                    {
                        "code": l.account.code,
                        "owner": l.owner,
                        "lot": l.lot,
                        "key": l.key,
                        "debit": l.credit,
                        "credit": l.debit,
                        "due_date": l.due_date,
                    }
                    for l in item.entry.lines.select_related(
                        "account", "owner", "lot", "key"
                    )
                ]
                if (
                    Settlement.objects.filter(active=True)
                    .filter(
                        Q(debit_line__entry=item.entry)
                        | Q(credit_line__entry=item.entry)
                    )
                    .exists()
                ):
                    raise ValueError(
                        "Annulez les lettrages de cette régularisation avant sa correction."
                    )
                post_entry(
                    year,
                    year.ends_on,
                    "OD",
                    "Annulation de régularisation",
                    rows,
                    request.user,
                    reversal_of=item.entry,
                    kind="regularization",
                )
            item.active = False
            item.save(update_fields=["active"])
            audit(request.user, "regularization.cancel", pk)
        elif resource == "close":
            next_year = FiscalYear.objects.select_for_update().get(pk=data["next_year"])
            item = close_year(year, next_year, data, request.user)
        elif resource == "fund-use":
            project = FinanceProject.objects.select_for_update().get(pk=pk)
            open_year(year.pk, date.fromisoformat(data["date"]))
            item = use_fund(project, year, data, request.user)
        elif resource == "project-complete":
            project = FinanceProject.objects.select_for_update().get(pk=pk)
            open_year(year.pk, date.fromisoformat(data["date"]))
            item = finish_project(project, year, data, request.user)
        elif resource == "cancel-entry":
            original = Entry.objects.select_for_update().get(pk=pk, year=year)
            if (
                original.kind != "normal"
                or original.reversal_of_id
                or Entry.objects.filter(reversal_of=original).exists()
            ):
                raise ValueError(
                    "Cette opération est déjà corrigée ou dépend d’un parcours dédié."
                )
            if (
                BankMatch.objects.filter(line__entry=original).exists()
                or Settlement.objects.filter(active=True)
                .filter(Q(debit_line__entry=original) | Q(credit_line__entry=original))
                .exists()
            ):
                raise ValueError(
                    "Dissociez les rapprochements et lettrages avant de corriger cette opération."
                )
            invoice = Expense.objects.filter(entry=original).first()
            if AllocationTransfer.objects.filter(
                allocation__call__entry=original, mutation__active=True
            ).exists():
                raise ValueError("Corrigez d’abord les mutations liées à cet appel.")
            if (
                invoice
                and invoice.payments.filter(entry__reversal__isnull=True).exists()
            ):
                raise ValueError(
                    "Corrigez les règlements avant de corriger leur facture."
                )
            rows = [
                {
                    "code": l.account.code,
                    "owner": l.owner,
                    "supplier": l.supplier,
                    "lot": l.lot,
                    "key": l.key,
                    "project": l.project,
                    "debit": l.credit,
                    "credit": l.debit,
                    "due_date": l.due_date,
                }
                for l in original.lines.select_related(
                    "account", "owner", "supplier", "lot", "key", "project"
                )
            ]
            item = post_entry(
                year,
                date.fromisoformat(data["date"]),
                original.journal,
                "Correction : " + original.label[:230],
                rows,
                request.user,
                reversal_of=original,
            )
            if any(Decimal(row["available"]) < 0 for row in funds()):
                raise ValueError(
                    "Cette cotisation finance déjà des travaux : corrigez d’abord leur affectation."
                )
            Expense.objects.filter(payment_entry=original).update(payment_entry=None)
            audit(request.user, "operation.cancel", original.pk)
        elif resource == "pay-balance":
            source = (
                Line.objects.select_for_update(of=("self",))
                .select_related("entry", "account", "supplier")
                .get(pk=pk)
            )
            if (
                source.entry.kind != "opening"
                or not source.credit
                or not source.supplier_id
                or not source.account.code.startswith("40")
            ):
                raise ValueError(
                    "Choisissez une dette fournisseur identifiée dans la reprise initiale."
                )
            value = amount(data["amount"])
            if value > line_remaining(source):
                raise ValueError("Le règlement dépasse le reste à payer.")
            day = date.fromisoformat(data["date"])
            open_year(year.pk, day)
            if day < source.entry.date:
                raise ValueError("Le paiement ne peut précéder la reprise.")
            bank = bank_for_posting(data.get("bank"))
            centre = (
                CostCenter.objects.get(pk=data["cost_center"])
                if data.get("cost_center")
                else None
            )
            item = post_entry(
                year,
                day,
                "BQ",
                "Règlement de dette reprise : " + source.supplier.name,
                [
                    {
                        "code": source.account.code,
                        "supplier": source.supplier,
                        "debit": value,
                    },
                    {"code": bank.account.code if bank else "512", "credit": value},
                ],
                request.user,
                cost_center=centre,
            )
            match_lines(
                item.lines.get(account=source.account), source, value, request.user
            )
        elif resource == "call-schedule":
            request_id = UUID(str(data["request_id"]))
            source_hash = digest(data)
            item = CallSchedule.objects.filter(request_id=request_id).first()
            if item:
                if item.source_hash != source_hash:
                    raise ValueError(
                        "Cet identifiant d’échéancier a déjà été utilisé avec d’autres données."
                    )
                return JsonResponse({"id": item.pk, "created": False})
            count = int(data.get("count", 4))
            interval = int(data.get("interval", 3))
            total = amount(data["amount"])
            if (
                isinstance(data.get("count"), bool)
                or isinstance(data.get("interval"), bool)
                or not 1 <= count <= 12
                or not 1 <= interval <= 12
                or total * 100 < count
            ):
                raise ValueError(
                    "De 1 à 12 échéances non nulles, espacées de 1 à 12 mois."
                )
            if (
                data.get("kind", "current") == "current"
                and (count != 4 or interval != 3)
                and not data.get("decision")
            ):
                raise ValueError(
                    "Indiquez la décision pour un échéancier différent des quatre provisions trimestrielles."
                )
            first = date.fromisoformat(data["first_date"])
            label = str(data.get("label", "Appel de fonds")).strip()
            if not label or len(label) > 125:
                raise ValueError("Libellé attendu, 125 caractères maximum.")
            item = CallSchedule.objects.create(
                request_id=request_id,
                source_hash=source_hash,
                year=year,
                created_by=request.user,
            )
            rows = distribute(
                total,
                [(SimpleNamespace(pk=i), Decimal(1)) for i in range(count)],
                require_owner=False,
            )
            from .views import form_value
            from .forms import CallForm

            for part, weight, value in rows:
                ordinal = first.year * 12 + first.month - 1 + part.pk * interval
                y, m = divmod(ordinal, 12)
                day = date(y, m + 1, min(first.day, calendar.monthrange(y, m + 1)[1]))
                open_year(year.pk, day)
                form = form_value(
                    CallForm,
                    {
                        "year": year.pk,
                        "key": data["key"],
                        "label": f"{label} · {part.pk+1}/{count}",
                        "date": str(day),
                        "due_date": str(day),
                        "amount": str(value),
                        "kind": data.get("kind", "current"),
                        "project": data.get("project"),
                        "decision": data.get("decision", ""),
                        "cost_center": data.get("cost_center"),
                    },
                )
                call = form.save(commit=False)
                call.schedule = item
                call.save()
            audit(request.user, "calls.schedule", item.pk)
        else:
            return JsonResponse({"error": "Action inconnue."}, status=404)
    return JsonResponse({"id": item.pk if item else None}, status=201)


def fec(year):
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter="\t", lineterminator="\n")
    writer.writerow(
        [
            "JournalCode",
            "JournalLib",
            "EcritureNum",
            "EcritureDate",
            "CompteNum",
            "CompteLib",
            "CompAuxNum",
            "CompAuxLib",
            "PieceRef",
            "PieceDate",
            "EcritureLib",
            "Debit",
            "Credit",
            "EcritureLet",
            "DateLet",
            "ValidDate",
            "Montantdevise",
            "Idevise",
        ]
    )
    journals = {j.code: j.name for j in Journal.objects.all()}
    active = list(
        Settlement.objects.filter(active=True).select_related(
            "debit_line", "credit_line"
        )
    )
    parents = {}
    matched = {}
    dates = {}
    amounts = {}

    def root(pk):
        parents.setdefault(pk, pk)
        if parents[pk] != pk:
            parents[pk] = root(parents[pk])
        return parents[pk]

    for match in active:
        a, b = root(match.debit_line_id), root(match.credit_line_id)
        parents[max(a, b)] = min(a, b)
        for line in [match.debit_line, match.credit_line]:
            matched[line.pk] = matched.get(line.pk, Decimal(0)) + match.amount
            amounts[line.pk] = line.debit + line.credit
    complete = {}
    for pk in parents:
        identity = root(pk)
        complete[identity] = complete.get(identity, True) and matched[pk] == amounts[pk]
    for match in active:
        identity = root(match.debit_line_id)
        dates[identity] = max(dates.get(identity, match.created_at), match.created_at)
    for line in (
        Line.objects.filter(entry__year=year)
        .select_related("entry", "account", "owner", "supplier")
        .order_by("entry__number", "id")
    ):
        entry = line.entry
        third = line.owner or line.supplier
        prefix = "COP" if line.owner else "FOU"
        group = root(line.pk) if line.pk in parents else None
        fully = group is not None and complete[group]
        writer.writerow(
            [
                safe_csv(
                    str(v).replace("\t", " ").replace("\r", " ").replace("\n", " ")
                )
                for v in [
                    entry.journal,
                    journals.get(entry.journal, entry.journal),
                    entry.number,
                    entry.date.strftime("%Y%m%d"),
                    line.account.code,
                    line.account.name,
                    prefix + str(third.pk) if third else "",
                    str(third) if third else "",
                    entry.reference or f"E{entry.number}",
                    entry.date.strftime("%Y%m%d"),
                    entry.label,
                    f"{line.debit:.2f}",
                    f"{line.credit:.2f}",
                    f"L{group}" if fully else "",
                    (
                        timezone.localtime(dates[group]).strftime("%Y%m%d")
                        if fully
                        else ""
                    ),
                    timezone.localtime(entry.created_at).strftime("%Y%m%d"),
                    "",
                    "",
                ]
            ]
        )
    response = HttpResponse(stream.getvalue(), content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="comptabilite-{year.pk}.txt"'
    )
    return response
