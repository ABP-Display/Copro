"""TOTP secrets never leave the server after enrolment; codes are consumed under a row lock."""
import base64
import hashlib
import hmac
import secrets
import time
from datetime import timedelta

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import Attempt, Credential, Policy, SecurityEvent


def cipher():
    key = hashlib.sha256(("copro.totp.v1:" + settings.SECRET_KEY).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(secret):
    return cipher().encrypt(secret.encode()).decode()


def decrypt(value):
    try:
        return cipher().decrypt(value.encode()).decode()
    except (InvalidToken, ValueError):
        raise ValueError("La clé du serveur ne permet pas de lire ce secret. Utilisez la procédure de récupération serveur.") from None


def recovery_hash(code):
    normalized = str(code).replace("-", "").replace(" ", "").upper()
    return salted_hmac("copro.recovery.v1", normalized).hexdigest()


def new_recovery_codes(credential):
    codes = [secrets.token_hex(8).upper() for _ in range(10)]
    credential.recovery_hashes = [recovery_hash(code) for code in codes]
    return ["-".join(code[i:i + 4] for i in range(0, 16, 4)) for code in codes]


def consume_code(credential, code, *, allow_recovery=True, pending=False):
    # Caller holds select_for_update() on Credential, including when using a recovery code.
    code = str(code).strip()
    if not pending and allow_recovery:
        digest = recovery_hash(code)
        for index, saved in enumerate(credential.recovery_hashes):
            if hmac.compare_digest(digest, saved):
                credential.recovery_hashes.pop(index)
                credential.save(update_fields=["recovery_hashes"])
                return True
    if len(code) != 6 or not code.isascii() or not code.isdigit():
        return False
    totp = pyotp.TOTP(decrypt(credential.pending_secret if pending else credential.secret))
    now = int(time.time()) // 30
    for counter in (now, now - 1, now + 1):
        if counter > credential.last_counter and hmac.compare_digest(totp.at(counter * 30), code):
            credential.last_counter = counter
            credential.save(update_fields=["last_counter"])
            return True
    return False


def required(user):
    from core.access import is_manager
    return bool(is_manager(user) and Policy.objects.filter(pk=1, require_managers=True).exists())


def security_data(user):
    credential = Credential.objects.filter(user=user).first()
    return {"mfa_enabled": bool(credential and credential.enabled),
            "mfa_required": required(user), "recovery_remaining": len(credential.recovery_hashes) if credential else 0}


def event(user, action, detail=""):
    SecurityEvent.objects.create(user=user, action=action, detail=detail[:300])


def charge_attempt(namespace, value, limit=5, seconds=300):
    """Shared DB rate limit, independent of cookies and Gunicorn workers."""
    key = salted_hmac("copro.attempt", namespace + ":" + value).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        Attempt.objects.get_or_create(key=key, defaults={"started_at": now})
        item = Attempt.objects.select_for_update().get(pk=key)
        if now >= item.started_at + timedelta(seconds=seconds):
            item.started_at, item.count = now, 0
        if item.count >= limit:
            return False
        item.count += 1
        item.save()
    return True


def establish_session(request, user, *, verified_revision=None):
    from django.contrib.auth import login
    credential, _ = Credential.objects.get_or_create(user=user)
    if (verified_revision is None and credential.enabled
            or verified_revision is not None and credential.revision != verified_revision):
        raise ValueError("La sécurité du compte a changé. Recommencez la connexion.")
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["security_revision"] = credential.revision if verified_revision is None else verified_revision
    request.session.pop("mfa_challenge", None)


def reset_credential(credential):
    credential.enabled = False
    credential.secret = credential.pending_secret = ""
    credential.pending_until = credential.enabled_at = None
    credential.recovery_hashes = []
    credential.last_counter = -1
    credential.revision += 1
    credential.save()
