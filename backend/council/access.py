from django.db.models import Q
from django.utils import timezone
from .models import Mandate, CouncilSettings

READ = "council.read"
PREPARE = "expense.prepare"
REVIEW = "expense.review"
CONTROL = "accounts.control"
MANAGE = "management.write"
ROLE_CAPABILITIES = {
    "syndic": {READ, PREPARE, MANAGE},
    "coop_syndic": {READ, PREPARE, MANAGE},
    "president": {READ, REVIEW},
    "vice": {READ, REVIEW},
    "council": {READ, REVIEW},
    "treasurer": {READ, PREPARE},
    "controller": {READ, CONTROL},
}


def active_mandates(user):
    if not user.is_authenticated or not user.is_active:
        return Mandate.objects.none()
    today = timezone.localdate()
    query = Mandate.objects.filter(user=user, starts_on__lte=today, ends_on__gte=today, revoked_at__isnull=True)
    # A mandate is bound to its original account; changing a contact never transfers access.
    query = query.filter(Q(role="controller") | Q(owner__user=user, owner__lots__isnull=False)).distinct()
    mode = CouncilSettings.objects.filter(pk=1).values_list("mode", flat=True).first() or "benevole"
    query = query.exclude(role="syndic" if mode == "cooperative" else "coop_syndic")
    return query.filter(
        Q(seat__isnull=True)
        | Q(seat__user=user, seat__revoked_at__isnull=True, seat__starts_on__lte=today, seat__ends_on__gte=today)
    )


def capabilities(user):
    result = set()
    if user.is_authenticated and user.is_active:
        if user.is_staff or user.is_superuser:
            result.update({READ, PREPARE, MANAGE})
        for role in active_mandates(user).values_list("role", flat=True):
            result.update(ROLE_CAPABILITIES.get(role, set()))
        # A person who manages the accounts does not act as their independent reviewer.
        if MANAGE in result:
            result.difference_update({REVIEW, CONTROL})
        if user.is_superuser:
            result.add("access.admin")
    return result


def is_manager(user):
    if not user.is_authenticated or not user.is_active:
        return False
    return user.is_staff or user.is_superuser or active_mandates(user).filter(role__in=["syndic", "coop_syndic"]).exists()


def can(user, capability):
    return capability in capabilities(user)
