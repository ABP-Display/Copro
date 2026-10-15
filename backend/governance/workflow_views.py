from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from core.access import member_required
from core.views import manager_required, payload
from core.models import Owner, Lot
from documents.models import Document, Version
from finance.views import errors
from finance.idempotency import idempotent
from finance.models import (
    FiscalYear,
    ChargeKey,
    FinanceProject,
    Budget,
    Account,
    AnnualSettlement,
)
from finance.forms import CallForm
from finance.services import amount, open_year
from .models import (
    Meeting,
    Resolution,
    AssemblyWorkflow,
    AssemblyDecision,
    AssemblyMandate,
    AssemblyAppeal,
)
from . import workflow as service
from .templates import TEMPLATES
from finance.services import CHART
from .deadlines import extend_nonworking


def serialize(workflow):
    checks = []
    preview = None
    if workflow.phase == "draft":
        try:
            preview = service.build_packet(workflow)
        except (
            ValueError,
            KeyError,
            TypeError,
            Owner.DoesNotExist,
            Version.DoesNotExist,
            ChargeKey.DoesNotExist,
            FiscalYear.DoesNotExist,
        ) as error:
            checks.append(str(error))
    deliveries = [
        {
            "id": d.pk,
            "kind": d.kind,
            "elector": d.elector,
            "name": d.recipient["name"],
            "method": d.method,
            "sent_on": str(d.sent_on),
            "effective_on": str(d.effective_on),
            "reference": d.reference,
            "proof": d.proof_id,
            "appeal_until": (
                str(
                    extend_nonworking(
                        service.add_month(d.effective_on, 2),
                        workflow.packet.get("local_holidays", False),
                    )
                )
                if d.kind == "minutes"
                else None
            ),
        }
        for d in workflow.deliveries.order_by("id")
    ]
    votes = [
        {
            "id": v.pk,
            "resolution": v.resolution_id,
            "tour": v.tour,
            "created_at": v.created_at.isoformat(),
            "void_reason": v.void_reason,
            "voided": bool(v.voided_at),
            **v.data,
            "execution": (
                {"kind": v.execution.kind, "data": v.execution.data}
                if hasattr(v, "execution")
                else None
            ),
        }
        for v in workflow.votes.select_related("execution").all()
    ]
    deadlines = {}
    if workflow.packet:
        deadlines = {
            "latest_notification": workflow.packet["latest_notification"],
            "correspondence_deadline": workflow.packet["correspondence_deadline"],
            "signature_deadline": str(
                service.day_of(workflow.meeting) + service.timedelta(days=8)
            ),
            "notification_deadline": str(
                service.add_month(service.day_of(workflow.meeting), 1)
            ),
        }
    return {
        "phase": workflow.phase,
        "config": workflow.config,
        "packet": workflow.packet,
        "participants": workflow.participants,
        "bureau": workflow.bureau,
        "minutes": workflow.minutes,
        "digest": workflow.digest,
        "preview": preview,
        "checks": checks,
        "deliveries": deliveries,
        "votes": votes,
        "deadlines": deadlines,
        "events": [
            {
                "action": e.action,
                "date": e.created_at.isoformat(),
                "actor": e.actor_id,
                "data": e.data,
            }
            for e in workflow.events.order_by("id")
        ],
        "published": bool(workflow.config.get("summary_published")),
        "appeals": [
            {
                "id": a.pk,
                "elector": a.elector,
                "resolution": a.resolution_id,
                "filed_on": str(a.filed_on),
                "reference": a.reference,
                "notes": a.notes,
                "status": a.status,
                "proof": a.proof_id,
            }
            for a in workflow.appeals.all()
        ],
    }


@require_http_methods(["GET"])
@manager_required
def context(request):
    accounts = {code: name for code, name in CHART.items() if code.startswith("6")}
    for account in Account.objects.filter(code__startswith="6"):
        if account.active:
            accounts[account.code] = account.name
        else:
            accounts.pop(account.code, None)
    return JsonResponse(
        {
            "templates": TEMPLATES,
            "versions": [
                {
                    "id": v.pk,
                    "title": v.document.title,
                    "filename": v.filename,
                    "checksum": v.checksum,
                }
                for v in Version.objects.select_related("document")
                .filter(document__archived=False)
                .order_by("document__title", "-id")
            ],
            "owners": [
                {
                    "id": o.pk,
                    "name": str(o),
                    "shares": str(sum(o.lots.values_list("shares", flat=True))),
                }
                for o in Owner.objects.prefetch_related("lots")
            ],
            "keys": list(ChargeKey.objects.values("id", "name")),
            "years": [
                {
                    "id": y.pk,
                    "name": y.name,
                    "starts_on": y.starts_on,
                    "ends_on": y.ends_on,
                    "closed": y.closed,
                }
                for y in FiscalYear.objects.all()
            ],
            "projects": list(
                FinanceProject.objects.filter(completed_on__isnull=True).values(
                    "id", "name", "key_id"
                )
            ),
            "accounts": [
                {"code": code, "name": name} for code, name in sorted(accounts.items())
            ],
        }
    )


def execute_decision(workflow, user, data):
    if workflow.phase not in ["signed", "closed"]:
        raise ValueError("Le PV doit être signé avant de mettre en œuvre la décision.")
    vote = workflow.votes.get(pk=data["vote"], voided_at__isnull=True)
    if (
        not vote.data["result"]["adopted"]
        or workflow.votes.filter(
            resolution=vote.resolution, tour__gt=vote.tour, voided_at__isnull=True
        ).exists()
    ):
        raise ValueError("Choisissez le dernier vote adopté de la résolution.")
    if AssemblyDecision.objects.filter(vote=vote).exists():
        raise ValueError("La mise en œuvre a déjà été enregistrée pour ce vote.")
    service.boolean(data, "reviewed")
    reference = f"AG {workflow.meeting_id} · résolution {vote.resolution.position} · vote {vote.pk}"
    kind = data.get("kind")
    resolution = next(
        r for r in workflow.packet["resolutions"] if r["id"] == vote.resolution_id
    )
    if kind in ["syndic", "council", "fund"] and resolution["majority"] != "25":
        raise ValueError(
            "Cette mise en œuvre nécessite une résolution initialement soumise à l’article 25 (ou son second vote autorisé)."
        )
    year = (
        FiscalYear.objects.select_for_update().get(pk=data["year"])
        if kind not in ["syndic", "council"]
        else None
    )
    if year and year.closed:
        raise ValueError("L’exercice choisi est clôturé.")
    if kind == "accounts":
        from finance.cycle import apply_regularization

        item = apply_regularization(
            year,
            {
                "approved_on": str(service.day_of(workflow.meeting)),
                "decision": reference,
                "source_hash": data["source_hash"],
            },
            user,
        )
        result = {"year": year.pk, "regularization": item.pk, "reference": reference}
    elif kind in ["syndic", "council"]:
        owner = Owner.objects.get(pk=data["owner"])
        start, end = service.date.fromisoformat(
            data["starts_on"]
        ), service.date.fromisoformat(data["ends_on"])
        if (
            not owner.lots.exists()
            or start < service.day_of(workflow.meeting)
            or end <= start
            or end > service.add_month(start, 36)
        ):
            raise ValueError(
                "Choisissez un copropriétaire détenteur de lots et un mandat daté de trois ans maximum, à compter de l’AG."
            )
        result = {
            "owner": owner.pk,
            "name": str(owner),
            "starts_on": str(start),
            "ends_on": str(end),
            "reference": reference,
            "notes": service.text(data.get("notes"), 1000, False),
        }
    elif kind == "budget":
        rows = data.get("lines")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 200:
            raise ValueError("Saisissez les postes du budget adopté.")
        ids, identities = [], set()
        for row in rows:
            code = service.text(row["code"], 20)
            if (
                code not in CHART
                and not Account.objects.filter(code=code, active=True).exists()
            ):
                raise ValueError(
                    "Choisissez un compte de charges actif du plan comptable."
                )
            account, _ = Account.objects.get_or_create(
                code=code, defaults={"name": CHART.get(code, code)}
            )
            if not account.active:
                raise ValueError("Ce compte est désactivé.")
            if not account.code.startswith("6"):
                raise ValueError("Le budget détaille les comptes de charges.")
            key = ChargeKey.objects.get(pk=row["key"])
            identity = (account.pk, key.pk)
            if identity in identities:
                raise ValueError(
                    "Un poste et une clé ne peuvent apparaître deux fois dans le budget adopté."
                )
            identities.add(identity)
            if Budget.objects.filter(
                year=year, account=account, cost_center__isnull=True, key__isnull=True
            ).exists():
                raise ValueError(
                    "Retirez d’abord le budget global du poste pour éviter une double prévision."
                )
            item, _ = Budget.objects.update_or_create(
                year=year,
                account=account,
                key=key,
                cost_center=None,
                defaults={
                    "amount": amount(row["amount"], False),
                    "variance_note": reference,
                },
            )
            ids.append(item.pk)
        result = {
            "year": year.pk,
            "budgets": ids,
            "lines": rows,
            "reference": reference,
        }
    elif kind in ["current", "works", "fund", "advance"]:
        key = ChargeKey.objects.get(pk=data["key"])
        project = None
        if kind == "works":
            project = FinanceProject.objects.create(
                name=service.text(data.get("label"), 150),
                key=key,
                budget=amount(data["amount"]),
                decision=reference,
                decided_on=service.day_of(workflow.meeting),
            )
        count = int(data.get("count", 4))
        if not 1 <= count <= 12:
            raise ValueError("Choisissez de 1 à 12 échéances.")
        start = service.date.fromisoformat(data["date"])
        spacing = int(data.get("months", 3))
        if not 1 <= spacing <= 12:
            raise ValueError("L’espacement doit être de 1 à 12 mois.")
        total = amount(data["amount"])
        cents = int(total * 100)
        ids = []
        for index in range(count):
            due = service.add_month(start, index * spacing)
            if not year.starts_on <= due <= year.ends_on:
                raise ValueError(
                    "Toutes les échéances doivent appartenir à l’exercice choisi."
                )
            form = CallForm(
                {
                    "year": year.pk,
                    "key": key.pk,
                    "label": f"{service.text(data.get('label'), 140)} {index+1}/{count}",
                    "date": due.isoformat(),
                    "due_date": due.isoformat(),
                    "amount": str(
                        service.Decimal(cents // count + (index < cents % count)) / 100
                    ),
                    "kind": kind,
                    "advance_type": data.get('advance_type','reserve'),
                    "project": project.pk if project else "",
                    "decision": reference,
                }
            )
            if not form.is_valid():
                raise ValueError(" · ".join(" ".join(v) for v in form.errors.values()))
            ids.append(form.save().pk)
        result = {
            "year": year.pk,
            "calls": ids,
            "project": project.pk if project else None,
            "reference": reference,
            "note": "Brouillons à contrôler avant publication. Aucun envoi ni mouvement bancaire.",
        }
    else:
        raise ValueError("Choisissez une mise en œuvre proposée.")
    decision = AssemblyDecision.objects.create(
        vote=vote, kind=kind, data=result, created_by=user
    )
    if kind in ["syndic", "council"]:
        AssemblyMandate.objects.create(
            decision=decision,
            owner=owner,
            kind=kind,
            starts_on=start,
            ends_on=end,
            notes=result["notes"],
        )
    service.event(workflow, user, "execute", result)


@require_http_methods(["GET", "POST"])
@manager_required
@errors
@idempotent
def workflow(request, pk, action=None):
    with transaction.atomic():
        meeting = Meeting.objects.select_for_update().get(pk=pk)
        item, _ = AssemblyWorkflow.objects.get_or_create(meeting=meeting)
        if request.method == "GET":
            return JsonResponse(serialize(item))
        data = payload(request)
        if meeting.archived and item.phase != 'closed':
            raise ValueError('Restaurez cette préparation archivée avant de poursuivre le parcours.')
        if action == "configure":
            service.ensure_draft(meeting)
            config = data.get("config")
            if not isinstance(config, dict) or len(str(config)) > 200000:
                raise ValueError("Configuration du dossier invalide.")
            for field in ["contacts", "resolutions"]:
                mapping = config.get(field, {})
                if not isinstance(mapping, dict) or any(
                    not isinstance(value, dict) for value in mapping.values()
                ):
                    raise ValueError(
                        "Les destinataires et paramètres de résolution doivent être des objets."
                    )
            for settings in config.get("resolutions", {}).values():
                pieces = settings.get("pieces", [])
                if (
                    not isinstance(pieces, list)
                    or len(pieces) > 50
                    or any(not isinstance(piece, dict) for piece in pieces)
                ):
                    raise ValueError("Liste de pièces invalide.")
            config.pop("summary_published", None)
            item.config = config
            item.save(update_fields=["config"])
            service.event(item, request.user, "configure")
        elif action == "freeze":
            service.freeze(item, request.user)
        elif action == "delivery":
            service.register_delivery(item, request.user, data)
        elif action == "participants":
            service.set_participants(item, request.user, data)
        elif action == "start":
            service.start_session(item, request.user, data)
        elif action == "vote":
            service.record_vote(item, request.user, data)
        elif action == "void-vote":
            service.void_vote(item, request.user, data)
        elif action == "minutes":
            service.prepare_minutes(item, request.user, data)
        elif action == "revise-minutes":
            if item.phase != "minutes":
                raise ValueError(
                    "Un PV signé ne se réécrit pas ; conservez un additif dans les documents."
                )
            reason = service.text(data.get("reason"), 500)
            service.event(
                item,
                request.user,
                "revise_minutes",
                {"previous": item.minutes, "reason": reason},
            )
            item.minutes = {}
            item.phase = "session"
            item.save(update_fields=["minutes", "phase"])
        elif action == "sign":
            service.sign_minutes(item, request.user, data)
        elif action == "close":
            service.close_assembly(item, request.user, data)
        elif action == "publish":
            if item.phase not in ["signed", "closed"] or not isinstance(
                data.get("published"), bool
            ):
                raise ValueError("Seul un résumé de PV signé peut être partagé.")
            item.config = {**item.config, "summary_published": data["published"]}
            item.save(update_fields=["config"])
            service.event(
                item, request.user, "publish", {"published": data["published"]}
            )
        elif action == "execute":
            execute_decision(item, request.user, data)
        elif action == "appeal":
            if item.phase not in ["signed", "closed"]:
                raise ValueError("Le suivi d’un recours nécessite un PV signé.")
            elector = data.get("elector")
            if elector not in {e["elector"] for e in item.packet["electors"]}:
                raise ValueError("Copropriétaire absent du dossier.")
            resolution = item.meeting.resolutions.get(pk=data["resolution"])
            day = service.date.fromisoformat(data["filed_on"])
            if not service.day_of(meeting) <= day <= timezone.localdate():
                raise ValueError("Indiquez la date réelle du recours après l’AG.")
            service.evidence(item, data["proof"])
            appeal = AssemblyAppeal.objects.create(
                workflow=item,
                elector=elector,
                resolution=resolution,
                filed_on=day,
                reference=service.text(data.get("reference"), 250),
                notes=service.text(data.get("notes"), 5000, False),
                proof_id=data["proof"],
                created_by=request.user,
            )
            service.event(
                item,
                request.user,
                "appeal",
                {"id": appeal.pk, "reference": appeal.reference},
            )
        elif action == "appeal-update":
            appeal = item.appeals.get(pk=data["appeal"])
            if data.get("status") not in ["filed", "ongoing", "resolved"]:
                raise ValueError("État du recours inconnu.")
            previous = {"status": appeal.status, "notes": appeal.notes}
            appeal.status = data["status"]
            appeal.notes = service.text(data.get("notes"), 5000, False)
            appeal.save(update_fields=["status", "notes"])
            service.event(
                item,
                request.user,
                "appeal_update",
                {
                    "id": appeal.pk,
                    "previous": previous,
                    "status": appeal.status,
                    "notes": appeal.notes,
                },
            )
        else:
            raise ValueError("Action d’assemblée inconnue.")
        return JsonResponse(serialize(item))


@require_http_methods(["GET"])
@member_required
def summaries(request):
    query = AssemblyWorkflow.objects.filter(
        phase__in=["signed", "closed"], config__summary_published=True
    ).select_related("meeting")
    return JsonResponse(
        {
            "items": [
                {
                    "id": w.meeting_id,
                    "title": w.minutes["title"],
                    "date": w.minutes["scheduled_at"],
                    "resolutions": [
                        {
                            "title": r["resolution"]["title"],
                            "text": r["votes"][-1].get("amendment")
                            or r["resolution"]["text"],
                            "adopted": r["adopted"],
                            "result": r["votes"][-1]["result"],
                        }
                        for r in w.minutes["resolutions"]
                    ],
                }
                for w in query
            ]
        }
    )
