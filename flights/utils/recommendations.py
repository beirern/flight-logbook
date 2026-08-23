"""Frequency-ranked query helpers for the add-flight page's typeahead/default fields.

These are deliberately separate from flights/utils/statistics.py: the functions
there loop over full querysets in Python, which is fine for a once-per-page-load
stats dashboard but far too slow for typeahead-latency search. Everything here
is a single DB-aggregated, capped query - no full-table scans, no per-row
Route.__str__/Pilot.__str__ calls (which is what makes the Django admin's
dropdowns slow).
"""
from django.db.models import Count, Q

from flights.models import Flight
from pilots.models import Pilot
from planes.models import Plane
from routes.models import Airport, Route

SEARCH_RESULT_LIMIT = 8


def get_planes_by_frequency(pilot):
    """All planes, most-flown-first. Small table, so no limit - safe to render as a <select>."""
    return Plane.objects.annotate(
        flight_count=Count("flight", filter=Q(flight__pilot=pilot))
    ).order_by("-flight_count", "tail_number")


def search_routes(pilot, query="", limit=SEARCH_RESULT_LIMIT):
    """Top routes by frequency, optionally filtered by name. Never touches Route.__str__."""
    qs = Route.objects.annotate(
        flight_count=Count("flight", filter=Q(flight__pilot=pilot))
    ).prefetch_related("route_steps__waypoint")
    if query:
        qs = qs.filter(name__icontains=query)
    qs = qs.order_by("-flight_count", "name")[:limit]
    return [_serialize_route(route) for route in qs]


def _serialize_route(route):
    path = " -> ".join(step.waypoint.code for step in route.route_steps.all())
    return {
        "id": route.id,
        "name": route.name,
        "path": path,
        "flight_count": route.flight_count,
        "label": f"{route.name} ({path})" if path else route.name,
    }


def get_default_route(pilot):
    routes = search_routes(pilot, limit=1)
    return routes[0] if routes else None


def search_pilots(role_codes, query="", limit=SEARCH_RESULT_LIMIT):
    """Search pilots by role, alphabetically. Used to back the instructor/passenger typeahead."""
    qs = Pilot.objects.filter(role__in=role_codes)
    if query:
        qs = qs.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query))
    qs = qs.order_by("last_name", "first_name")[:limit]
    return [_serialize_pilot(p) for p in qs]


def get_recent_pilots_by_role(pilot, role_codes, limit=SEARCH_RESULT_LIMIT):
    """Frequency-ranked pilots of the given role(s), used as the pre-seeded 'recent' list
    shown before the user types anything (zero-latency, no fetch needed on focus)."""
    if role_codes == [Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]:
        count_filter = Q(as_flight_instructor__pilot=pilot)
        count_field = "as_flight_instructor"
    else:
        count_filter = Q(as_passenger__pilot=pilot)
        count_field = "as_passenger"

    qs = (
        Pilot.objects.filter(role__in=role_codes)
        .annotate(flight_count=Count(count_field, filter=count_filter))
        .order_by("-flight_count", "last_name")[:limit]
    )
    return [_serialize_pilot(p) for p in qs]


def _serialize_pilot(pilot):
    return {
        "id": pilot.id,
        "name": str(pilot),
        "flight_count": getattr(pilot, "flight_count", None),
    }


def get_default_instructor(pilot):
    """Most recently used instructor (by flight date), not just most frequent."""
    last_flight = (
        Flight.objects.filter(pilot=pilot, instructor__isnull=False)
        .select_related("instructor")
        .order_by("-date", "-id")
        .first()
    )
    return last_flight.instructor if last_flight else None


def search_airports(query="", limit=SEARCH_RESULT_LIMIT):
    """Used for the per-approach airport typeahead."""
    qs = Airport.objects.all()
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(municipality__icontains=query))
    qs = qs.order_by("code")[:limit]
    return [
        {"id": a.id, "code": a.code, "name": a.name, "label": f"{a.code} - {a.name}"}
        for a in qs
    ]
