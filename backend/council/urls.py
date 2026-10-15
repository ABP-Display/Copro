from django.urls import path
from . import views

urlpatterns = [
    path("context/", views.context),
    path("settings/", views.settings),
    path("mandates/", views.mandates),
    path("mandates/<int:pk>/<str:action>/", views.mandates),
    path("drafts/", views.drafts),
    path("drafts/<int:pk>/", views.drafts),
    path("drafts/<int:pk>/<str:action>/", views.drafts),
    path("requests/", views.requests),
    path("requests/<int:pk>/<str:action>/", views.requests),
    path("controls/", views.controls),
    path("controls/<int:pk>/", views.controls),
    path("controls/<int:pk>/<str:action>/", views.controls),
    path("records/", views.records),
    path("targets/", views.targets),
    path("files/<int:pk>/", views.file),
    path("upload/", views.upload),
]
