from django.urls import path
from . import views
from . import advanced
from . import banking
from . import cycle_views
urlpatterns=[path('cycle/<str:resource>/',cycle_views.cycle),path('cycle/<str:resource>/<int:pk>/',cycle_views.cycle),path('banks/',banking.banks),path('banks/<int:pk>/',banking.banks),path('banks/<int:pk>/default/',banking.default_bank),path('bank-transfers/',banking.transfers),path("manage/<str:resource>/",advanced.manage),path("manage/<str:resource>/<int:pk>/",advanced.manage),path("operations/<str:resource>/<int:pk>/",advanced.operations),path("reporting/<str:kind>/",advanced.reports),path("<str:resource>/",views.collection),path("<str:resource>/<int:pk>/<str:operation>/",views.action)]
