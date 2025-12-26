import json

from django.shortcuts import render

from flights.models import Flight
from flights.utils.currency_calculator import check_medical_status, check_passenger_currency
from flights.utils.statistics import (
    get_aircraft_breakdown,
    get_commercial_license_progress,
    get_cumulative_time_data,
    get_days_since_last_flight,
    get_instructor_leaderboard,
    get_instrument_breakdown,
    get_instrument_rating_progress,
    get_monthly_breakdown,
    get_passenger_leaderboard,
    get_recent_flights,
    get_total_times,
)
from pilots.models import Pilot
from routes.models import Route


def dashboard(request):
    """
    Main dashboard view showing flight statistics, currency, and visualizations.
    """
    # For now, hardcode to pilot with pk=1 (single user mode)
    # In the future, this could filter by request.user
    try:
        pilot = Pilot.objects.get(pk=1)
    except Pilot.DoesNotExist:
        # If no pilot exists, show empty dashboard
        return render(request, 'flights/dashboard.html', {
            'error': 'No pilot found. Please create a pilot in the admin.',
            'total_times': {},
            'currency': {},
            'medical': {},
            'ir_progress': {},
            'monthly_labels': [],
            'monthly_hours': [],
            'instrument_breakdown': {},
            'cumulative_data': [],
            'aircraft_breakdown': [],
            'recent_flights': [],
            'days_since_last_flight': None,
        })

    # Gather all statistics
    total_times = get_total_times(pilot)
    currency = check_passenger_currency(pilot)
    medical = check_medical_status(pilot)
    ir_progress = get_instrument_rating_progress(pilot)
    commercial_progress = get_commercial_license_progress(pilot)
    instrument_breakdown = get_instrument_breakdown(pilot)
    aircraft_breakdown = get_aircraft_breakdown(pilot)
    recent_flights = get_recent_flights(pilot, limit=10)
    days_since_last_flight = get_days_since_last_flight(pilot)
    passenger_leaderboard = get_passenger_leaderboard(pilot, limit=10)
    instructor_leaderboard = get_instructor_leaderboard(pilot, limit=10)

    # Get monthly data for charts
    monthly_data = get_monthly_breakdown(pilot, months=12)
    monthly_labels = [entry['month'] for entry in monthly_data]
    monthly_hours = [entry['hours'] for entry in monthly_data]

    # Get cumulative time data for line chart
    cumulative_data = get_cumulative_time_data(pilot)

    context = {
        'total_times': total_times,
        'currency': currency,
        'medical': medical,
        'ir_progress': ir_progress,
        'commercial_progress': commercial_progress,
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_hours': json.dumps(monthly_hours),
        'instrument_breakdown': instrument_breakdown,
        'cumulative_data': json.dumps(cumulative_data),
        'aircraft_breakdown': aircraft_breakdown,
        'recent_flights': recent_flights,
        'days_since_last_flight': days_since_last_flight,
        'passenger_leaderboard': passenger_leaderboard,
        'instructor_leaderboard': instructor_leaderboard,
    }

    return render(request, 'flights/dashboard.html', context)


def logbook(request):
    """
    Logbook view showing all flight entries in a table format.
    """
    # For now, hardcode to pilot with pk=1 (single user mode)
    # In the future, this could filter by request.user
    try:
        pilot = Pilot.objects.get(pk=1)
    except Pilot.DoesNotExist:
        # If no pilot exists, show empty logbook
        return render(request, 'flights/logbook.html', {
            'error': 'No pilot found. Please create a pilot in the admin.',
            'flights': [],
        })

    # Get all flights for this pilot, ordered by date (most recent first)
    flights = Flight.objects.filter(pilot=pilot).select_related('plane', 'instructor').order_by('-date')

    context = {
        'flights': flights,
    }

    return render(request, 'flights/logbook.html', context)


def routes_map(request):
    """
    Routes map view showing unique flight routes on an interactive map.
    """
    try:
        pilot = Pilot.objects.get(pk=1)
    except Pilot.DoesNotExist:
        return render(request, 'flights/routes_map.html', {
            'error': 'No pilot found. Please create a pilot in the admin.',
            'routes': [],
        })

    # Get all unique routes from flights and count how many times each was flown
    # Also count how many times each airport was visited
    flights = Flight.objects.filter(pilot=pilot).select_related('route').prefetch_related('route__waypoints')
    unique_routes = {}
    route_counts = {}
    airport_visits = {}

    for flight in flights:
        if flight.route:
            route_id = flight.route.id

            # Count flights for this route
            route_counts[route_id] = route_counts.get(route_id, 0) + 1

            # Count airport visits for this flight (each airport only counted once per flight)
            waypoints = flight.route.waypoints.all()
            unique_airports_in_flight = set()
            for waypoint in waypoints:
                unique_airports_in_flight.add(waypoint.code)

            for airport_code in unique_airports_in_flight:
                airport_visits[airport_code] = airport_visits.get(airport_code, 0) + 1

            if route_id not in unique_routes:
                route = flight.route
                waypoints = route.waypoints.all().order_by('routewaypoint__sequence')

                waypoints_data = []
                for waypoint in waypoints:
                    if waypoint.latitude and waypoint.longitude:
                        waypoints_data.append({
                            'code': waypoint.code,
                            'name': waypoint.name,
                            'lat': float(waypoint.latitude),
                            'lon': float(waypoint.longitude),
                            'visit_count': 0,  # Will be updated below
                        })

                if waypoints_data:
                    unique_routes[route_id] = {
                        'id': route.id,
                        'name': route.name,
                        'waypoints': waypoints_data,
                        'flight_count': 0,  # Will be updated below
                    }

    # Add flight counts to unique routes
    for route_id in unique_routes:
        unique_routes[route_id]['flight_count'] = route_counts.get(route_id, 0)

        # Add visit counts to waypoints
        for waypoint in unique_routes[route_id]['waypoints']:
            waypoint['visit_count'] = airport_visits.get(waypoint['code'], 0)

    context = {
        'routes_json': json.dumps(list(unique_routes.values())),
    }

    return render(request, 'flights/routes_map.html', context)
