from functools import wraps
from uuid import UUID
from django.db import transaction
from django.http import JsonResponse
import json
from core.views import payload
from .models import OperationTicket


def idempotent(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method == "GET" or "preview-mutation" in request.path:
            return view(request, *args, **kwargs)
        data = payload(request)
        if not data.get("request_id"):
            return view(request, *args, **kwargs)
        from .cycle import digest

        request_id = UUID(str(data["request_id"]))
        source_hash = digest(data)
        with transaction.atomic():
            ticket, created = OperationTicket.objects.get_or_create(
                request_id=request_id,
                defaults={
                    "actor": request.user,
                    "path": request.path,
                    "source_hash": source_hash,
                },
            )
            ticket = OperationTicket.objects.select_for_update().get(pk=ticket.pk)
            if not created:
                if (
                    ticket.actor_id != request.user.pk
                    or ticket.path != request.path
                    or ticket.source_hash != source_hash
                ):
                    raise ValueError(
                        "Cet identifiant d’opération a déjà été utilisé avec d’autres données."
                    )
                if ticket.response is None:
                    raise ValueError(
                        "Opération en cours ; réessayez avec le même identifiant."
                    )
                return JsonResponse(ticket.response, status=ticket.status)
            response = view(request, *args, **kwargs)
            if response.status_code >= 400:
                transaction.set_rollback(True)
            else:
                ticket.response = json.loads(response.content)
                ticket.status = response.status_code
                ticket.save(update_fields=["response", "status"])
            return response

    return wrapped
