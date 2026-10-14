import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management import call_command

password = os.environ["ADMIN_PASSWORD"]
validate_password(password)
call_command("migrate", interactive=False)
User = get_user_model()
username = os.environ.get("ADMIN_USERNAME", "admin")
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, password=password)
    print("Compte administrateur initialisé.", flush=True)
os.execvp("gunicorn", ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000",
                       "--workers", "2", "--access-logfile", "-", "--error-logfile", "-"])
