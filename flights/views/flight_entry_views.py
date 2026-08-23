import json

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render

from flights.forms import ApproachFormSet, FlightForm
from flights.utils.recommendations import (
    get_default_instructor,
    get_default_route,
    get_planes_by_frequency,
    get_recent_pilots_by_role,
    search_airports,
    search_pilots,
    search_routes,
)
from pilots.models import Pilot

INSTRUCTOR_ROLES = [Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]
PASSENGER_ROLES = [Pilot.RoleChoices.PASSENGER]


@staff_member_required
def add_flight(request):
    """Fast flight-entry page: a purpose-built alternative to the slow Django
    admin add-flight form. Typeahead fields never render full option lists
    (that N+1/full-dump pattern is what makes admin slow); instead they search
    against small, frequency-ranked, DB-aggregated endpoints below."""
    pilot = Pilot.objects.get(pk=1)

    default_route = get_default_route(pilot)
    default_instructor = get_default_instructor(pilot)

    if request.method == "POST":
        form = FlightForm(request.POST)
        formset = ApproachFormSet(request.POST, instance=form.instance)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                flight = form.save(commit=False)
                flight.pilot = pilot
                flight.save()
                form.save_m2m()
                formset.instance = flight
                formset.save()
            return redirect("logbook")
    else:
        form = FlightForm(
            initial={
                "route": default_route["id"] if default_route else None,
                "instructor": default_instructor.id if default_instructor else None,
            }
        )
        formset = ApproachFormSet()

    form.fields["plane"].queryset = get_planes_by_frequency(pilot)

    context = {
        "form": form,
        "formset": formset,
        "default_route": default_route,
        "default_instructor": default_instructor,
        "recent_instructors_json": json.dumps(get_recent_pilots_by_role(pilot, INSTRUCTOR_ROLES)),
        "recent_passengers_json": json.dumps(get_recent_pilots_by_role(pilot, PASSENGER_ROLES)),
    }
    return render(request, "flights/add_flight.html", context)


@staff_member_required
def search_routes_json(request):
    pilot = Pilot.objects.get(pk=1)
    return JsonResponse({"results": search_routes(pilot, request.GET.get("q", "").strip())})


@staff_member_required
def search_instructors_json(request):
    return JsonResponse({"results": search_pilots(INSTRUCTOR_ROLES, request.GET.get("q", "").strip())})


@staff_member_required
def search_passengers_json(request):
    return JsonResponse({"results": search_pilots(PASSENGER_ROLES, request.GET.get("q", "").strip())})


@staff_member_required
def search_airports_json(request):
    return JsonResponse({"results": search_airports(request.GET.get("q", "").strip())})
