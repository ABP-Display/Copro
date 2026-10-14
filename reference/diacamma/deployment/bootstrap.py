"""Migrate, secure the upstream default admin, then start the web process."""
import os
import sys

import django


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deployment.settings")
    password = os.environ.get("SYNDIC_ADMIN_PASSWORD", "")
    if len(password) < 12 or password == "admin":
        raise SystemExit("SYNDIC_ADMIN_PASSWORD doit contenir au moins 12 caractères.")

    django.setup()
    from django.contrib.auth import get_user_model
    from django.apps import apps
    from django.core.management import call_command
    from django.core.management.color import no_style
    from django.db import connection

    # Test DB state before migrations: upstream creates admin/admin on a new DB.
    first_install = "auth_user" not in connection.introspection.table_names()
    call_command("migrate", interactive=False)
    # Upstream data migrations insert explicit IDs. PostgreSQL sequences do not
    # advance on those inserts; synchronize before accepting new records.
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), apps.get_models()):
                cursor.execute(sql)
    admin = get_user_model().objects.get(username="admin")
    if first_install or admin.check_password("admin"):
        admin.set_password(password)
        admin.save(update_fields=["password"])
        print("Compte admin initialisé avec le mot de passe configuré.", flush=True)
    call_command("collectstatic", interactive=False, verbosity=0)
    if len(sys.argv) > 1:
        os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
