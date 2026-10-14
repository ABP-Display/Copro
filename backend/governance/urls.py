from django.urls import path

from . import views
from . import workflow_views

urlpatterns = [
    path("workflow-context/", workflow_views.context),
    path("summaries/", workflow_views.summaries),
    path("meetings/<int:pk>/workflow/", workflow_views.workflow),
    path("meetings/<int:pk>/workflow/<str:action>/", workflow_views.workflow),
    path("electorate/", views.electorate),
    path("meetings/", views.meetings),
    path("meetings/<int:pk>/", views.meeting),
    path("meetings/<int:pk>/resolutions/", views.resolutions),
    path("resolutions/<int:pk>/", views.resolution),
    path("resolutions/<int:pk>/simulate/", views.simulate),
    path("tools/<str:kind>/", views.tools),
]
