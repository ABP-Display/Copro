import json
from django.core.management.base import BaseCommand, CommandError
from safety.inventory import inventory


class Command(BaseCommand):
    help = "Inventaire interne des tables et fichiers ; ne contient aucun enregistrement en clair."

    def add_arguments(self, parser):
        parser.add_argument("--allow-damaged-documents", action="store_true")

    def handle(self, *args, **options):
        try:
            self.stdout.write(json.dumps(inventory(allow_damaged=options["allow_damaged_documents"]), sort_keys=True))
        except ValueError as error:
            raise CommandError(str(error)) from error
