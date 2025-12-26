import json
import math

from django.shortcuts import render

from flights.models import Flight
from flights.utils.currency_calculator import check_medical_status, check_passenger_currency
from flights.utils.statistics import (
    get_aircraft_breakdown,
    get_aircraft_class_breakdown,
    get_aircraft_highlights,
    get_aircraft_type_statistics,
    get_commercial_license_progress,
    get_cumulative_time_data,
    get_days_since_last_flight,
    get_instructor_leaderboard,
    get_instructor_time_progression,
    get_instrument_breakdown,
    get_instrument_rating_progress,
    get_monthly_breakdown,
    get_monthly_people_frequency,
    get_passenger_leaderboard,
    get_people_insights,
    get_people_role_distribution,
    get_recent_flights,
    get_sel_total_hours,
    get_total_times,
    get_unique_people_counts,
)
from pilots.models import Pilot
from routes.models import Route


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in nautical miles between two points
    on the earth (specified in decimal degrees).
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in nautical miles
    nm = 3440.065
    return c * nm


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
    recent_flights = get_recent_flights(pilot, limit=10)
    days_since_last_flight = get_days_since_last_flight(pilot)

    # Get monthly data for charts
    monthly_data = get_monthly_breakdown(pilot, months=12)
    monthly_labels = [entry['month'] for entry in monthly_data]
    monthly_hours = [entry['hours'] for entry in monthly_data]

    # Get cumulative time data for line chart
    cumulative_data = get_cumulative_time_data(pilot)

    # Get instructor time progression data
    instructor_progression = get_instructor_time_progression(pilot)

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
        'instructor_progression': json.dumps(instructor_progression),
        'recent_flights': recent_flights,
        'days_since_last_flight': days_since_last_flight,
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
                    # Calculate total distance for the route
                    total_distance = 0
                    for i in range(len(waypoints_data) - 1):
                        wp1 = waypoints_data[i]
                        wp2 = waypoints_data[i + 1]
                        total_distance += haversine_distance(wp1['lat'], wp1['lon'], wp2['lat'], wp2['lon'])

                    unique_routes[route_id] = {
                        'id': route.id,
                        'name': route.name,
                        'waypoints': waypoints_data,
                        'flight_count': 0,  # Will be updated below
                        'distance': round(total_distance, 1),  # Distance in nautical miles
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


def aircraft(request):
    """
    Aircraft page showing aircraft-related statistics, charts, and tables.
    """
    try:
        pilot = Pilot.objects.get(pk=1)
    except Pilot.DoesNotExist:
        return render(request, 'flights/aircraft.html', {
            'error': 'No pilot found. Please create a pilot in the admin.',
            'sel_hours': 0,
            'aircraft_class_breakdown': {},
            'aircraft_type_statistics': [],
            'aircraft_highlights': {},
            'aircraft_breakdown': [],
        })

    # Gather aircraft statistics
    sel_hours = get_sel_total_hours(pilot)
    aircraft_class_breakdown = get_aircraft_class_breakdown(pilot)
    aircraft_type_statistics = get_aircraft_type_statistics(pilot)
    aircraft_highlights = get_aircraft_highlights(pilot)
    aircraft_breakdown = get_aircraft_breakdown(pilot)

    # Prepare chart data
    class_labels = list(aircraft_class_breakdown.keys())
    class_hours = [aircraft_class_breakdown[c]['hours'] for c in class_labels]

    type_labels = [stat['type'] for stat in aircraft_type_statistics]
    type_hours = [stat['hours'] for stat in aircraft_type_statistics]

    context = {
        'sel_hours': sel_hours,
        'aircraft_class_breakdown': aircraft_class_breakdown,
        'aircraft_type_statistics': aircraft_type_statistics,
        'aircraft_highlights': aircraft_highlights,
        'aircraft_breakdown': aircraft_breakdown,
        'class_labels': json.dumps(class_labels),
        'class_hours': json.dumps(class_hours),
        'type_labels': json.dumps(type_labels),
        'type_hours': json.dumps(type_hours),
    }

    return render(request, 'flights/aircraft.html', context)


def people(request):
    """
    People page showing statistics about passengers and instructors.
    """
    try:
        pilot = Pilot.objects.get(pk=1)
    except Pilot.DoesNotExist:
        return render(request, 'flights/people.html', {
            'error': 'No pilot found. Please create a pilot in the admin.',
            'unique_people_counts': {},
            'people_role_distribution': {},
            'passenger_leaderboard': [],
            'instructor_leaderboard': [],
            'people_insights': {},
            'monthly_people_data': [],
        })

    # Gather people statistics
    unique_people_counts = get_unique_people_counts(pilot)
    people_role_distribution = get_people_role_distribution(pilot)
    passenger_leaderboard = get_passenger_leaderboard(pilot, limit=10)
    instructor_leaderboard = get_instructor_leaderboard(pilot, limit=10)
    people_insights = get_people_insights(pilot)
    monthly_people_data = get_monthly_people_frequency(pilot, months=12)

    # Prepare chart data for role distribution pie chart
    role_labels = ['Solo', 'With Passengers', 'With Instructor']
    role_counts = [
        people_role_distribution['solo_flights'],
        people_role_distribution['passenger_flights'],
        people_role_distribution['instruction_flights']
    ]

    # Prepare chart data for monthly trends
    monthly_labels = [entry['month'] for entry in monthly_people_data]
    monthly_total_flights = [entry['total_flights'] for entry in monthly_people_data]
    monthly_passenger_flights = [entry['flights_with_passengers'] for entry in monthly_people_data]
    monthly_instruction_flights = [entry['flights_with_instruction'] for entry in monthly_people_data]

    context = {
        'unique_people_counts': unique_people_counts,
        'people_role_distribution': people_role_distribution,
        'passenger_leaderboard': passenger_leaderboard,
        'instructor_leaderboard': instructor_leaderboard,
        'people_insights': people_insights,
        'role_labels': json.dumps(role_labels),
        'role_counts': json.dumps(role_counts),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_total_flights': json.dumps(monthly_total_flights),
        'monthly_passenger_flights': json.dumps(monthly_passenger_flights),
        'monthly_instruction_flights': json.dumps(monthly_instruction_flights),
    }

    return render(request, 'flights/people.html', context)
