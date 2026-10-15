import json
from functools import wraps
from django.contrib.auth import authenticate, logout
from django.db import connection, transaction, IntegrityError
from django.db.models import Count, Sum
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from .forms import OwnerForm, LotForm
from .models import Owner, Lot
from .access import user_data, member_required, provision_access, password_pending, is_manager, active_mandates
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


def csrf_failure(request, reason=""):
    return JsonResponse({"error": "Session expirée. Actualisez la page puis réessayez."}, status=403)


def manager_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Connexion nécessaire."}, status=401)
        if not is_manager(request.user):
            return JsonResponse({"error": "Accès réservé aux gestionnaires."}, status=403)
        owner=getattr(request.user,"owner_profile",None)
        if password_pending(request.user):
            return JsonResponse({"error":"Changez votre mot de passe avant d’accéder à la gestion.","code":"password_change_required"},status=403)
        return view(request, *args, **kwargs)
    return wrapped


def payload(request):
    try:
        value = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("Le contenu JSON est invalide.")
    if not isinstance(value, dict):
        raise ValueError("Un objet JSON est attendu.")
    return value


def owner_data(owner):
    return {"id": owner.pk, "first_name": owner.first_name, "last_name": owner.last_name,
            "email": owner.email, "phone": owner.phone, "lots_count": owner.lots.count(),
            "has_access": bool(owner.user_id), "access_active": bool(owner.user_id and owner.user.is_active), "must_change_password": owner.must_change_password}


def lot_data(lot):
    return {"id": lot.pk, "number": lot.number, "kind": lot.kind, "floor": lot.floor,
            "area": str(lot.area) if lot.area is not None else "", "shares": str(lot.shares),
            "owner": lot.owner_id, "owner_name": str(lot.owner) if lot.owner else ""}


@require_GET
def health(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"status": "ok"})


@require_GET
def session(request):
    user = request.user
    organization = None
    if user.is_authenticated:
        from finance.models import Organization
        item, _ = Organization.objects.get_or_create(pk=1)
        organization = {"id": item.pk, "name": item.name}
    return JsonResponse({"csrfToken": get_token(request), "user": user_data(user) if user.is_authenticated else None, "organization": organization})


@require_POST
def sign_in(request):
    from safety.authentication import charge_attempt, establish_session
    from safety.models import Credential
    from django.utils import timezone
    try:
        data = payload(request)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return JsonResponse({"error": "Identifiant et mot de passe requis."}, status=400)
    # Do not trust X-Forwarded-For from arbitrary clients. The account bucket is
    # shared across every IP, session and application worker.
    if not charge_attempt("login-ip", request.META.get("REMOTE_ADDR", ""), limit=100, seconds=600):
        return JsonResponse({"error": "Trop de tentatives de connexion. Réessayez dans dix minutes."}, status=429)
    linked = Owner.objects.select_related("user").filter(email__iexact=username.strip()).exclude(email="").first()
    login_name = linked.user.username if linked and linked.user_id else username.strip()
    if not linked:
        external = get_user_model().objects.filter(email__iexact=username.strip(), council_identity__isnull=False).first()
        if external:
            login_name = external.username
    if not charge_attempt("login-account", login_name.casefold()[:254], limit=10, seconds=600):
        return JsonResponse({"error": "Trop de tentatives de connexion. Réessayez dans dix minutes."}, status=429)
    user = authenticate(request, username=login_name, password=password)
    if user is None:
        return JsonResponse({"error": "Identifiant ou mot de passe incorrect."}, status=401)
    if not is_manager(user) and not getattr(user, "owner_profile", None) and not active_mandates(user).exists():
        return JsonResponse({"error": "Compte sans accès copropriétaire."}, status=403)
    credential = Credential.objects.filter(user=user, enabled=True).first()
    if credential:
        logout(request)
        request.session.cycle_key()
        request.session["mfa_challenge"] = {"user": user.pk, "hash": user.get_session_auth_hash(),
                                            "revision": credential.revision, "expires": timezone.now().timestamp() + 300}
        return JsonResponse({"mfa_required": True, "csrfToken": get_token(request)})
    try:
        establish_session(request, user)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=409)
    return JsonResponse({"user": user_data(user),
                         "csrfToken": get_token(request)})


@require_POST
def sign_out(request):
    logout(request)
    return JsonResponse({"user": None, "csrfToken": get_token(request)})


@require_GET
@member_required
def overview(request):
    return JsonResponse({"owners_count": Owner.objects.count(), "lots_count": Lot.objects.count(),
                         "unassigned_count": Lot.objects.filter(owner__isnull=True).count(),
                         "shares_total": str(Lot.objects.aggregate(total=Sum("shares"))["total"] or 0),
                         "kinds": list(Lot.objects.values("kind").annotate(count=Count("id")).order_by("kind"))})


def save_form(request, form_class, serializer, instance=None):
    try:
        data = payload(request)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    if instance is not None:
        # PATCH preserves fields omitted by the caller.
        initial = {field: getattr(instance, field + "_id" if field == "owner" else field)
                   for field in form_class.Meta.fields}
        data = initial | data
    if any(isinstance(value, (dict, list)) for value in data.values()):
        return JsonResponse({"error": "Les champs doivent contenir des valeurs simples."}, status=400)
    if isinstance(instance,Owner) and instance.user_id and (is_manager(instance.user) or active_mandates(instance.user).exists()) and not str(data.get("email","")).strip():
        return JsonResponse({"error":"Un compte gestionnaire doit conserver un courriel de connexion."},status=400)
    form = form_class(data=data, instance=instance)
    if not form.is_valid():
        return JsonResponse({"error": "Vérifiez les champs du formulaire.", "fields": form.errors}, status=400)
    try:
        with transaction.atomic():
            item = form.save()
            credentials = None
            if isinstance(item, Owner):
                if instance is None and item.email:
                    credentials = provision_access(item)
                elif item.user_id:
                    item.user.email = item.email
                    # Editing contact details must not undo an administrative suspension.
                    fields=["email"]
                    if not item.email:item.user.is_active = False;fields.append("is_active")
                    item.user.save(update_fields=fields)
    except IntegrityError:
        return JsonResponse({"error": "Ces données existent déjà ou ont été modifiées. Actualisez la page."}, status=409)
    result = serializer(item)
    if credentials:
        result["credentials"] = credentials
    response = JsonResponse(result, status=200 if instance else 201)
    response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["GET", "POST"])
@manager_required
def owners(request):
    if request.method == "GET":
        return JsonResponse({"items": [owner_data(item) for item in Owner.objects.select_related("user").prefetch_related("lots")]})
    return save_form(request, OwnerForm, owner_data)


@require_http_methods(["GET", "POST"])
@member_required
def lots(request):
    if request.method == "GET":
        items = [lot_data(item) for item in Lot.objects.select_related("owner")]
        if not is_manager(request.user):
            for item in items:
                item["owner"] = None
                item["owner_name"] = ""
        return JsonResponse({"items": items})
    if not is_manager(request.user):
        return JsonResponse({"error": "Accès en lecture uniquement."}, status=403)
    return save_form(request, LotForm, lot_data)


def detail(request, pk, model, form, serializer):
    try:
        instance = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return JsonResponse({"error": "Élément introuvable."}, status=404)
    if request.method == "PATCH":
        return save_form(request, form, serializer, instance)
    if isinstance(instance,Owner) and instance.user_id and (is_manager(instance.user) or active_mandates(instance.user).exists()):
        return JsonResponse({"error":"Ce copropriétaire possède un accès gestionnaire. Modifiez d’abord son rôle dans Administration → Utilisateurs."},status=409)
    try:
        with transaction.atomic():
            instance.delete()
            if isinstance(instance, Owner) and instance.user_id:
                instance.user.is_active = False
                instance.user.save(update_fields=["is_active"])
    except ProtectedError:
        return JsonResponse({"error": "Réattribuez les lots de ce copropriétaire avant de le supprimer."}, status=409)
    return JsonResponse({"deleted": True})


@require_http_methods(["PATCH", "DELETE"])
@manager_required
def owner_detail(request, pk):
    return detail(request, pk, Owner, OwnerForm, owner_data)


@require_http_methods(["PATCH", "DELETE"])
@manager_required
def lot_detail(request, pk):
    return detail(request, pk, Lot, LotForm, lot_data)


@require_POST
@manager_required
def owner_access(request, pk):
    try:
        data = payload(request)
        with transaction.atomic():
            owner = Owner.objects.select_for_update().get(pk=pk)
            if owner.user_id and active_mandates(owner.user).exists() and not request.user.is_superuser:
                return JsonResponse({"error": "La réinitialisation d’un accès au conseil est réservée à l’administrateur principal."}, status=403)
            credentials = provision_access(owner, reset=data.get("reset") is True)
    except Owner.DoesNotExist:
        return JsonResponse({"error": "Copropriétaire introuvable."}, status=404)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    response = JsonResponse({"credentials": credentials})
    response["Cache-Control"] = "no-store"
    return response


@require_POST
def change_password(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Connexion nécessaire."}, status=401)
    try:
        data = payload(request)
        old, new = data.get("old_password"), data.get("new_password")
        if not isinstance(old, str) or not isinstance(new, str):
            raise ValueError("Les deux mots de passe sont requis.")
        if not request.user.check_password(old):
            raise ValueError("Le mot de passe actuel est incorrect.")
        if old == new:
            raise ValueError("Choisissez un nouveau mot de passe différent.")
        validate_password(new, user=request.user)
    except (ValueError, ValidationError) as error:
        return JsonResponse({"error": " ".join(error.messages) if isinstance(error, ValidationError) else str(error)}, status=400)
    with transaction.atomic():
        request.user.set_password(new)
        request.user.save(update_fields=["password"])
        owner = getattr(request.user, "owner_profile", None)
        if owner:
            owner.must_change_password = False
            owner.save(update_fields=["must_change_password"])
        external = getattr(request.user, "council_identity", None)
        if external:
            external.must_change_password = False
            external.save(update_fields=["must_change_password"])
        from safety.models import Credential
        Credential.objects.filter(user=request.user).update(must_change_password=False)
        security = getattr(request.user, "security_credential", None)
        if security:
            security.must_change_password = False
    update_session_auth_hash(request, request.user)
    return JsonResponse({"user": user_data(request.user), "csrfToken": get_token(request)})
