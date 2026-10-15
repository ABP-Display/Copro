import base64
import io
from datetime import timedelta
from functools import wraps

import pyotp
import qrcode
from qrcode.image.svg import SvgPathImage
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from core.access import password_pending, user_data, is_manager, active_mandates
from core.views import payload
from .authentication import (charge_attempt, consume_code, encrypt, establish_session, event,
                             new_recovery_codes, required, reset_credential, security_data)
from .models import BackupRecord, Credential, Policy, SecurityEvent


def authenticated(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Connexion nécessaire."}, status=401)
        if password_pending(request.user):
            return JsonResponse({"error": "Changez d’abord votre mot de passe temporaire."}, status=403)
        try:
            return view(request, *args, **kwargs)
        except ValueError as error:
            return JsonResponse({"error": str(error)}, status=400)
    return wrapped


def sensitive(request, credential, *, code=True):
    if not charge_attempt("security", str(request.user.pk)):
        raise ValueError("Trop de tentatives. Réessayez dans cinq minutes.")
    data = payload(request)
    if not request.user.check_password(str(data.get("password", ""))):
        raise ValueError("Le mot de passe actuel est incorrect.")
    if credential.enabled and code:
        with transaction.atomic():
            locked = Credential.objects.select_for_update().get(pk=credential.pk)
            if not consume_code(locked, data.get("code", "")):
                raise ValueError("Code incorrect, déjà utilisé ou expiré. Attendez le prochain code ou utilisez un code de secours.")
    return data


@require_GET
@authenticated
def status(request):
    return JsonResponse({**security_data(request.user), "user": user_data(request.user),
                         "events": list(SecurityEvent.objects.filter(user=request.user).values("action", "detail", "created_at")[:20])})


@require_POST
@authenticated
def setup(request):
    credential, _ = Credential.objects.get_or_create(user=request.user)
    # Rate limiting is intentionally outside the transaction used for secret changes.
    sensitive(request, credential, code=False)
    with transaction.atomic():
        credential = Credential.objects.select_for_update().get(pk=credential.pk)
        if credential.enabled:
            raise ValueError("La double authentification est déjà activée.")
        secret = pyotp.random_base32()
        credential.pending_secret = encrypt(secret)
        credential.pending_until = timezone.now() + timedelta(minutes=10)
        credential.save(update_fields=["pending_secret", "pending_until"])
    uri = pyotp.TOTP(secret).provisioning_uri(name=request.user.email or request.user.username, issuer_name="Copro.")
    stream = io.BytesIO()
    qrcode.make(uri, image_factory=SvgPathImage).save(stream)
    return JsonResponse({"secret": secret, "qr": "data:image/svg+xml;base64," + base64.b64encode(stream.getvalue()).decode(),
                         "expires_at": credential.pending_until})


@require_POST
@authenticated
def confirm(request):
    if not charge_attempt("security", str(request.user.pk)):
        return JsonResponse({"error": "Trop de tentatives. Réessayez dans cinq minutes."}, status=429)
    data = payload(request)
    with transaction.atomic():
        credential, _ = Credential.objects.select_for_update().get_or_create(user=request.user)
        if credential.enabled or not credential.pending_secret or credential.pending_until < timezone.now():
            raise ValueError("La préparation a expiré. Recommencez l’activation.")
        if not consume_code(credential, data.get("code", ""), pending=True, allow_recovery=False):
            raise ValueError("Code incorrect. Vérifiez l’heure du téléphone et le code à six chiffres.")
        credential.secret, credential.pending_secret = credential.pending_secret, ""
        credential.pending_until = None
        credential.enabled = True
        credential.enabled_at = timezone.now()
        credential.revision += 1
        codes = new_recovery_codes(credential)
        credential.save()
        event(request.user, "mfa.enabled")
    request.session["security_revision"] = credential.revision
    request.session.cycle_key()
    return JsonResponse({"user": user_data(request.user), "recovery_codes": codes})


def modify_factor(request, action):
    credential, _ = Credential.objects.get_or_create(user=request.user)
    # Charge before atomic so a rejected code cannot roll back the attempt counter.
    if not charge_attempt("security", str(request.user.pk)):
        raise ValueError("Trop de tentatives. Réessayez dans cinq minutes.")
    data = payload(request)
    if not request.user.check_password(str(data.get("password", ""))):
        raise ValueError("Le mot de passe actuel est incorrect.")
    with transaction.atomic():
        credential = Credential.objects.select_for_update().get(pk=credential.pk)
        if not credential.enabled:
            raise ValueError("La double authentification n’est pas activée.")
        if action == "disable" and required(request.user):
            raise ValueError("La double authentification est obligatoire pour votre accès de gestion.")
        if not consume_code(credential, data.get("code", "")):
            raise ValueError("Code incorrect, expiré ou déjà utilisé.")
        codes = None
        if action == "disable":
            reset_credential(credential)
        else:
            codes = new_recovery_codes(credential)
            credential.revision += 1
            credential.save()
        event(request.user, "mfa." + action)
    request.session["security_revision"] = credential.revision
    request.session.cycle_key()
    return JsonResponse({"user": user_data(request.user), "recovery_codes": codes})


@require_POST
@authenticated
def disable(request):
    return modify_factor(request, "disable")


@require_POST
@authenticated
def recovery(request):
    return modify_factor(request, "recovery")


@require_POST
def verify_login(request):
    try:
        data = payload(request)
        challenge = request.session.get("mfa_challenge")
        if not challenge or challenge["expires"] < timezone.now().timestamp():
            request.session.pop("mfa_challenge", None)
            raise ValueError("La connexion a expiré. Saisissez à nouveau votre mot de passe.")
        if not charge_attempt("mfa-login", str(challenge["user"])):
            return JsonResponse({"error": "Trop de codes essayés. Réessayez dans cinq minutes."}, status=429)
        with transaction.atomic():
            user = get_user_model().objects.filter(pk=challenge["user"], is_active=True).first()
            if not user or user.get_session_auth_hash() != challenge["hash"]:
                raise ValueError("La connexion a expiré. Recommencez.")
            if not is_manager(user) and not getattr(user, "owner_profile", None) and not active_mandates(user).exists():
                raise ValueError("Ce compte ne possède plus d’accès.")
            credential = Credential.objects.select_for_update().get(user=user)
            if not credential.enabled or credential.revision != challenge["revision"]:
                raise ValueError("La sécurité du compte a changé. Recommencez la connexion.")
            if not consume_code(credential, data.get("code", "")):
                raise ValueError("Code incorrect, déjà utilisé ou expiré.")
            event(user, "mfa.login")
        establish_session(request, user, verified_revision=credential.revision)
        return JsonResponse({"user": user_data(user), "csrfToken": get_token(request)})
    except (ValueError, Credential.DoesNotExist) as error:
        return JsonResponse({"error": str(error) if isinstance(error, ValueError) else "Recommencez la connexion."}, status=400)


@require_POST
@authenticated
def policy(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Réservé à l’administrateur principal."}, status=403)
    credential, _ = Credential.objects.get_or_create(user=request.user)
    if not credential.enabled:
        raise ValueError("Activez votre propre double authentification avant de modifier la règle.")
    data = sensitive(request, credential)
    value = data.get("require_managers")
    if not isinstance(value, bool):
        raise ValueError("Choix invalide.")
    Policy.objects.update_or_create(pk=1, defaults={"require_managers": value})
    event(request.user, "mfa.policy", "Gestionnaires : " + ("obligatoire" if value else "facultatif"))
    return JsonResponse({"require_managers": value, "user": user_data(request.user)})


@require_GET
@authenticated
def backups(request):
    if not request.user.is_superuser:
        return JsonResponse({"error": "Réservé à l’administrateur principal."}, status=403)
    if required(request.user) and not Credential.objects.filter(user=request.user, enabled=True).exists():
        return JsonResponse({"error": "Activez d’abord votre double authentification.", "code": "mfa_setup_required"}, status=403)
    return JsonResponse({"require_managers": Policy.objects.filter(pk=1, require_managers=True).exists(),
                         "items": list(BackupRecord.objects.values("archive_id", "action", "filename", "database_rows", "files", "size", "created_at")[:50]),
                         "events": list(SecurityEvent.objects.values("action", "detail", "created_at", "user__username")[:30])})
