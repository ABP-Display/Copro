from django.urls import path
from . import views

urlpatterns = [
    path("folders/", views.folders),
    path("folders/<int:pk>/", views.folders),
    path("items/", views.items),
    path("items/<int:pk>/", views.item),
    path("items/<int:pk>/upload/", views.upload),
    path("items/<int:pk>/download/", views.download),
    path("versions/<int:version>/download/", views.download),
]
