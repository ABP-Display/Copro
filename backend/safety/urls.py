from django.urls import path
from . import views

urlpatterns = [
    path("status/", views.status),
    path("setup/", views.setup),
    path("confirm/", views.confirm),
    path("disable/", views.disable),
    path("recovery/", views.recovery),
    path("policy/", views.policy),
    path("backups/", views.backups),
]
