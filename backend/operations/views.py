from datetime import date, timedelta
from decimal import Decimal
from django import forms
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from core.views import manager_required, payload
from core.access import member_required, allow_former_owner
from core.models import Owner
from finance.views import errors
from finance.models import Line, Expense, AuditEvent
from governance.models import (
    Meeting,
    Resolution,
    AssemblyWorkflow,
    AssemblyMandate,
    AssemblyAppeal,
    AssemblyDelivery,
)
from documents.models import Document
from .models import Case, Quote, Reminder, Supplier
from .partners import contract_alerts


class CaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = [
            "kind",
            "title",
            "description",
            "due_date",
            "status",
            "budget",
            "source_url",
            "resolution",
            "documents",
        ]


class QuoteForm(forms.ModelForm):
    supplier = forms.CharField(max_length=150, required=False)

    class Meta:
        model = Quote
        fields = ["supplier", "supplier_record", "amount", "notes", "document"]

    def clean(self):
        data = super().clean()
        supplier = data.get("supplier_record")
        if supplier:
            if supplier.archived:
                self.add_error(
                    "supplier_record",
                    "Réactivez le fournisseur avant de lui ajouter un devis.",
                )
            data["supplier"] = supplier.name
        elif not data.get("supplier"):
            self.add_error(
                "supplier", "Choisissez un fournisseur ou saisissez son nom."
            )
        return data


def valid(form):
    if not form.is_valid():
        raise ValueError(" · ".join(" ".join(v) for v in form.errors.values()))
    if getattr(form, "cleaned_data", {}).get("source_url") and not form.cleaned_data[
        "source_url"
    ].startswith("https://"):
        raise ValueError("Utilisez une source HTTPS.")
    return form


def case_data(item):
    return {
        "id": item.pk,
        **{
            f: getattr(item, f)
            for f in [
                "kind",
                "title",
                "description",
                "due_date",
                "status",
                "budget",
                "source_url",
            ]
        },
        "resolution": item.resolution_id,
        "documents": [d.id for d in item.documents.all()],
        "quotes": [
            {
                "id": q.pk,
                "supplier": q.supplier,
                "supplier_record": q.supplier_record_id,
                "amount": q.amount,
                "notes": q.notes,
                "document": q.document_id,
                "selected": bool(q.selected_at),
            }
            for q in item.quotes.all()
        ],
    }


@require_http_methods(["GET", "POST"])
@manager_required
@errors
def cases(request):
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    case_data(c)
                    for c in Case.objects.prefetch_related("quotes", "documents")
                ]
            }
        )
    with transaction.atomic():
        form = valid(CaseForm(payload(request)))
        item = form.save(commit=False)
        item.created_by = request.user
        item.save()
        form.save_m2m()
        AuditEvent.objects.create(
            actor=request.user, action="case.create", target=str(item.pk)
        )
    return JsonResponse(case_data(item), status=201)


@require_http_methods(["PATCH"])
@manager_required
@errors
def case(request, pk):
    data = payload(request)
    if set(data) - set(CaseForm.Meta.fields):
        raise ValueError("Champ inconnu.")
    with transaction.atomic():
        item = Case.objects.select_for_update().get(pk=pk)
        initial = {
            f: getattr(item, f)
            for f in CaseForm.Meta.fields
            if f not in ["documents", "resolution"]
        }
        initial.update(
            documents=list(item.documents.values_list("id", flat=True)),
            resolution=item.resolution_id,
        )
        valid(CaseForm(initial | data, instance=item)).save()
        AuditEvent.objects.create(
            actor=request.user, action="case.update", target=str(item.pk)
        )
    return JsonResponse(case_data(item))


@require_http_methods(["POST"])
@manager_required
@errors
def quotes(request, pk):
    with transaction.atomic():
        item = Case.objects.select_for_update().get(pk=pk)
        if item.kind == "obligation" or item.status != "open":
            raise ValueError(
                "Ajoutez un devis à un dossier travaux ou sinistre en cours."
            )
        quote = valid(QuoteForm(payload(request))).save(commit=False)
        quote.case = item
        quote.save()
        AuditEvent.objects.create(
            actor=request.user, action="quote.create", target=str(quote.pk)
        )
    return JsonResponse({"ok": True}, status=201)


@require_http_methods(["POST"])
@manager_required
@errors
def select_quote(request, pk):
    with transaction.atomic():
        parent = Quote.objects.get(pk=pk).case_id
        item = Case.objects.select_for_update().get(pk=parent)
        if item.status != "open":
            raise ValueError("Rouvrez le dossier avant de retenir un devis.")
        quote = Quote.objects.get(pk=pk)
        selected = payload(request).get("selected", True)
        if not isinstance(selected, bool):
            raise ValueError("Choix invalide.")
        if selected and item.quotes.filter(selected_at__isnull=False).exists():
            raise ValueError("Un devis est déjà retenu dans ce dossier.")
        quote.selected_at = timezone.now() if selected else None
        quote.selected_by = request.user if selected else None
        quote.save()
        AuditEvent.objects.create(
            actor=request.user, action="quote.select", target=str(pk)
        )
    return JsonResponse({"ok": True})


def owner_lines(owner):
    return (
        Line.objects.filter(
            owner=owner,
            account__code__startswith="450",
            entry__date__lte=timezone.localdate(),
        )
        .exclude(entry__kind="carry")
        .select_related("entry")
        .order_by("entry__date", "entry__number", "id")
    )


def movement_data(owner):
    return [
        {
            "id": line.id,
            "date": str(line.entry.date),
            "number": line.entry.number,
            "label": line.entry.label,
            "debit": str(line.debit),
            "credit": str(line.credit),
        }
        for line in owner_lines(owner)
    ]


def owner_balance(owner):
    amounts = owner_lines(owner).aggregate(debit=Sum("debit"), credit=Sum("credit"))
    return (amounts["debit"] or Decimal(0)) - (amounts["credit"] or Decimal(0))


def reminder_data(r):
    return {
        "id": r.pk,
        "owner": r.owner_id,
        "name": str(r.owner),
        "email": r.owner.email,
        "balance": str(r.balance),
        "text": r.text,
        "evidence": r.evidence,
        "status": r.status,
        "created_at": r.created_at,
        "validated_at": r.validated_at,
    }


@require_http_methods(["GET", "POST"])
@manager_required
@errors
def reminders(request):
    if request.method == "GET":
        return JsonResponse(
            {
                "items": [
                    reminder_data(r) for r in Reminder.objects.select_related("owner")
                ]
            }
        )
    owner = Owner.objects.get(pk=payload(request)["owner"])
    amount = owner_balance(owner)
    if amount <= 0:
        raise ValueError("Ce copropriétaire ne présente pas de solde débiteur.")
    if Reminder.objects.filter(owner=owner, status__in=["draft", "approved"]).exists():
        raise ValueError("Une relance reste déjà à traiter pour ce copropriétaire.")
    evidence = {
        "date": str(timezone.localdate()),
        "account_prefix": "450",
        "line_ids": list(owner_lines(owner).values_list("id", flat=True)),
        "rows": movement_data(owner),
        "note": "Solde comptable, sans lettrage ni vérification des échéances : ne prouve pas à lui seul un impayé.",
    }
    with transaction.atomic():
        r = Reminder.objects.create(
            owner=owner,
            balance=amount,
            created_by=request.user,
            evidence=evidence,
            text=f'Bonjour {owner.first_name},\n\nNotre suivi comptable fait apparaître un solde débiteur de {amount:.2f} € au {evidence["date"]}. Pourriez-vous vérifier les appels de fonds et règlements correspondants ? Si vous avez déjà effectué un règlement, merci de nous en préciser la date afin que nous puissions vérifier son enregistrement.\n\nNous restons disponibles pour faire le point ensemble.\n\nLe syndic bénévole',
        )
        AuditEvent.objects.create(
            actor=request.user, action="reminder.prepare", target=str(r.pk)
        )
    return JsonResponse(reminder_data(r), status=201)


@require_http_methods(["PATCH"])
@manager_required
@errors
def reminder(request, pk):
    data = payload(request)
    with transaction.atomic():
        r = Reminder.objects.select_for_update().get(pk=pk)
        if set(data) == {"text"}:
            if r.status != "draft":
                raise ValueError("Seul un brouillon peut être modifié.")
            if (
                not isinstance(data["text"], str)
                or not data["text"].strip()
                or len(data["text"]) > 10000
            ):
                raise ValueError("Texte requis (10000 caractères maximum).")
            r.text = data["text"]
        elif set(data) == {"status"}:
            next_status = data["status"]
            if next_status == "approved" and r.status == "draft":
                if (
                    owner_balance(r.owner) != r.balance
                    or list(owner_lines(r.owner).values_list("id", flat=True))
                    != r.evidence["line_ids"]
                    or movement_data(r.owner) != r.evidence.get("rows", [])
                ):
                    raise ValueError(
                        "La comptabilité a changé. Annulez ce brouillon et préparez-en un nouveau."
                    )
                r.validated_by = request.user
                r.validated_at = timezone.now()
            elif not (
                (next_status == "sent" and r.status == "approved")
                or (next_status == "cancelled" and r.status in ["draft", "approved"])
            ):
                raise ValueError("Transition de relance invalide.")
            r.status = next_status
        else:
            raise ValueError("Modifiez le texte ou le statut séparément.")
        r.save()
        AuditEvent.objects.create(
            actor=request.user, action="reminder.update", target=f"{pk}:{r.status}"
        )
    return JsonResponse(reminder_data(r))


@require_http_methods(["GET"])
@manager_required
@errors
def options(request):
    return JsonResponse(
        {
            "owners": [{"id": o.pk, "name": str(o)} for o in Owner.objects.all()],
            "suppliers": [
                {"id": s.pk, "name": s.name, "archived": s.archived}
                for s in Supplier.objects.all()
            ],
            "documents": [
                {"id": d.pk, "title": d.title}
                for d in Document.objects.filter(archived=False)
            ],
            "resolutions": [
                {"id": r.pk, "title": f"{r.meeting.title} — {r.title}"}
                for r in Resolution.objects.select_related("meeting").filter(
                    meeting__archived=False
                )
            ],
        }
    )


@require_http_methods(["GET"])
@manager_required
@errors
def metrics(request):
    today = timezone.localdate()
    horizon = today + timedelta(days=30)
    alerts = contract_alerts(today)
    from governance.workflow import day_of, add_month
    from governance.deadlines import extend_nonworking

    for workflow in AssemblyWorkflow.objects.select_related("meeting").exclude(
        phase__in=["draft", "closed"]
    ):
        title = workflow.meeting.title
        account_year = workflow.packet.get("account_year")
        if (
            account_year
            and date.fromisoformat(account_year["approval_deadline"]) <= horizon
        ):
            alerts.append(
                {
                    "title": title,
                    "detail": f"Approbation annuelle de {account_year['name']} : échéance {account_year['approval_deadline']}.",
                    "level": (
                        "warning"
                        if date.fromisoformat(account_year["approval_deadline"]) < today
                        else "info"
                    ),
                    "page": "assemblies",
                    "section": "preparation",
                }
            )
        if workflow.phase == "convened":
            missing = (
                len(workflow.packet["electors"])
                - workflow.deliveries.filter(kind="invitation").count()
            )
            deadline = workflow.packet["latest_notification"]
            if missing:
                alerts.append(
                    {
                        "title": title,
                        "detail": f"{missing} convocation(s) sans preuve. Dernière prise d’effet : {deadline}.",
                        "level": "warning",
                        "page": "assemblies",
                        "section": "invitations",
                    }
                )
        if workflow.phase == "minutes":
            deadline = day_of(workflow.meeting) + timedelta(days=8)
            alerts.append(
                {
                    "title": title,
                    "detail": f"PV et feuille de présence à signer et conserver avant le {deadline}.",
                    "level": "warning" if deadline < today else "info",
                    "page": "assemblies",
                    "section": "minutes",
                }
            )
        if workflow.phase == "signed":
            delivered = set(
                workflow.deliveries.filter(kind="minutes").values_list(
                    "elector", flat=True
                )
            )
            missing = set(workflow.minutes["required_notifications"]) - delivered
            if missing:
                alerts.append(
                    {
                        "title": title,
                        "detail": f"{len(missing)} notification(s) de PV sans preuve. Échéance : {add_month(day_of(workflow.meeting),1)}.",
                        "level": "warning",
                        "page": "assemblies",
                        "section": "notifications",
                    }
                )
    for mandate in AssemblyMandate.objects.select_related("owner").filter(
        ends_on__gte=today, ends_on__lte=today + timedelta(days=90)
    )[:20]:
        alerts.append(
            {
                "title": "Mandat à renouveler",
                "detail": f"{mandate.owner} : fin le {mandate.ends_on}. Préparez la décision de renouvellement.",
                "level": "warning",
                "page": "assemblies",
                "section": "decisions",
            }
        )
    count = AssemblyAppeal.objects.exclude(status="resolved").count()
    if count:
        alerts.append(
            {
                "title": "Contestations à suivre",
                "detail": f"{count} recours déclaré(s) en cours.",
                "level": "info",
                "page": "assemblies",
                "section": "notifications",
            }
        )
    for delivery in AssemblyDelivery.objects.filter(kind="minutes").select_related(
        "workflow__meeting"
    ):
        deadline = extend_nonworking(
            add_month(delivery.effective_on, 2),
            delivery.workflow.packet.get("local_holidays", False),
        )
        if today <= deadline <= horizon:
            alerts.append(
                {
                    "title": delivery.workflow.meeting.title,
                    "detail": f"Délai de contestation de {delivery.recipient['name']} : jusqu’au {deadline}, selon la notification enregistrée.",
                    "level": "info",
                    "page": "assemblies",
                    "section": "notifications",
                }
            )
    for item in Case.objects.filter(status="open", due_date__lte=horizon).order_by(
        "due_date", "id"
    )[:30]:
        alerts.append(
            {
                "title": item.title,
                "detail": f"Échéance : {item.due_date}",
                "level": "warning" if item.due_date < today else "info",
                "page": "operations",
                "section": "deadlines" if item.kind == "obligation" else "works",
            }
        )
    unpaid = Decimal(0)
    for expense in Expense.objects.filter(entry__reversal__isnull=True):
        paid = expense.payments.filter(entry__reversal__isnull=True).aggregate(
            total=Sum("amount")
        )["total"] or Decimal(0)
        unpaid += max(Decimal(0), expense.amount - paid)
    if unpaid:
        alerts.append(
            {
                "title": "Factures restant à régler",
                "detail": f"{unpaid:.2f} € enregistrés, tous exercices confondus.",
                "level": "info",
                "page": "finance",
                "section": "expenses",
            }
        )
    balances = (
        Line.objects.filter(
            owner__isnull=False, account__code__startswith="450", entry__date__lte=today
        )
        .exclude(entry__kind="carry")
        .values("owner_id")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
    )
    debtor_count = sum((r["debit"] or 0) > (r["credit"] or 0) for r in balances)
    if debtor_count:
        alerts.append(
            {
                "title": "Soldes débiteurs à vérifier",
                "detail": f"{debtor_count} copropriétaire(s). Vérifiez les échéances et paiements avant toute relance.",
                "level": "warning",
                "page": "operations",
                "section": "reminders",
            }
        )
    draft_count = Reminder.objects.filter(status="draft").count()
    if draft_count:
        alerts.append(
            {
                "title": "Brouillons à relire",
                "detail": f"{draft_count} relance(s) attendent votre validation.",
                "level": "info",
                "page": "operations",
                "section": "reminders",
            }
        )
    for m in Meeting.objects.filter(
        archived=False, scheduled_at__date__gte=today, scheduled_at__date__lte=horizon
    )[:10]:
        alerts.append(
            {
                "title": m.title,
                "detail": f"AG à préparer : {timezone.localtime(m.scheduled_at).date()}",
                "level": "info",
                "page": "assemblies",
                "section": "preparation",
            }
        )
    return JsonResponse(
        {
            "date": today,
            "alerts": alerts,
            "pending_expenses": str(unpaid),
            "debtor_count": debtor_count,
            "draft_reminders": draft_count,
            "note": "Analyses déterministes des données saisies ; aucune IA ni notification extérieure.",
        }
    )


@require_http_methods(["GET"])
@member_required
@allow_former_owner
def personal_account(request):
    owner = getattr(request.user, "owner_profile", None)
    if owner is None:
        return JsonResponse({"error": "Compte copropriétaire requis."}, status=403)
    query = owner_lines(owner)
    return JsonResponse(
        {
            "balance": str(owner_balance(owner)),
            "date": timezone.localdate(),
            "rows": [
                {
                    "date": line.entry.date,
                    "label": line.entry.label,
                    "debit": str(line.debit),
                    "credit": str(line.credit),
                }
                for line in query.reverse()[:100]
            ],
            "note": "Solde comptable cumulé des comptes 450 jusqu’à aujourd’hui. Les 100 derniers mouvements sont affichés.",
        }
    )
