from functools import wraps
from datetime import date
from decimal import Decimal
import secrets
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse, FileResponse, Http404
from django.utils import timezone
from django.db.models import Q, Exists, OuterRef, Sum, Value, F
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_http_methods
from core.access import member_required, user_data
from core.views import payload
from core.models import Owner
from documents.models import Version, Document
from finance.models import FiscalYear, Expense, Entry, Line, Budget, BankAccount, ChargeKey, CostCenter, Account, FinanceProject, ExpensePayment, BankStatement
from finance.forms import ExpenseForm
from finance.services import amount, record_expense
from governance.models import AssemblyMandate
from operations.models import Quote, Contract, Supplier, Case
from .models import CouncilSettings, Mandate, ExternalAccess, ExpenseDraft, ReviewRequest, AccountControl, CouncilEvent
from .access import can, capabilities, active_mandates, is_manager, READ, PREPARE, CONTROL, ROLE_CAPABILITIES
from . import services as service


def council_required(view):
    @wraps(view)
    @member_required
    def wrapped(request, *args, **kwargs):
        if not can(request.user, READ):
            return JsonResponse({"error": "Votre mandat ne donne pas accès au conseil syndical."}, status=403)
        try:
            return view(request, *args, **kwargs)
        except PermissionError as error:
            return JsonResponse({"error": str(error)}, status=403)
        except ObjectDoesNotExist:
            return JsonResponse({"error": "Élément ou pièce introuvable."}, status=404)
        except (ValueError, TypeError, KeyError, ValidationError) as error:
            return JsonResponse({"error": " · ".join(error.messages) if isinstance(error, ValidationError) else str(error)}, status=400)
        except IntegrityError:
            return JsonResponse({"error": "Un élément existe déjà ou vient d’être modifié. Actualisez la page."}, status=409)
    return wrapped


def require(user, capability):
    if not can(user, capability):
        raise PermissionError("Votre responsabilité ne permet pas cette action.")


def person(user):
    owner = getattr(user, "owner_profile", None)
    return str(owner) if owner else user.get_full_name() or user.username


def mandate_data(item, active_ids):
    return {"id": item.pk, "user": item.user_id, "owner": item.owner_id, "name": person(item.user), "role": item.role,
            "role_label": item.get_role_display(), "starts_on": item.starts_on, "ends_on": item.ends_on, "authority": item.authority,
            "reference": item.reference, "proof": item.proof_id, "seat": item.seat_id, "assembly_mandate": item.assembly_mandate_id,
            "active": item.pk in active_ids, "revoked_at": item.revoked_at, "revocation_reason": item.revocation_reason,
            "permanent_manager": item.user.is_staff or item.user.is_superuser}


def config_data(item):
    return {"mode": item.mode, "approval_enabled": item.approval_enabled, "threshold": str(item.threshold),
            "required_approvals": item.required_approvals, "reference": item.reference, "proof": item.proof_id}


def review_data(item):
    target = service.request_target(item)
    can_withdraw = not item.withdrawn_at and not service.consumed(item)
    return {"id": item.pk, "kind": item.kind, "expense": item.expense_id, "quote": item.quote_id, "draft": item.draft_id,
            "snapshot": item.snapshot, "proof": item.proof_id, "state": service.request_state(item), "required_approvals": service.required_reviews(item),
            "created_by": person(item.created_by), "created_by_id": item.created_by_id, "created_at": item.created_at,
            "withdrawn_at": item.withdrawn_at, "withdrawal_reason": item.withdrawal_reason, "can_withdraw": can_withdraw,
            "reviews": [{"id": r.pk, "author": person(r.author), "author_id": r.author_id, "decision": r.decision, "reason": r.reason, "created_at": r.created_at, "mandate": r.mandate_id} for r in item.reviews.select_related("author")]}


CHECKS = ["books", "invoices", "banks", "allocation", "budget"]


def control_data(item):
    return {"id": item.pk, "year": item.year_id, "year_name": item.year.name, "title": item.title, "observations": item.observations,
            "checks": item.checks, "conclusion": item.conclusion, "evidence": list(item.evidence.values_list("pk", flat=True)),
            "author": person(item.author), "author_id": item.author_id, "mandate": item.mandate_id, "created_at": item.created_at,
            "finalized_at": item.finalized_at, "snapshot": item.snapshot,
            "changed_since_control": bool(item.finalized_at and item.snapshot != service.account_snapshot(item.year))}


@require_http_methods(["GET"])
@council_required
def context(request):
    config, _ = CouncilSettings.objects.get_or_create(pk=1)
    admin = request.user.is_superuser
    mandates = list(Mandate.objects.select_related("user", "owner"))
    active_ids = set()
    for user in {m.user_id: m.user for m in mandates}.values():
        active_ids.update(active_mandates(user).values_list("pk", flat=True))
    data = {
        "user": user_data(request.user), "settings": config_data(config),
        "roles": [{"value": r, "label": label, "capabilities": sorted(ROLE_CAPABILITIES[r])} for r, label in Mandate.Role.choices],
        "mandates": [mandate_data(m, active_ids) for m in mandates],
        "years": list(FiscalYear.objects.values("id", "name", "starts_on", "ends_on", "closed")),
        "keys": list(ChargeKey.objects.values("id", "name")),
        "centers": list(CostCenter.objects.filter(active=True).values("id", "name")),
        "accounts": list(Account.objects.filter(active=True, code__startswith="6").values("code", "name")),
        "suppliers": list(Supplier.objects.filter(archived=False).values("id", "name")),
        "projects": list(FinanceProject.objects.filter(completed_on__isnull=True).values("id", "name")),
        "documents": list(Document.objects.filter(archived=False, current__isnull=False).values("id", "title", "current")),
        "versions": [{"id": v.pk, "document": v.document_id, "title": v.document.title, "filename": v.filename} for v in Version.objects.select_related("document").filter(document__archived=False)],
    }
    if admin:
        data["owners"] = [{"id": o.pk, "name": str(o), "has_access": bool(o.user_id), "user": o.user_id} for o in Owner.objects.all()]
        data["users"] = [{"id": u.pk, "name": person(u), "email": u.email, "permanent_manager": u.is_staff or u.is_superuser, "is_active": u.is_active, "external": hasattr(u, "council_identity")} for u in get_user_model().objects.select_related("owner_profile", "council_identity")]
        data["assembly_mandates"] = [{"id": m.pk, "owner": m.owner_id, "name": str(m.owner), "kind": m.kind, "starts_on": m.starts_on, "ends_on": m.ends_on, "reference": m.decision.data.get("reference", ""), "signed": m.decision.vote.workflow.phase in ["signed", "closed"]} for m in AssemblyMandate.objects.select_related("owner", "decision__vote__workflow").filter(mandate__isnull=True)]
    return JsonResponse(data)


@require_http_methods(["PATCH"])
@council_required
def settings(request):
    require(request.user, "access.admin")
    data = payload(request)
    if set(data) - {"mode", "approval_enabled", "threshold", "required_approvals", "reference", "proof", "reason"}:
        raise ValueError("Champ de configuration inconnu.")
    with transaction.atomic():
        item = service.settings_locked()
        before = config_data(item)
        mode = data.get("mode", item.mode)
        if mode not in ["benevole", "cooperative"]:
            raise ValueError("Choisissez bénévole ou coopératif.")
        if mode != item.mode and Mandate.objects.filter(role__in=["syndic", "coop_syndic", "president", "vice"], revoked_at__isnull=True, ends_on__gte=timezone.localdate()).exists():
            raise ValueError("Terminez les mandats de direction concernés avant de changer de mode.")
        enabled = data.get("approval_enabled", item.approval_enabled)
        if not isinstance(enabled, bool):
            raise ValueError("Choix de contrôle invalide.")
        minimum = data.get("required_approvals", item.required_approvals)
        if isinstance(minimum, bool) or str(minimum) not in [str(n) for n in range(1, 11)]:
            raise ValueError("Choisissez de 1 à 10 avis distincts.")
        item.mode, item.approval_enabled, item.required_approvals = mode, enabled, int(minimum)
        item.threshold = amount(data.get("threshold", item.threshold), False)
        item.reference = service.text(data.get("reference", item.reference), required=enabled)
        item.proof = Version.objects.get(pk=data["proof"]) if data.get("proof") else item.proof
        if enabled and not item.proof:
            raise ValueError("Rattachez le document définissant la règle de contrôle interne.")
        if enabled and item.proof.document.archived:
            raise ValueError("Restaurez la pièce définissant la règle avant de l’activer.")
        reason = service.text(data.get("reason"))
        item.full_clean(); item.save()
        service.event(request.user, "settings.updated", "1", {"before": before, "after": config_data(item), "reason": reason})
    return JsonResponse(config_data(item))


@require_http_methods(["POST"])
@council_required
def mandates(request, pk=None, action=None):
    require(request.user, "access.admin")
    data = payload(request)
    with transaction.atomic():
        service.settings_locked()
        if pk is None:
            item, credentials = service.create_mandate(data, request.user)
            return JsonResponse({"id": item.pk, "credentials": credentials}, status=201)
        item = Mandate.objects.select_for_update().get(pk=pk)
        if action == "revoke":
            if item.revoked_at:
                raise ValueError("Ce mandat est déjà terminé.")
            reason = service.text(data.get("reason"))
            item.revoked_at = timezone.now(); item.revocation_reason = reason
            item.save(update_fields=["revoked_at", "revocation_reason"])
            service.event(request.user, "mandate.revoked", item.pk, {"reason": reason, "user": item.user_id, "role": item.role})
            return JsonResponse({"ok": True})
        if action == "reset-external":
            identity = ExternalAccess.objects.select_for_update().get(user=item.user)
            if item.user.is_staff or item.user.is_superuser or not item.user.is_active:
                raise ValueError("Ce compte ne peut pas être réinitialisé ici.")
            password = secrets.token_urlsafe(18)
            item.user.set_password(password); item.user.save(update_fields=["password"])
            identity.must_change_password = True; identity.save(update_fields=["must_change_password"])
            service.event(request.user, "external.reset", item.user_id)
            return JsonResponse({"credentials": {"email": item.user.email, "temporary_password": password}})
        raise ValueError("Action de mandat inconnue.")


def canonical_draft(data):
    allowed = set(ExpenseForm.Meta.fields) | {"charge_code", "cost_center"}
    if set(data) - allowed or any(isinstance(v, (dict, list, bool)) for v in data.values()):
        raise ValueError("Champs de dépense invalides.")
    form = ExpenseForm(data)
    if not form.is_valid():
        raise ValueError(" · ".join(" ".join(v) for v in form.errors.values()))
    item = form.instance
    if item.year.closed:
        raise ValueError("Choisissez un exercice ouvert.")
    result = {}
    for key in ExpenseForm.Meta.fields:
        value = getattr(item, key + "_id") if key in ["year", "key", "supplier_record", "document", "project"] else getattr(item, key)
        result[key] = str(value) if isinstance(value, (date, Decimal)) else value
    if data.get("cost_center"):
        result["cost_center"] = CostCenter.objects.get(pk=data["cost_center"], active=True).pk
    code = str(data.get("charge_code") or ("671" if item.project_id else "601"))
    from finance.services import CHART
    if not code.startswith("6") or code.startswith("67") != bool(item.project_id) or code not in CHART and not Account.objects.filter(code=code, active=True).exists():
        raise ValueError("Choisissez un compte de charges adapté à la dépense.")
    result["charge_code"] = code
    return result


def draft_data(item):
    review = ReviewRequest.objects.filter(draft=item, withdrawn_at__isnull=True).first()
    return {"id": item.pk, "data": item.data, "status": item.status, "expense": item.expense_id,
            "author": person(item.created_by), "author_id": item.created_by_id, "created_at": item.created_at,
            "review_state": service.request_state(review) if review else None}


@require_http_methods(["GET", "POST", "PATCH"])
@council_required
def drafts(request, pk=None, action=None):
    if request.method == "GET":
        query = ExpenseDraft.objects.select_related("created_by").order_by("-id")[:200]
        return JsonResponse({"items": [draft_data(d) for d in query]})
    require(request.user, PREPARE)
    data = payload(request)
    with transaction.atomic():
        service.settings_locked()
        if pk is None:
            item = ExpenseDraft.objects.create(data=canonical_draft(data), created_by=request.user)
            service.event(request.user, "expense.prepared", item.pk, item.data)
            return JsonResponse({"id": item.pk}, status=201)
        item = ExpenseDraft.objects.select_for_update().get(pk=pk)
        if request.method == "PATCH" and not action:
            if item.status != "draft" or not (is_manager(request.user) or item.created_by_id == request.user.pk):
                raise ValueError("Seul votre brouillon peut être corrigé ; retirez la demande de contrôle si nécessaire.")
            item.data = canonical_draft(data)
            item.save(update_fields=["data"])
            service.event(request.user, "expense.updated", item.pk, item.data)
            return JsonResponse({"id": item.pk})
        if action == "submit":
            result = service.create_request("draft", item.pk, request.user, data.get("proof"))
            return JsonResponse({"id": result.pk}, status=201)
        if action == "cancel":
            if item.status != "draft" or not (is_manager(request.user) or item.created_by_id == request.user.pk):
                raise ValueError("Retirez d’abord la demande de contrôle, ou choisissez votre brouillon.")
            item.status = "cancelled"; item.save(update_fields=["status"])
            service.event(request.user, "expense.cancelled", item.pk, {"reason": service.text(data.get("reason"))})
            return JsonResponse({"ok": True})
        if action == "post":
            require(request.user, "management.write")
            if item.status != "submitted" or item.expense_id:
                raise ValueError("Choisissez une préparation soumise et non comptabilisée.")
            review = ReviewRequest.objects.select_for_update().get(draft=item, withdrawn_at__isnull=True)
            if service.request_state(review) != "approved":
                raise ValueError("Cette préparation doit recevoir les avis favorables avant comptabilisation.")
            config = service.settings_locked()
            if config.approval_enabled and Decimal(item.data["amount"]) >= config.threshold and review.reviews.filter(decision="approved").count() < config.required_approvals:
                raise ValueError("Le nombre d’avis requis a augmenté ; complétez le contrôle.")
            expense = record_expense(item.data, request.user)
            item.expense = expense; item.status = "posted"; item.save(update_fields=["expense", "status"])
            review.expense = expense; review.posted_snapshot = service.expense_snapshot(expense)
            review.save(update_fields=["expense", "posted_snapshot"])
            service.event(request.user, "expense.posted", item.pk, {"expense": expense.pk, "review": review.pk})
            return JsonResponse({"expense": expense.pk}, status=201)
        raise ValueError("Action de préparation inconnue.")


@require_http_methods(["GET", "POST"])
@council_required
def requests(request, pk=None, action=None):
    if request.method == "GET":
        page = max(1, int(request.GET.get("page", 1)))
        query = ReviewRequest.objects.select_related("created_by", "draft", "expense__entry", "expense__document", "quote__case", "quote__document").prefetch_related("reviews__author")
        return JsonResponse({"items": [review_data(i) for i in query[(page-1)*50:page*50]], "count": query.count(), "page": page})
    data = payload(request)
    with transaction.atomic():
        service.settings_locked()
        if pk is None:
            item = service.create_request(data.get("kind"), data["target"], request.user, data.get("proof"))
            return JsonResponse({"id": item.pk}, status=201)
        item = ReviewRequest.objects.select_for_update().get(pk=pk)
        if action == "review":
            service.review_request(item, request.user, data)
        elif action == "withdraw":
            if not (is_manager(request.user) or item.created_by_id == request.user.pk and can(request.user, PREPARE)):
                raise PermissionError("Seul le demandeur ou le syndic peut retirer la demande.")
            if item.withdrawn_at or service.consumed(item):
                raise ValueError("Ce contrôle a déjà été retiré ou utilisé.")
            item.withdrawal_reason = service.text(data.get("reason")); item.withdrawn_at = timezone.now()
            item.save(update_fields=["withdrawal_reason", "withdrawn_at"])
            if item.draft_id:
                item.draft.status = "draft"; item.draft.save(update_fields=["status"])
            service.event(request.user, "review.withdrawn", item.pk, {"reason": item.withdrawal_reason})
        else:
            raise ValueError("Action de contrôle inconnue.")
    return JsonResponse({"ok": True})


@require_http_methods(["GET", "POST", "PATCH"])
@council_required
def controls(request, pk=None, action=None):
    if request.method == "GET":
        return JsonResponse({"items": [control_data(i) for i in AccountControl.objects.select_related("year", "author").prefetch_related("evidence")[:100]]})
    require(request.user, CONTROL)
    data = payload(request)
    with transaction.atomic():
        service.settings_locked()
        item = AccountControl.objects.select_for_update().get(pk=pk) if pk else None
        if item and (item.author_id != request.user.pk or item.finalized_at):
            raise ValueError("Seul votre rapport encore en brouillon peut être complété.")
        mandate = active_mandates(request.user).filter(role="controller").first()
        if not mandate:
            raise PermissionError("Votre mandat de contrôle indépendant n’est plus actif.")
        if not item:
            year = FiscalYear.objects.get(pk=data["year"])
            item = AccountControl(year=year, author=request.user, mandate=mandate)
        if set(data) - {"year", "title", "observations", "checks", "evidence", "conclusion"}:
            raise ValueError("Champ de rapport inconnu.")
        item.title = service.text(data.get("title", item.title), 150)
        item.observations = service.text(data.get("observations", item.observations), 10000)
        checks = data.get("checks", item.checks)
        if not isinstance(checks, dict) or set(checks) - set(CHECKS) or any(not isinstance(v, bool) for v in checks.values()):
            raise ValueError("La checklist du contrôle est invalide.")
        item.checks = checks
        ids = data.get("evidence", list(item.evidence.values_list("pk", flat=True)) if item.pk else [])
        if not isinstance(ids, list) or len(ids) > 100 or any(type(i) is not int for i in ids):
            raise ValueError("Liste de pièces invalide.")
        versions = list(Version.objects.filter(pk__in=ids, document__archived=False))
        if len(versions) != len(set(ids)):
            raise ValueError("Une pièce est absente ou archivée.")
        if action == "finalize":
            conclusion = data.get("conclusion")
            if conclusion not in ["favorable", "reserves", "adverse"] or not all(checks.get(k) for k in CHECKS) or not versions:
                raise ValueError("Complétez les cinq vérifications, joignez une pièce et choisissez une conclusion.")
            if Entry.objects.filter(year=item.year, created_by=request.user).exists():
                raise ValueError("Vous avez comptabilisé des opérations de cet exercice : le contrôle doit être confié à une autre personne.")
            # Serialize with new accounting entries while capturing the reviewed state.
            FiscalYear.objects.select_for_update().get(pk=item.year_id)
            item.snapshot = service.account_snapshot(item.year)
            item.conclusion = conclusion; item.finalized_at = timezone.now()
        elif action:
            raise ValueError("Action de rapport inconnue.")
        item.full_clean(exclude=["snapshot", "finalized_at", "checks"]); item.save(); item.evidence.set(versions)
        service.event(request.user, "control.finalized" if item.finalized_at else "control.saved", item.pk, {"year": item.year_id, "conclusion": item.conclusion, "snapshot": item.snapshot, "evidence": ids})
    return JsonResponse(control_data(item), status=200 if pk else 201)


@require_http_methods(["GET"])
@council_required
def records(request):
    kind = request.GET.get("kind", "expenses")
    page = max(1, int(request.GET.get("page", 1)))
    offset, end = (page-1)*100, page*100
    year = FiscalYear.objects.get(pk=request.GET["year"]) if request.GET.get("year") else None
    if kind == "expenses":
        from finance.views import expense_data
        query = Expense.objects.select_related("document").prefetch_related("payments__entry", "payments__bank")
        if year: query = query.filter(year=year)
        rows = [expense_data(e) for e in query[offset:end]]
    elif kind == "works":
        query = Case.objects.prefetch_related("documents")
        rows = [{"id": c.pk, "title": c.title, "kind": c.get_kind_display(), "description": c.description, "status": c.get_status_display(), "budget": str(c.budget), "due_date": c.due_date,
                 "versions": [d.current_id for d in c.documents.all() if d.current_id]} for c in query[offset:end]]
    elif kind == "quotes":
        query = Quote.objects.select_related("case", "document")
        rows = [{"id": q.pk, "label": q.case.title, "supplier": q.supplier, "amount": str(q.amount), "document": q.document_id, "selected": bool(q.selected_at), "version": q.document.current_id if q.document_id else None} for q in query[offset:end]]
    elif kind in ["balance", "budget"]:
        if not year: raise ValueError("Choisissez un exercice.")
        from finance.reporting import report
        value = report(year, kind, {})
        return JsonResponse({**value, "rows": value["rows"][offset:end], "count": len(value["rows"]), "page": page})
    elif kind == "ledger":
        if not year: raise ValueError("Choisissez un exercice.")
        query = Line.objects.filter(entry__year=year).select_related("entry", "account", "owner", "supplier").order_by("entry__date", "entry__number", "id")
        rows = [{"id": l.pk, "date": l.entry.date, "number": l.entry.number, "journal": l.entry.journal, "label": l.entry.label,
                 "reference": l.entry.reference, "account": l.account.code, "owner": str(l.owner) if l.owner_id else "", "supplier": l.supplier.name if l.supplier_id else "", "debit": str(l.debit), "credit": str(l.credit)} for l in query[offset:end]]
    elif kind == "banks":
        query = BankAccount.objects.select_related("account")
        rows = [{"id": b.pk, "name": b.name, "bank_name": b.bank_name, "iban": b.iban, "account": b.account.code} for b in query[offset:end]]
    elif kind == "statements":
        query = BankStatement.objects.select_related("bank").prefetch_related("rows__matches")
        if year: query = query.filter(starts_on__lte=year.ends_on, ends_on__gte=year.starts_on)
        rows = [{"id": s.pk, "bank": s.bank.name, "starts_on": s.starts_on, "ends_on": s.ends_on,
                 "opening_balance": str(s.opening_balance), "closing_balance": str(s.closing_balance), "validated": s.validated,
                 "movements": [{"id": r.pk, "date": r.date, "label": r.label, "amount": str(r.amount), "matched": r.matches.exists()} for r in s.rows.all()]} for s in query[offset:end]]
    elif kind == "contracts":
        query = Contract.objects.select_related("supplier").prefetch_related("documents")
        rows = [{"id": c.pk, "title": c.title, "supplier": c.supplier.name, "starts_on": c.starts_on, "ends_on": c.ends_on, "reference": c.reference, "annual_cost": c.annual_cost, "status": c.status, "versions": [d.current_id for d in c.documents.all() if d.current_id]} for c in query[offset:end]]
    elif kind == "documents":
        query = Version.objects.select_related("document")
        rows = [{"id": v.pk, "title": v.document.title, "filename": v.filename, "created_at": v.created_at, "archived": v.document.archived} for v in query[offset:end]]
    elif kind == "history":
        query = CouncilEvent.objects.select_related("actor")
        rows = [{"id": e.pk, "action": e.action, "target": e.target, "actor": person(e.actor), "details": e.details, "created_at": e.created_at} for e in query[offset:end]]
    else:
        raise ValueError("Rubrique de consultation inconnue.")
    return JsonResponse({"items": rows, "count": query.count(), "page": page})


@require_http_methods(["GET"])
@council_required
def targets(request):
    require(request.user, "management.write")
    kind = request.GET.get("kind", "expense")
    page = max(1, int(request.GET.get("page", 1)))
    term = request.GET.get("q", "").strip()[:150]
    if kind == "expense":
        query = Expense.objects.select_related("document").annotate(
            paid_total=Coalesce(Sum("payments__amount", filter=Q(payments__entry__reversal__isnull=True)), Value(Decimal("0"))),
            cancelled=Exists(Entry.objects.filter(reversal_of_id=OuterRef("entry_id"))),
            has_request=Exists(ReviewRequest.objects.filter(expense_id=OuterRef("pk"), withdrawn_at__isnull=True)),
        ).filter(paid_total__lt=F("amount"), cancelled=False, has_request=False)
        if term: query = query.filter(Q(label__icontains=term) | Q(supplier__icontains=term) | Q(reference__icontains=term))
        rows = [{"id": e.pk, "label": e.label, "supplier": e.supplier, "reference": e.reference, "amount": str(e.amount)} for e in query[(page-1)*25:page*25]]
    elif kind == "quote":
        query = Quote.objects.select_related("case").filter(selected_at__isnull=True, case__status="open").annotate(has_request=Exists(ReviewRequest.objects.filter(quote_id=OuterRef("pk"), withdrawn_at__isnull=True))).filter(has_request=False)
        if term: query = query.filter(Q(case__title__icontains=term) | Q(supplier__icontains=term))
        rows = [{"id": q.pk, "label": q.case.title, "supplier": q.supplier, "reference": "", "amount": str(q.amount)} for q in query[(page-1)*25:page*25]]
    else:
        raise ValueError("Choisissez une facture ou un devis.")
    return JsonResponse({"items": rows, "count": query.count(), "page": page})


@require_http_methods(["GET"])
@council_required
def file(request, pk):
    version = Version.objects.get(pk=pk)
    try:
        stream = version.file.open("rb")
    except FileNotFoundError:
        raise Http404()
    response = FileResponse(stream, as_attachment=True, filename=version.filename, content_type=version.content_type)
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_http_methods(["POST"])
@council_required
def upload(request):
    if not (can(request.user, PREPARE) or can(request.user, CONTROL)):
        raise PermissionError("Votre responsabilité permet la consultation, sans dépôt de nouvelles pièces.")
    from documents.views import validate_upload, add_version
    title = service.text(request.POST.get("title"), 150)
    file = request.FILES.get("file")
    info = validate_upload(file)
    with transaction.atomic():
        document = Document.objects.create(title=title, published=False)
        version = add_version(document, file, info, request.user)
        service.event(request.user, "document.prepared", document.pk, {"version": version.pk, "title": title})
    return JsonResponse({"id": document.pk, "version": version.pk}, status=201)
