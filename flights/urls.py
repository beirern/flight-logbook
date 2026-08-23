from django.urls import path

from .views import dashboard_views, flight_entry_views

urlpatterns = [
    path("", dashboard_views.dashboard, name="dashboard"),
    path("logbook/", dashboard_views.logbook, name="logbook"),
    path("routes/", dashboard_views.routes_map, name="routes_map"),
    path("people/", dashboard_views.people, name="people"),
    path("aircraft/", dashboard_views.aircraft, name="aircraft"),
    path("flights/add/", flight_entry_views.add_flight, name="add_flight"),
    path("api/routes/search/", flight_entry_views.search_routes_json, name="search_routes"),
    path("api/instructors/search/", flight_entry_views.search_instructors_json, name="search_instructors"),
    path("api/passengers/search/", flight_entry_views.search_passengers_json, name="search_passengers"),
    path("api/airports/search/", flight_entry_views.search_airports_json, name="search_airports"),
]
