from datetime import date
from decimal import Decimal
import secrets
import hashlib
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from core.models import Owner
from documents.models import Version
from finance.models import AuditEvent, Expense, Entry, FiscalYear
from finance.services import amount
from governance.models import AssemblyMandate
from operations.models import Quote
from .models import CouncilSettings, Mandate, ExternalAccess, ReviewRequest, Review, ExpenseDraft, CouncilEvent
from .access import active_mandates, can, is_manager, REVIEW


def text(value, limit=1000, required=True):
    if not isinstance(value, str) or len(value.strip()) > limit or (required and not value.strip()):
        raise ValueError(f"Texte requis, limité à {limit} caractères." if required else f"Texte limité à {limit} caractères.")
    return value.strip()


def day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError("Renseignez une date complète au format année-mois-jour.") from None


def event(user, action, target, details=None):
    CouncilEvent.objects.create(actor=user, action=action, target=str(target), details=details or {})
    AuditEvent.objects.create(actor=user, action="council." + action, target=str(target))


def settings_locked():
    CouncilSettings.objects.get_or_create(pk=1)
    return CouncilSettings.objects.select_for_update().get(pk=1)


def create_mandate(data, actor):
    """Caller locks the singleton: competing grants and revocations serialize."""
    config = settings_locked()
    role = data.get("role")
    if role not in Mandate.Role.values:
        raise ValueError("Choisissez une responsabilité proposée.")
    if data.get("eligibility_confirmed") is not True:
        raise ValueError("Confirmez l’éligibilité et la décision de désignation.")
    start, end = day(data.get("starts_on")), day(data.get("ends_on"))
    if end < start:
        raise ValueError("La fin doit suivre le début du mandat.")
    reference = text(data.get("reference"))
    owner = Owner.objects.select_related("user").get(pk=data["owner"]) if data.get("owner") else None
    credentials = None
    if owner:
        if not owner.user_id or not owner.user.is_active or not owner.email:
            raise ValueError("Créez ou réactivez d’abord l’accès de cette personne dans l’annuaire.")
        user = owner.user
    elif role == "controller" and data.get("user"):
        user = get_user_model().objects.get(pk=data["user"], is_active=True)
        owner = getattr(user, "owner_profile", None)
    elif role == "controller" and data.get("external_email"):
        email = text(data["external_email"], 254).lower()
        validate_email(email)
        if get_user_model().objects.filter(email__iexact=email).exists() or Owner.objects.filter(email__iexact=email).exists():
            raise ValueError("Ce courriel existe déjà : choisissez le compte correspondant.")
        name = text(data.get("external_name"), 150)
        password = secrets.token_urlsafe(18)
        user = get_user_model().objects.create_user(username="controller-" + secrets.token_hex(16), email=email, first_name=name, password=password)
        ExternalAccess.objects.create(user=user)
        credentials = {"email": email, "temporary_password": password}
    else:
        raise ValueError("Choisissez un copropriétaire avec accès ; un contrôleur peut aussi utiliser un compte externe.")
    if role != "controller" and (not owner or not owner.lots.exists()):
        raise ValueError("Ce parcours exige un copropriétaire détenteur de lots.")
    if role == "syndic" and config.mode != "benevole" or role == "coop_syndic" and config.mode != "cooperative":
        raise ValueError("La responsabilité doit correspondre au mode de gestion configuré.")
    if role == "president" and config.mode == "cooperative":
        raise ValueError("En mode coopératif, utilisez la responsabilité réunissant président du conseil et syndic.")
    if role in ["syndic", "coop_syndic", "council", "president", "vice"]:
        from governance.workflow import add_month
        if end > add_month(start, 36):
            raise ValueError("Ce mandat ne peut pas dépasser trois ans dans ce parcours.")
    authority = data.get("authority")
    expected = "council" if role in ["coop_syndic", "president", "vice"] else "organisation" if role == "treasurer" else "ag"
    if authority != expected:
        raise ValueError("Choisissez la décision de l’AG, du conseil ou l’organisation interne correspondant à cette responsabilité.")
    proof = Version.objects.get(pk=data["proof"]) if data.get("proof") else None
    source = AssemblyMandate.objects.select_related("decision__vote__workflow", "owner").get(pk=data["assembly_mandate"]) if data.get("assembly_mandate") else None
    if source:
        expected_role = "syndic" if source.kind == "syndic" else "council"
        if role != expected_role or source.owner_id != getattr(owner, "pk", None) or start != source.starts_on or end != source.ends_on:
            raise ValueError("La personne, les dates et la responsabilité doivent reprendre le mandat issu de l’AG.")
        workflow = source.decision.vote.workflow
        if workflow.phase not in ["signed", "closed"]:
            raise ValueError("Le PV source doit être signé.")
        proof = Version.objects.get(pk=workflow.minutes["signed_proof"]["id"])
    if role != "treasurer" and not proof:
        raise ValueError("Rattachez la version du PV ou du document de désignation.")
    if proof and proof.document.archived:
        raise ValueError("Restaurez la pièce de désignation avant de l’utiliser.")
    seat = Mandate.objects.get(pk=data["seat"]) if data.get("seat") else None
    if role in ["coop_syndic", "president", "vice"]:
        if not seat or seat.role != "council" or seat.user_id != user.pk or seat.revoked_at or seat.starts_on > start or seat.ends_on < end:
            raise ValueError("Rattachez un mandat de membre du conseil couvrant toute la période.")
    elif seat:
        raise ValueError("Un mandat support n’est prévu que pour la présidence et la vice-présidence.")
    overlapping = Mandate.objects.filter(revoked_at__isnull=True, starts_on__lte=end, ends_on__gte=start)
    own = overlapping.filter(user=user)
    if own.filter(role=role).exists():
        raise ValueError("Cette responsabilité existe déjà sur une période qui se recoupe.")
    if role == "controller" and (user.is_staff or user.is_superuser or own.exclude(role="controller").exists()) or role != "controller" and own.filter(role="controller").exists():
        raise ValueError("Le contrôle indépendant ne peut pas être cumulé avec la gestion ou les fonctions du conseil sur cette période.")
    if role in ["syndic", "coop_syndic", "president"] and overlapping.filter(role=role).exists():
        raise ValueError("Un titulaire exerce déjà cette responsabilité sur la période ; terminez son mandat avant la passation.")
    mandate = Mandate.objects.create(user=user, owner=owner, role=role, starts_on=start, ends_on=end, authority=authority, reference=reference, proof=proof, assembly_mandate=source, seat=seat, eligibility_confirmed=True, created_by=actor)
    event(actor, "mandate.granted", mandate.pk, {"user": user.pk, "role": role, "starts_on": str(start), "ends_on": str(end), "reference": reference, "proof": proof.pk if proof else None})
    return mandate, credentials


def expense_snapshot(item):
    return {"id": item.pk, "label": item.label, "amount": str(item.amount), "supplier": item.supplier, "supplier_record": item.supplier_record_id,
            "reference": item.reference, "date": str(item.date), "due_date": str(item.due_date) if item.due_date else None, "year": item.year_id, "key": item.key_id,
            "project": item.project_id, "entry": item.entry_id, "document": item.document_id,
            "version": item.document.current_id if item.document_id else None}


def target_snapshot(kind, target):
    if kind == "expense":
        return expense_snapshot(target)
    if kind == "draft":
        result = dict(target.data)
        result["version"] = target_document(target).current_id if target.data.get("document") else None
        return result
    return {"id": target.pk, "label": target.case.title, "case": target.case_id, "supplier": target.supplier, "supplier_record": target.supplier_record_id,
            "amount": str(target.amount), "notes": target.notes, "document": target.document_id, "version": target.document.current_id if target.document_id else None}


def target_document(draft):
    from documents.models import Document
    return Document.objects.get(pk=draft.data["document"])


def request_target(item):
    return item.draft if item.kind == "draft" else item.quote if item.kind == "quote" else item.expense


def request_state(item):
    if item.withdrawn_at:
        return "withdrawn"
    if target_snapshot(item.kind, request_target(item)) != item.snapshot:
        return "stale"
    reviews = list(item.reviews.all())
    if any(r.decision == "rejected" for r in reviews):
        return "rejected"
    return "approved" if sum(r.decision == "approved" for r in reviews) >= required_reviews(item) else "pending"


def required_reviews(item):
    config = CouncilSettings.objects.filter(pk=1).first()
    minimum = item.required_approvals
    if config and config.approval_enabled and Decimal(item.snapshot["amount"]) >= config.threshold:
        minimum = max(minimum, config.required_approvals)
    return minimum


def consumed(item):
    if item.draft_id and item.draft.expense_id or item.quote_id and item.quote.selected_at:
        return True
    return bool(item.expense_id and item.expense.payments.filter(entry__reversal__isnull=True, entry__created_at__gte=item.created_at).exists())


def create_request(kind, pk, user, proof_pk=None):
    config = settings_locked()
    model = {"expense": Expense, "quote": Quote, "draft": ExpenseDraft}.get(kind)
    if not model:
        raise ValueError("Choisissez une facture, un devis ou une préparation.")
    target = model.objects.select_for_update().get(pk=pk)
    if kind == "draft":
        if target.status != "draft" or not (is_manager(user) or target.created_by_id == user.pk):
            raise ValueError("Cette préparation ne peut pas être soumise.")
        if not can(user, "expense.prepare"):
            raise PermissionError("Votre mandat ne permet plus de préparer une dépense.")
    elif not is_manager(user):
        raise PermissionError("Seul le syndic soumet une facture ou un devis.")
    if kind == "expense":
        from django.db.models import Sum
        paid = target.payments.filter(entry__reversal__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        if paid >= target.amount or Entry.objects.filter(reversal_of_id=target.entry_id).exists():
            raise ValueError("Cette facture est déjà entièrement réglée ou annulée.")
    if kind == "quote" and (target.selected_at or target.case.status != "open"):
        raise ValueError("Choisissez un devis non retenu dans un dossier ouvert.")
    if ReviewRequest.objects.filter(**{kind: target}, withdrawn_at__isnull=True).exists():
        raise ValueError("Une demande existe déjà. Retirez-la avec un motif avant de la remplacer.")
    snapshot = target_snapshot(kind, target)
    if not (proof_pk or snapshot.get("version")):
        raise ValueError("Joignez la version de la facture, du devis ou d’un justificatif avant de demander le contrôle.")
    proof = Version.objects.get(pk=proof_pk or snapshot.get("version"))
    if proof.document.archived:
        raise ValueError("Restaurez la pièce avant de soumettre le dossier.")
    result = ReviewRequest.objects.create(kind=kind, **{kind: target}, snapshot=snapshot, proof=proof, required_approvals=config.required_approvals, created_by=user)
    if kind == "draft":
        target.status = "submitted"
        target.save(update_fields=["status"])
    event(user, "review.requested", result.pk, {"kind": kind, "target": pk, "snapshot": snapshot, "proof": proof.pk, "required_approvals": result.required_approvals})
    return result


def review_request(item, user, data):
    if not can(user, REVIEW):
        raise PermissionError("Un membre du conseil indépendant de la gestion doit donner l’avis.")
    target = request_target(item)
    authors = {item.created_by_id}
    if item.expense_id:
        authors.add(item.expense.entry.created_by_id)
    if item.draft_id:
        authors.add(item.draft.created_by_id)
    if item.quote_id:
        authors.add(item.quote.case.created_by_id)
    if user.pk in authors:
        raise ValueError("Vous ne pouvez pas contrôler votre propre préparation.")
    if consumed(item) or request_state(item) not in ["pending", "approved"]:
        raise ValueError("Cette demande n’accepte plus d’avis. Retirez et soumettez à nouveau un dossier corrigé si nécessaire.")
    decision = data.get("decision")
    if decision not in ["approved", "rejected"]:
        raise ValueError("Choisissez un avis favorable ou un refus.")
    if item.reviews.filter(author=user).exists():
        raise ValueError("Votre avis est déjà conservé. Il ne peut pas être réécrit.")
    mandate = active_mandates(user).filter(role__in=["council", "president", "vice"]).first()
    if not mandate:
        raise PermissionError("Votre mandat de conseil n’est plus actif.")
    result = Review.objects.create(request=item, author=user, mandate=mandate, decision=decision, reason=text(data.get("reason"), 2000))
    event(user, "review." + decision, item.pk, {"review": result.pk, "mandate": mandate.pk, "reason": result.reason})


def ensure_approved(kind, target):
    """A payment or quote selection locks settings and its request in its transaction."""
    config = settings_locked()
    item = ReviewRequest.objects.select_for_update().filter(**{kind: target}, withdrawn_at__isnull=True).first()
    if item is None:
        if not config.approval_enabled or target.amount < config.threshold:
            return
        raise ValueError("Contrôle du conseil requis : soumettez ce dossier dans Conseil syndical → Dépenses à valider.")
    if request_state(item) != "approved":
        raise ValueError("Le conseil doit valider ce dossier à jour avant de continuer.")
    # Raising the configured quorum also applies to pending operations; lowering it cannot erase an existing request.
    minimum = max(item.required_approvals, config.required_approvals if config.approval_enabled and target.amount >= config.threshold else 1)
    if item.reviews.filter(decision="approved").count() < minimum:
        raise ValueError(f"Le contrôle exige {minimum} avis favorables distincts.")
    if kind == "expense" and item.kind == "draft" and expense_snapshot(target) != item.posted_snapshot:
        raise ValueError("La facture ne correspond plus à la préparation contrôlée.")


def account_snapshot(year):
    from finance.models import Line, Budget, ChargeAllocation, BankStatement, BankMatch
    from django.db.models import Sum
    entries = Entry.objects.filter(year=year)
    totals = Line.objects.filter(entry__year=year).aggregate(debit=Sum("debit"), credit=Sum("credit"))
    details = {
        "lines": list(Line.objects.filter(entry__year=year).order_by("id").values("id", "entry_id", "account_id", "debit", "credit", "owner_id", "supplier_id", "key_id", "project_id", "lot_id", "due_date")),
        "budgets": list(Budget.objects.filter(year=year).order_by("id").values()),
        "allocations": list(ChargeAllocation.objects.filter(line__entry__year=year).order_by("id").values()),
        "statements": list(BankStatement.objects.filter(starts_on__lte=year.ends_on, ends_on__gte=year.starts_on).order_by("id").values()),
        "matches": list(BankMatch.objects.filter(line__entry__year=year).order_by("id").values()),
        "invoice_versions": [expense_snapshot(e) for e in Expense.objects.select_related("document").filter(year=year).order_by("id")],
    }
    digest = hashlib.sha256(json.dumps(details, cls=DjangoJSONEncoder, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"year": year.pk, "closed": FiscalYear.objects.get(pk=year.pk).closed, "entries": list(entries.order_by("id").values_list("id", flat=True)), "digest": digest,
            "debit": str(totals["debit"] or Decimal("0")), "credit": str(totals["credit"] or Decimal("0")),
            "expenses": list(Expense.objects.filter(year=year).order_by("id").values_list("id", flat=True))}
