from django.urls import path

from .views import dashboard_views

urlpatterns = [
    path("", dashboard_views.dashboard, name="dashboard"),
    path("logbook/", dashboard_views.logbook, name="logbook"),
]
