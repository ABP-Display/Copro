from django.urls import path, include
from core import views

urlpatterns = [
    path("api/council/", include("council.urls")),
    path("api/operations/",include("operations.urls")),
    path("api/ag/",include("governance.urls")),
    path("api/documents/",include("documents.urls")),
    path("api/finance/",include("finance.urls")),
    path("api/health/", views.health),
    path("api/session/", views.session),
    path("api/login/", views.sign_in),
    path("api/logout/", views.sign_out),
    path("api/password/", views.change_password),
    path("api/owners/<int:pk>/access/", views.owner_access),
    path("api/overview/", views.overview),
    path("api/owners/", views.owners),
    path("api/owners/<int:pk>/", views.owner_detail),
    path("api/lots/", views.lots),
    path("api/lots/<int:pk>/", views.lot_detail),
]
