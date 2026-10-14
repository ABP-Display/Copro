from django import forms

from django.db import transaction

from django.http import JsonResponse

from django.views.decorators.http import require_http_methods

from core.views import manager_required, payload

from finance.views import errors

from finance.models import AuditEvent

from .models import Meeting, Resolution

from .roster import normalize_roster

from core.models import Owner, Lot

from django.db.models import Sum

from .calculations import vote_result, split_result, installment_result
from .workflow import ensure_draft


class MeetingForm(forms.ModelForm):

    class Meta:

        model = Meeting
        fields = ["title", "scheduled_at", "location", "notes"]


class ResolutionForm(forms.ModelForm):

    class Meta:

        model = Resolution
        fields = ["position", "title", "text", "majority", "notes"]


def resolution_data(item):

    return {
        "id": item.pk,
        "meeting": item.meeting_id,
        "position": item.position,
        "title": item.title,
        "text": item.text,
        "majority": item.majority,
        "notes": item.notes,
        "analysis": item.analysis,
    }


def meeting_data(item):

    return {
        "id": item.pk,
        "title": item.title,
        "scheduled_at": item.scheduled_at,
        "location": item.location,
        "notes": item.notes,
        "archived": item.archived,
        "roster": item.roster,
        "phase": item.workflow.phase if hasattr(item, "workflow") else "draft",
        "resolutions": [resolution_data(r) for r in item.resolutions.all()],
    }


def validate(form):

    if not form.is_valid():
        raise ValueError(
            " · ".join(" ".join(errors) for errors in form.errors.values())
        )

    return form


@require_http_methods(["GET", "POST"])
@manager_required
@errors
def meetings(request):

    if request.method == "GET":

        query = Meeting.objects.prefetch_related("resolutions")

        if request.GET.get("archived") != "1":
            query = query.filter(archived=False)

        return JsonResponse({"items": [meeting_data(m) for m in query]})

    data = payload(request)

    if any(isinstance(v, (dict, list)) for v in data.values()):
        raise ValueError("Champs simples attendus.")

    with transaction.atomic():

        item = validate(MeetingForm(data)).save(commit=False)
        item.created_by = request.user
        item.save()

        AuditEvent.objects.create(
            actor=request.user, action="meeting.create", target=str(item.pk)
        )

    return JsonResponse(meeting_data(item), status=201)


@require_http_methods(["PATCH"])
@manager_required
@errors
def meeting(request, pk):

    data = payload(request)

    with transaction.atomic():

        item = Meeting.objects.select_for_update().get(pk=pk)
        ensure_draft(item)

        if set(data) == {"archived"}:

            if not isinstance(data["archived"], bool):
                raise ValueError("Valeur d’archivage invalide.")

            item.archived = data["archived"]
            item.save(update_fields=["archived"])

        elif set(data) == {"roster"}:

            if item.archived:
                raise ValueError("Cette assemblée est archivée.")

            item.roster = normalize_roster(data["roster"])
            item.save(update_fields=["roster"])

        else:

            if item.archived:
                raise ValueError("Restaurez cette assemblée avant de la modifier.")

            if set(data) - set(MeetingForm.Meta.fields):
                raise ValueError("Champ inconnu.")

            initial = {field: getattr(item, field) for field in MeetingForm.Meta.fields}

            validate(MeetingForm(initial | data, instance=item)).save()

        AuditEvent.objects.create(
            actor=request.user, action="meeting.update", target=str(item.pk)
        )

    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
@manager_required
@errors
def resolutions(request, pk):

    data = payload(request)

    with transaction.atomic():

        meeting = Meeting.objects.select_for_update().get(pk=pk)
        ensure_draft(meeting)

        if meeting.archived:
            raise ValueError("Cette assemblée est archivée.")

        form = validate(ResolutionForm(data))
        item = form.save(commit=False)
        item.meeting = meeting
        item.save()

        AuditEvent.objects.create(
            actor=request.user, action="resolution.create", target=str(item.pk)
        )

    return JsonResponse(resolution_data(item), status=201)


@require_http_methods(["PATCH"])
@manager_required
@errors
def resolution(request, pk):

    data = payload(request)

    with transaction.atomic():

        parent = Resolution.objects.get(pk=pk).meeting_id

        meeting = Meeting.objects.select_for_update().get(pk=parent)
        ensure_draft(meeting)

        if meeting.archived:
            raise ValueError("Cette assemblée est archivée.")

        item = Resolution.objects.select_for_update().get(pk=pk)

        if set(data) - set(ResolutionForm.Meta.fields):
            raise ValueError("Champ inconnu.")

        initial = {field: getattr(item, field) for field in ResolutionForm.Meta.fields}

        form = validate(ResolutionForm(initial | data, instance=item))

        item = form.save(commit=False)
        item.analysis = None
        item.save()

        AuditEvent.objects.create(
            actor=request.user, action="resolution.update", target=str(item.pk)
        )

    return JsonResponse(resolution_data(item))


@require_http_methods(["POST"])
@manager_required
@errors
def simulate(request, pk):

    data = payload(request)

    with transaction.atomic():

        parent = Resolution.objects.get(pk=pk).meeting_id

        meeting = Meeting.objects.select_for_update().get(pk=parent)
        ensure_draft(meeting)

        if meeting.archived:
            raise ValueError("Cette assemblée est archivée.")

        item = Resolution.objects.select_for_update().get(pk=pk)

        if data.get("mode", "first") != "first":

            if not item.analysis:
                raise ValueError("Enregistrez d’abord le premier vote.")

            expected = {"25": "25-1", "26": "26-1"}.get(item.majority)

            if data.get("mode") != expected:
                raise ValueError("Passerelle incohérente avec la résolution.")

            if item.analysis["input"].get("mode", "first") != "first":
                raise ValueError(
                    "Le second vote est déjà enregistré ; aucun enchaînement de passerelles n’est autorisé."
                )

            data["initial"] = item.analysis["input"]

        else:
            data["rule"] = item.majority

        result = vote_result(data)

        history = item.analysis if data.get("mode", "first") != "first" else None

        item.analysis = {"input": data, "result": result, "first_vote": history}
        item.save(update_fields=["analysis"])

        AuditEvent.objects.create(
            actor=request.user, action="resolution.simulate", target=str(item.pk)
        )

    return JsonResponse(item.analysis)


@require_http_methods(["POST"])
@manager_required
@errors
def tools(request, kind):

    data = payload(request)

    functions = {
        "vote": vote_result,
        "split": split_result,
        "installments": installment_result,
    }

    if kind not in functions:
        raise ValueError("Outil inconnu.")

    return JsonResponse(functions[kind](data))


@require_http_methods(["GET"])
@manager_required
@errors
def electorate(request):

    owners = Owner.objects.annotate(voting_shares=Sum("lots__shares"))

    return JsonResponse(
        {
            "items": [
                {
                    "owner_id": o.pk,
                    "name": str(o),
                    "shares": str(o.voting_shares or 0),
                    "attendance": "absent",
                    "vote": "pending",
                }
                for o in owners
            ],
            "unassigned_lots": Lot.objects.filter(owner__isnull=True).count(),
        }
    )
