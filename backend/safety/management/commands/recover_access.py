import secrets
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from safety.authentication import event, reset_credential
from safety.models import Credential


class Command(BaseCommand):
    help = "Récupération serveur : nouveau mot de passe temporaire et révocation du second facteur."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--confirm", required=True)
        parser.add_argument("--reason", required=True)

    def handle(self, *args, **options):
        if options["confirm"] != options["username"] or len(options["reason"].strip()) < 10:
            raise CommandError("Confirmez l’identifiant et donnez un motif d’au moins dix caractères.")
        with transaction.atomic():
            user = get_user_model().objects.select_for_update().filter(username=options["username"]).first()
            if not user or not user.is_active:
                raise CommandError("Compte actif introuvable. Cette commande ne réactive pas un compte suspendu.")
            credential, _ = Credential.objects.select_for_update().get_or_create(user=user)
            reset_credential(credential)
            credential.must_change_password = True
            credential.save(update_fields=["must_change_password"])
            password = secrets.token_urlsafe(24)
            user.set_password(password)
            user.save(update_fields=["password"])
            event(user, "access.emergency", options["reason"].strip())
        self.stdout.write("Accès récupéré. Les anciennes sessions et codes sont révoqués.")
        self.stdout.write("Mot de passe temporaire (à conserver maintenant) : " + password)
