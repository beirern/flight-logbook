from datetime import datetime, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from flights.models import Flight, Ground, SimulatorFlight


def get_total_times(pilot):
    """Aggregate all flight time categories for a pilot."""
    flights = Flight.objects.filter(pilot=pilot)

    total_landings = (
        (flights.aggregate(Sum('day_landings'))['day_landings__sum'] or 0) +
        (flights.aggregate(Sum('day_fullstop_landings'))['day_fullstop_landings__sum'] or 0) +
        (flights.aggregate(Sum('night_landings'))['night_landings__sum'] or 0) +
        (flights.aggregate(Sum('night_fullstop_landings'))['night_fullstop_landings__sum'] or 0)
    )

    return {
        'total_time': round(float(flights.aggregate(Sum('flight_time'))['flight_time__sum'] or 0), 1),
        'pic_time': round(float(flights.aggregate(Sum('pic_time'))['pic_time__sum'] or 0), 1),
        'sic_time': round(float(flights.aggregate(Sum('sic_time'))['sic_time__sum'] or 0), 1),
        'dual_time': round(float(flights.aggregate(Sum('flight_training_received'))['flight_training_received__sum'] or 0), 1),
        'xc_time': round(float(flights.aggregate(Sum('xc_time'))['xc_time__sum'] or 0), 1),
        'day_time': round(float(flights.aggregate(Sum('day_time'))['day_time__sum'] or 0), 1),
        'night_time': round(float(flights.aggregate(Sum('night_time'))['night_time__sum'] or 0), 1),
        'actual_instrument': round(float(flights.aggregate(Sum('actual_instrument_time'))['actual_instrument_time__sum'] or 0), 1),
        'simulated_instrument': round(float(flights.aggregate(Sum('simulated_instrument_time'))['simulated_instrument_time__sum'] or 0), 1),
        'day_landings': flights.aggregate(Sum('day_landings'))['day_landings__sum'] or 0,
        'night_landings': flights.aggregate(Sum('night_landings'))['night_landings__sum'] or 0,
        'total_landings': total_landings,
    }


def get_monthly_breakdown(pilot, months=12):
    """Get flight hours broken down by month for the last N months, including months with 0 hours."""
    from dateutil.relativedelta import relativedelta

    # Get current date and calculate start date
    now = datetime.now().date()
    start_date = now - relativedelta(months=months-1)
    start_date = start_date.replace(day=1)  # Start from first day of the month

    # Query flights and group by month
    monthly = Flight.objects.filter(
        pilot=pilot,
        date__gte=start_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        hours=Sum('flight_time')
    ).order_by('month')

    # Create a dictionary of month -> hours from database results
    hours_by_month = {
        entry['month']: float(entry['hours']) if entry['hours'] else 0
        for entry in monthly
    }

    # Generate all months in the range and fill in 0 for missing months
    result = []
    current = start_date
    for _ in range(months):
        month_key = datetime(current.year, current.month, 1).date()
        result.append({
            'month': current.strftime('%b %Y'),
            'hours': hours_by_month.get(month_key, 0)
        })
        current = current + relativedelta(months=1)

    return result


def get_instrument_breakdown(pilot):
    """Get breakdown of instrument time (actual vs simulated from flights and simulators)."""
    flights = Flight.objects.filter(pilot=pilot)
    simulator_flights = SimulatorFlight.objects.filter(pilot=pilot)

    actual = flights.aggregate(Sum('actual_instrument_time'))['actual_instrument_time__sum'] or 0
    flight_simulated = flights.aggregate(Sum('simulated_instrument_time'))['simulated_instrument_time__sum'] or 0
    simulator_simulated = simulator_flights.aggregate(Sum('simulated_instrument_time'))['simulated_instrument_time__sum'] or 0

    total_simulated = flight_simulated + simulator_simulated

    return {
        'actual': round(float(actual), 1),
        'flight_simulated': round(float(flight_simulated), 1),
        'simulator_simulated': round(float(simulator_simulated), 1),
        'simulated': round(float(total_simulated), 1),
        'total': round(float(actual + total_simulated), 1)
    }


def get_aircraft_breakdown(pilot):
    """Get flight hours broken down by aircraft with type and location information."""
    flights = Flight.objects.filter(pilot=pilot).select_related('plane', 'route').prefetch_related('route__route_steps__waypoint').order_by('plane', '-date')

    aircraft_data = {}
    for flight in flights:
        plane_name = str(flight.plane)
        if plane_name not in aircraft_data:
            # Get first waypoint from route for location
            location = None
            if flight.route:
                first_waypoint = flight.route.route_steps.order_by('sequence').first()
                if first_waypoint:
                    location = first_waypoint.waypoint.code

            aircraft_data[plane_name] = {
                'tail_number': plane_name,
                'type': flight.plane.type,
                'hours': 0,
                'location': location  # Location from most recent flight (since ordered by -date)
            }
        aircraft_data[plane_name]['hours'] += float(flight.flight_time)

    # Sort by hours (descending) and return as list of tuples with dict values
    return sorted(aircraft_data.values(), key=lambda x: x['hours'], reverse=True)


def get_recent_flights(pilot, limit=10):
    """Get the most recent N flights for a pilot with computed total landings."""
    flights = Flight.objects.filter(pilot=pilot).select_related('plane').order_by('-date')[:limit]

    # Add computed total landings to each flight
    flights_with_totals = []
    for flight in flights:
        flight.total_day_landings = flight.day_landings + flight.day_fullstop_landings
        flight.total_night_landings = flight.night_landings + flight.night_fullstop_landings
        flights_with_totals.append(flight)

    return flights_with_totals


def get_days_since_last_flight(pilot):
    """Calculate days since the pilot's last flight."""
    last_flight = Flight.objects.filter(pilot=pilot).order_by('-date').first()

    if not last_flight:
        return None

    days_since = (datetime.now().date() - last_flight.date).days
    return days_since


def get_cumulative_time_data(pilot):
    """Get cumulative time data for line chart (all flights chronologically)."""
    flights = Flight.objects.filter(pilot=pilot).order_by('date')

    cumulative_data = []
    total = 0
    pic = 0
    dual = 0
    instrument = 0

    for flight in flights:
        total += float(flight.flight_time)
        pic += float(flight.pic_time)
        dual += float(flight.flight_training_received)
        instrument += float(flight.actual_instrument_time + flight.simulated_instrument_time)

        cumulative_data.append({
            'date': flight.date.strftime('%Y-%m-%d'),
            'total': round(total, 1),
            'pic': round(pic, 1),
            'dual': round(dual, 1),
            'instrument': round(instrument, 1)
        })

    return cumulative_data


def get_xc_pic_time(pilot):
    """Calculate cross-country PIC time (flights with both xc_time > 0 and pic_time > 0)."""
    flights = Flight.objects.filter(pilot=pilot, xc_time__gt=0, pic_time__gt=0)
    xc_pic_total = flights.aggregate(Sum('xc_time'))['xc_time__sum'] or 0
    return round(float(xc_pic_total), 1)


def get_commercial_license_progress(pilot):
    """Calculate progress toward commercial pilot license requirements."""
    total_times = get_total_times(pilot)
    xc_pic_time = get_xc_pic_time(pilot)

    # Commercial requirements
    required_total = 250
    required_pic = 100
    required_xc_pic = 50

    current_total = total_times['total_time']
    current_pic = total_times['pic_time']

    return {
        'total_time': {
            'current': current_total,
            'required': required_total,
            'remaining': max(0, required_total - current_total),
            'percentage': min(100, (current_total / required_total) * 100)
        },
        'pic_time': {
            'current': current_pic,
            'required': required_pic,
            'remaining': max(0, required_pic - current_pic),
            'percentage': min(100, (current_pic / required_pic) * 100)
        },
        'xc_pic_time': {
            'current': xc_pic_time,
            'required': required_xc_pic,
            'remaining': max(0, required_xc_pic - xc_pic_time),
            'percentage': min(100, (xc_pic_time / required_xc_pic) * 100)
        }
    }


def get_instrument_rating_progress(pilot):
    """Calculate progress toward instrument rating (40 hours total, max 20 simulated from simulator, 50 hours XC PIC)."""
    instrument_breakdown = get_instrument_breakdown(pilot)
    xc_pic_time = get_xc_pic_time(pilot)

    actual = instrument_breakdown['actual']
    flight_simulated = instrument_breakdown['flight_simulated']
    simulator_simulated = instrument_breakdown['simulator_simulated']
    total_simulated = instrument_breakdown['simulated']

    # For IR, max 20 hours of SIMULATOR simulated time can be credited
    # Flight simulated time has no limit
    creditable_simulator_simulated = min(simulator_simulated, 20)
    creditable_simulated = flight_simulated + creditable_simulator_simulated
    creditable_total = actual + creditable_simulated

    remaining = max(0, 40 - creditable_total)
    percentage = min(100, (creditable_total / 40) * 100)

    # XC PIC requirement for IR
    required_xc_pic = 50
    xc_pic_remaining = max(0, required_xc_pic - xc_pic_time)
    xc_pic_percentage = min(100, (xc_pic_time / required_xc_pic) * 100)

    return {
        'actual': actual,
        'flight_simulated': flight_simulated,
        'simulator_simulated': simulator_simulated,
        'simulated': total_simulated,
        'creditable_simulated': round(creditable_simulated, 1),
        'creditable_total': round(creditable_total, 1),
        'remaining': round(remaining, 1),
        'percentage': round(percentage, 1),
        'xc_pic_time': xc_pic_time,
        'xc_pic_required': required_xc_pic,
        'xc_pic_remaining': round(xc_pic_remaining, 1),
        'xc_pic_percentage': round(xc_pic_percentage, 1)
    }


def get_passenger_leaderboard(pilot, limit=10):
    """Get leaderboard of passengers (Pilots with role PA) ranked by number of flights."""
    from pilots.models import Pilot

    # Get flights where the pilot was PIC and had passengers
    flights = Flight.objects.filter(pilot=pilot).prefetch_related('passengers')

    # Collect passenger statistics
    passenger_stats = {}
    for flight in flights:
        for passenger in flight.passengers.filter(role=Pilot.RoleChoices.PASSENGER):
            if passenger.id not in passenger_stats:
                passenger_stats[passenger.id] = {
                    'pilot': passenger,
                    'flight_count': 0,
                    'total_time': 0
                }
            passenger_stats[passenger.id]['flight_count'] += 1
            passenger_stats[passenger.id]['total_time'] += float(flight.flight_time)

    # Sort by flight count (descending), then by total time (descending) for ties
    leaderboard = sorted(
        passenger_stats.values(),
        key=lambda x: (x['flight_count'], x['total_time']),
        reverse=True
    )[:limit]

    # Round the total times
    for entry in leaderboard:
        entry['total_time'] = round(entry['total_time'], 1)

    return leaderboard


def get_instructor_leaderboard(pilot, limit=10):
    """Get leaderboard of instructors/examiners (Pilots with role I or E) ranked by total time (flights + ground)."""
    from pilots.models import Pilot

    # Get flights where the pilot received instruction
    flights = Flight.objects.filter(
        pilot=pilot,
        instructor__isnull=False
    ).select_related('instructor').filter(
        Q(instructor__role=Pilot.RoleChoices.INSTRUCTOR) |
        Q(instructor__role=Pilot.RoleChoices.EXAMINER)
    )

    # Get ground lessons where the pilot received instruction
    grounds = Ground.objects.filter(
        pilot=pilot,
    ).select_related('instructor').filter(
        Q(instructor__role=Pilot.RoleChoices.INSTRUCTOR) |
        Q(instructor__role=Pilot.RoleChoices.EXAMINER)
    )

    # Collect instructor statistics
    instructor_stats = {}

    # Process flights
    for flight in flights:
        instructor = flight.instructor
        if instructor.id not in instructor_stats:
            instructor_stats[instructor.id] = {
                'pilot': instructor,
                'flight_count': 0,
                'ground_count': 0,
                'flight_time': 0,
                'ground_time': 0,
                'total_time': 0
            }
        instructor_stats[instructor.id]['flight_count'] += 1
        flight_time = float(flight.flight_time)
        instructor_stats[instructor.id]['flight_time'] += flight_time
        instructor_stats[instructor.id]['total_time'] += flight_time

    # Process ground lessons
    for ground in grounds:
        instructor = ground.instructor
        if instructor.id not in instructor_stats:
            instructor_stats[instructor.id] = {
                'pilot': instructor,
                'flight_count': 0,
                'ground_count': 0,
                'flight_time': 0,
                'ground_time': 0,
                'total_time': 0
            }
        instructor_stats[instructor.id]['ground_count'] += 1
        ground_time = float(ground.ground_time)
        instructor_stats[instructor.id]['ground_time'] += ground_time
        instructor_stats[instructor.id]['total_time'] += ground_time

    # Sort by total time (descending)
    leaderboard = sorted(
        instructor_stats.values(),
        key=lambda x: x['total_time'],
        reverse=True
    )[:limit]

    # Round the times
    for entry in leaderboard:
        entry['flight_time'] = round(entry['flight_time'], 1)
        entry['ground_time'] = round(entry['ground_time'], 1)
        entry['total_time'] = round(entry['total_time'], 1)

    return leaderboard


def get_sel_total_hours(pilot):
    """Calculate total Single Engine Land (SEL) hours for a pilot."""
    flights = Flight.objects.filter(
        pilot=pilot,
        plane__plane_class='Single Engine Land'
    ).select_related('plane')

    sel_total = flights.aggregate(Sum('flight_time'))['flight_time__sum'] or 0
    return round(float(sel_total), 1)


def get_aircraft_class_breakdown(pilot):
    """Get breakdown of flight hours by aircraft class (SEL/MEL)."""
    flights = Flight.objects.filter(pilot=pilot).select_related('plane')

    class_data = flights.values('plane__plane_class').annotate(
        hours=Sum('flight_time'),
        flight_count=Count('id')
    )

    # Calculate total hours for percentage calculation
    total_hours = sum(float(entry['hours']) for entry in class_data)

    # Build structured breakdown
    breakdown = {}
    for entry in class_data:
        plane_class = entry['plane__plane_class']
        hours = float(entry['hours'])
        breakdown[plane_class] = {
            'hours': round(hours, 1),
            'flight_count': entry['flight_count'],
            'percentage': round((hours / total_hours * 100) if total_hours > 0 else 0, 1)
        }

    return breakdown


def get_aircraft_type_statistics(pilot):
    """Get statistics for each aircraft type flown."""
    flights = Flight.objects.filter(pilot=pilot).select_related('plane')

    type_data = flights.values('plane__type', 'plane__plane_class').annotate(
        hours=Sum('flight_time'),
        flight_count=Count('id')
    ).order_by('-hours')

    return [
        {
            'type': entry['plane__type'],
            'plane_class': entry['plane__plane_class'],
            'hours': round(float(entry['hours']), 1),
            'flight_count': entry['flight_count']
        }
        for entry in type_data
    ]


def get_aircraft_highlights(pilot):
    """Get highlights about aircraft usage (most/least flown, total unique)."""
    aircraft_breakdown = get_aircraft_breakdown(pilot)

    if not aircraft_breakdown:
        return {
            'most_flown': None,
            'least_flown': None,
            'total_aircraft': 0
        }

    return {
        'most_flown': aircraft_breakdown[0],  # First item (sorted by hours descending)
        'least_flown': aircraft_breakdown[-1],  # Last item
        'total_aircraft': len(aircraft_breakdown)
    }


def get_unique_people_counts(pilot):
    """Get counts of unique people the pilot has flown with."""
    from pilots.models import Pilot

    flights = Flight.objects.filter(pilot=pilot).prefetch_related('passengers').select_related('instructor')

    unique_passengers = set()
    unique_instructors = set()
    total_interactions = 0

    for flight in flights:
        # Count passengers
        passengers = flight.passengers.filter(role=Pilot.RoleChoices.PASSENGER)
        for passenger in passengers:
            unique_passengers.add(passenger.id)

        # Count instructors
        if flight.instructor and flight.instructor.role in [Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]:
            unique_instructors.add(flight.instructor.id)

        # Count total interactions (flights with people)
        if passengers.exists() or flight.instructor:
            total_interactions += 1

    return {
        'unique_passengers': len(unique_passengers),
        'unique_instructors': len(unique_instructors),
        'total_unique_people': len(unique_passengers | unique_instructors),
        'total_interactions': total_interactions
    }


def get_people_role_distribution(pilot):
    """Get distribution of flights by type (solo, with passengers, with instructor)."""
    from pilots.models import Pilot

    flights = Flight.objects.filter(pilot=pilot).prefetch_related('passengers').select_related('instructor')

    solo_flights = 0
    passenger_flights = 0
    instruction_flights = 0

    for flight in flights:
        has_passengers = flight.passengers.filter(role=Pilot.RoleChoices.PASSENGER).exists()
        has_instructor = flight.instructor and flight.instructor.role in [Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]

        if has_passengers:
            passenger_flights += 1
        if has_instructor:
            instruction_flights += 1
        if not has_passengers and not has_instructor:
            solo_flights += 1

    return {
        'solo_flights': solo_flights,
        'passenger_flights': passenger_flights,
        'instruction_flights': instruction_flights
    }


def get_monthly_people_frequency(pilot, months=12):
    """Get monthly breakdown of flights with people for the last N months."""
    from pilots.models import Pilot
    from dateutil.relativedelta import relativedelta

    # Get current date and calculate start date
    now = datetime.now().date()
    start_date = now - relativedelta(months=months-1)
    start_date = start_date.replace(day=1)

    # Get flights in date range
    flights = Flight.objects.filter(
        pilot=pilot,
        date__gte=start_date
    ).prefetch_related('passengers').select_related('instructor').order_by('date')

    # Build monthly data structure
    monthly_data = {}
    current = start_date
    for _ in range(months):
        month_key = datetime(current.year, current.month, 1).date()
        monthly_data[month_key] = {
            'month': current.strftime('%b %Y'),
            'total_flights': 0,
            'flights_with_passengers': 0,
            'flights_with_instruction': 0,
            'unique_passengers': set(),
            'unique_instructors': set()
        }
        current = current + relativedelta(months=1)

    # Process flights
    for flight in flights:
        month_key = datetime(flight.date.year, flight.date.month, 1).date()
        if month_key in monthly_data:
            monthly_data[month_key]['total_flights'] += 1

            # Check for passengers
            passengers = flight.passengers.filter(role=Pilot.RoleChoices.PASSENGER)
            if passengers.exists():
                monthly_data[month_key]['flights_with_passengers'] += 1
                for passenger in passengers:
                    monthly_data[month_key]['unique_passengers'].add(passenger.id)

            # Check for instructor
            if flight.instructor and flight.instructor.role in [Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]:
                monthly_data[month_key]['flights_with_instruction'] += 1
                monthly_data[month_key]['unique_instructors'].add(flight.instructor.id)

    # Convert sets to counts and return as list
    result = []
    for month_key in sorted(monthly_data.keys()):
        data = monthly_data[month_key]
        result.append({
            'month': data['month'],
            'total_flights': data['total_flights'],
            'flights_with_passengers': data['flights_with_passengers'],
            'flights_with_instruction': data['flights_with_instruction'],
            'unique_passengers': len(data['unique_passengers']),
            'unique_instructors': len(data['unique_instructors'])
        })

    return result


def get_people_insights(pilot):
    """Get insights about flying patterns with people."""
    from pilots.models import Pilot

    # Get leaderboards
    passenger_leaderboard = get_passenger_leaderboard(pilot, limit=1)
    instructor_leaderboard = get_instructor_leaderboard(pilot, limit=1)

    # Get total flight count
    total_flights = Flight.objects.filter(pilot=pilot).count()

    # Get counts by type
    flights = Flight.objects.filter(pilot=pilot).prefetch_related('passengers').select_related('instructor')

    flights_with_passengers = 0
    flights_with_instruction = 0

    for flight in flights:
        if flight.passengers.filter(role=Pilot.RoleChoices.PASSENGER).exists():
            flights_with_passengers += 1
        if flight.instructor and flight.instructor.role in [Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]:
            flights_with_instruction += 1

    # Calculate percentages
    passenger_percentage = round((flights_with_passengers / total_flights * 100) if total_flights > 0 else 0, 1)
    instruction_percentage = round((flights_with_instruction / total_flights * 100) if total_flights > 0 else 0, 1)

    # Build insights
    insights = {
        'most_frequent_passenger': passenger_leaderboard[0] if passenger_leaderboard else None,
        'most_frequent_instructor': instructor_leaderboard[0] if instructor_leaderboard else None,
        'passenger_flight_percentage': passenger_percentage,
        'instruction_flight_percentage': instruction_percentage
    }

    # Add percentages to leaderboard entries
    if insights['most_frequent_passenger']:
        insights['most_frequent_passenger']['percentage'] = round(
            (insights['most_frequent_passenger']['flight_count'] / flights_with_passengers * 100) if flights_with_passengers > 0 else 0, 1
        )

    if insights['most_frequent_instructor']:
        insights['most_frequent_instructor']['percentage'] = round(
            (insights['most_frequent_instructor']['flight_count'] / flights_with_instruction * 100) if flights_with_instruction > 0 else 0, 1
        )

    return insights


def get_instructor_time_progression(pilot):
    """Get cumulative time progression data for each instructor showing when instructors 'overtake' each other."""
    from pilots.models import Pilot

    # Get all flights with instructors, ordered chronologically
    flights = Flight.objects.filter(
        pilot=pilot,
        instructor__isnull=False
    ).select_related('instructor').filter(
        Q(instructor__role=Pilot.RoleChoices.INSTRUCTOR) |
        Q(instructor__role=Pilot.RoleChoices.EXAMINER)
    ).order_by('date')

    # Build cumulative time for each instructor
    instructor_cumulative = {}
    progression_data = []

    for flight in flights:
        instructor_id = flight.instructor.id
        instructor_name = str(flight.instructor)

        # Initialize instructor if not seen before
        if instructor_id not in instructor_cumulative:
            instructor_cumulative[instructor_id] = {
                'name': instructor_name,
                'cumulative_time': 0
            }

        # Add flight time to instructor's cumulative total
        instructor_cumulative[instructor_id]['cumulative_time'] += float(flight.flight_time)

        # Record this data point
        progression_data.append({
            'date': flight.date.strftime('%Y-%m-%d'),
            'instructor_id': instructor_id,
            'instructor_name': instructor_name,
            'cumulative_time': round(instructor_cumulative[instructor_id]['cumulative_time'], 1)
        })

    # Build datasets for Chart.js - one dataset per instructor
    instructors = {}
    for data_point in progression_data:
        instructor_id = data_point['instructor_id']
        if instructor_id not in instructors:
            instructors[instructor_id] = {
                'name': data_point['instructor_name'],
                'data': []
            }

    # For each unique date, record each instructor's cumulative time at that point
    # This ensures smooth lines even when an instructor doesn't fly on a particular date
    unique_dates = sorted(set(d['date'] for d in progression_data))

    for date in unique_dates:
        # Get the latest cumulative time for each instructor up to this date
        for instructor_id in instructors:
            # Find the last data point for this instructor up to this date
            instructor_data_up_to_date = [
                d for d in progression_data
                if d['instructor_id'] == instructor_id and d['date'] <= date
            ]

            if instructor_data_up_to_date:
                latest = instructor_data_up_to_date[-1]
                instructors[instructor_id]['data'].append({
                    'x': date,
                    'y': latest['cumulative_time']
                })

    return {
        'instructors': instructors,
        'progression_data': progression_data
    }
