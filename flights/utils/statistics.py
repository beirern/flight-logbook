from datetime import datetime, timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth

from flights.models import Flight


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
    """Get flight hours broken down by month for the last N months."""
    start_date = datetime.now().date() - timedelta(days=30 * months)

    monthly = Flight.objects.filter(
        pilot=pilot,
        date__gte=start_date
    ).annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        hours=Sum('flight_time')
    ).order_by('month')

    return [
        {
            'month': entry['month'].strftime('%b %Y'),
            'hours': float(entry['hours']) if entry['hours'] else 0
        }
        for entry in monthly
    ]


def get_instrument_breakdown(pilot):
    """Get breakdown of instrument time (actual vs simulated)."""
    flights = Flight.objects.filter(pilot=pilot)

    actual = flights.aggregate(Sum('actual_instrument_time'))['actual_instrument_time__sum'] or 0
    simulated = flights.aggregate(Sum('simulated_instrument_time'))['simulated_instrument_time__sum'] or 0

    return {
        'actual': round(float(actual), 1),
        'simulated': round(float(simulated), 1),
        'total': round(float(actual + simulated), 1)
    }


def get_aircraft_breakdown(pilot):
    """Get flight hours broken down by aircraft."""
    flights = Flight.objects.filter(pilot=pilot).select_related('plane')

    aircraft_hours = {}
    for flight in flights:
        plane_name = str(flight.plane)
        if plane_name in aircraft_hours:
            aircraft_hours[plane_name] += float(flight.flight_time)
        else:
            aircraft_hours[plane_name] = float(flight.flight_time)

    return sorted(aircraft_hours.items(), key=lambda x: x[1], reverse=True)


def get_recent_flights(pilot, limit=10):
    """Get the most recent N flights for a pilot."""
    return Flight.objects.filter(pilot=pilot).select_related('plane').order_by('-date')[:limit]


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
    """Calculate progress toward instrument rating (40 hours total, max 20 simulated, 50 hours XC PIC)."""
    instrument_breakdown = get_instrument_breakdown(pilot)
    xc_pic_time = get_xc_pic_time(pilot)

    actual = instrument_breakdown['actual']
    simulated = instrument_breakdown['simulated']
    total_instrument = instrument_breakdown['total']

    # For IR, max 20 hours can be simulated
    creditable_simulated = min(simulated, 20)
    creditable_total = actual + creditable_simulated

    remaining = max(0, 40 - creditable_total)
    percentage = min(100, (creditable_total / 40) * 100)

    # XC PIC requirement for IR
    required_xc_pic = 50
    xc_pic_remaining = max(0, required_xc_pic - xc_pic_time)
    xc_pic_percentage = min(100, (xc_pic_time / required_xc_pic) * 100)

    return {
        'actual': actual,
        'simulated': simulated,
        'creditable_simulated': creditable_simulated,
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

    # Sort by flight count (descending) and return top N
    leaderboard = sorted(
        passenger_stats.values(),
        key=lambda x: x['flight_count'],
        reverse=True
    )[:limit]

    # Round the total times
    for entry in leaderboard:
        entry['total_time'] = round(entry['total_time'], 1)

    return leaderboard


def get_instructor_leaderboard(pilot, limit=10):
    """Get leaderboard of instructors/examiners (Pilots with role I or E) ranked by number of flights."""
    from pilots.models import Pilot

    # Get flights where the pilot received instruction
    flights = Flight.objects.filter(
        pilot=pilot,
        instructor__isnull=False
    ).select_related('instructor').filter(
        Q(instructor__role=Pilot.RoleChoices.INSTRUCTOR) |
        Q(instructor__role=Pilot.RoleChoices.EXAMINER)
    )

    # Collect instructor statistics
    instructor_stats = {}
    for flight in flights:
        instructor = flight.instructor
        if instructor.id not in instructor_stats:
            instructor_stats[instructor.id] = {
                'pilot': instructor,
                'flight_count': 0,
                'total_time': 0
            }
        instructor_stats[instructor.id]['flight_count'] += 1
        instructor_stats[instructor.id]['total_time'] += float(flight.flight_time)

    # Sort by flight count (descending) and return top N
    leaderboard = sorted(
        instructor_stats.values(),
        key=lambda x: x['flight_count'],
        reverse=True
    )[:limit]

    # Round the total times
    for entry in leaderboard:
        entry['total_time'] = round(entry['total_time'], 1)

    return leaderboard
