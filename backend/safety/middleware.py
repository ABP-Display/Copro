from django.contrib.auth import logout
from django.http import JsonResponse
from .authentication import required
from .models import Credential


class SecurityGate:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/") and request.user.is_authenticated:
            credential = Credential.objects.filter(user=request.user).first()
            revision = credential.revision if credential else 0
            if request.session.get("security_revision", 0) != revision or (credential and credential.enabled and "security_revision" not in request.session):
                logout(request)
                if request.path != "/api/session/":
                    return JsonResponse({"error": "Votre sécurité a changé. Reconnectez-vous."}, status=401)
            elif required(request.user) and not (credential and credential.enabled):
                allowed = ("/api/session/", "/api/logout/", "/api/password/", "/api/health/")
                if request.path not in allowed and not request.path.startswith("/api/security/"):
                    return JsonResponse({"error": "Activez la double authentification pour ouvrir la gestion.",
                                         "code": "mfa_setup_required"}, status=403)
        return self.get_response(request)
