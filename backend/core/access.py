import secrets
from functools import wraps
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from council.access import is_manager, active_mandates, capabilities


def password_pending(user):
    owner = getattr(user, "owner_profile", None)
    external = getattr(user, "council_identity", None)
    security = getattr(user, "security_credential", None)
    return bool(owner and owner.must_change_password or external and external.must_change_password or security and security.must_change_password)


def former_owner(owner):
    if owner is None or owner.lots.exists():
        return False
    from finance.models import OwnershipChange
    from django.db.models import Q

    return OwnershipChange.objects.filter(
        Q(old_owner=owner) | Q(new_owner=owner)
    ).exists()


def user_data(user):
    from safety.authentication import security_data
    owner = getattr(user, "owner_profile", None)
    return {
        **security_data(user),
        "id": user.pk,
        "username": user.email if owner or getattr(user, "council_identity", None) else user.username,
        "is_manager": is_manager(user),
        "is_admin": user.is_superuser,
        "must_change_password": password_pending(user),
        "is_former_owner": former_owner(owner),
        "display_name": str(owner) if owner else user.get_full_name() or user.username,
        "has_owner": owner is not None,
        "capabilities": sorted(capabilities(user)),
        "roles": list(active_mandates(user).values_list("role", flat=True)),
    }


def member_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Connexion nécessaire."}, status=401)
        owner = getattr(request.user, "owner_profile", None)
        if not is_manager(request.user) and not active_mandates(request.user).exists() and (owner is None or not owner.email):
            return JsonResponse(
                {"error": "Compte sans accès copropriétaire."}, status=403
            )
        if password_pending(request.user):
            return JsonResponse(
                {
                    "error": "Changez votre mot de passe pour accéder aux données.",
                    "code": "password_change_required",
                },
                status=403,
            )
        if (
            not is_manager(request.user)
            and not active_mandates(request.user).exists()
            and former_owner(owner)
            and not getattr(view, "allow_former_owner", False)
        ):
            return JsonResponse(
                {
                    "error": "Votre accès conserve votre compte individuel après la cession de vos lots."
                },
                status=403,
            )
        return view(request, *args, **kwargs)

    return wrapped


def allow_former_owner(view):
    view.allow_former_owner = True
    return view


def provision_access(owner, reset=False):
    if not owner.email:
        raise ValueError("Renseignez un courriel avant de créer un accès.")
    if owner.user_id and not reset:
        raise ValueError(
            "Un accès existe déjà. Utilisez la réinitialisation pour en générer un nouveau."
        )
    password = secrets.token_urlsafe(18)
    if owner.user_id:
        user = owner.user
        if is_manager(user):
            raise ValueError(
                "Un compte gestionnaire ne peut pas être réinitialisé ici."
            )
        if not user.is_active:
            raise ValueError(
                "Ce compte est désactivé. L’administrateur principal doit le réactiver avant la réinitialisation."
            )
        user.set_password(password)
        user.email = owner.email
        user.save(update_fields=["password", "email"])
    else:
        user = get_user_model().objects.create_user(
            username="owner-" + secrets.token_hex(16),
            email=owner.email,
            password=password,
            first_name=owner.first_name,
            last_name=owner.last_name,
        )
        owner.user = user
    owner.must_change_password = True
    owner.save(update_fields=["user", "must_change_password"])
    return {"email": owner.email, "temporary_password": password}
