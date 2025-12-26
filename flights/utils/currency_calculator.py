from datetime import datetime, timedelta

from django.db.models import Sum

from flights.models import Flight


def check_passenger_currency(pilot):
    """
    Check passenger carrying currency per FAR 61.57(a).
    Requires 3 takeoffs and landings in the preceding 90 days.
    """
    ninety_days_ago = datetime.now().date() - timedelta(days=90)
    recent_flights = Flight.objects.filter(pilot=pilot, date__gte=ninety_days_ago)

    day_landings = recent_flights.aggregate(Sum('day_landings'))['day_landings__sum'] or 0
    night_fullstop_landings = recent_flights.aggregate(Sum('night_fullstop_landings'))['night_fullstop_landings__sum'] or 0

    # Find the date when currency expires (90 days from the 3rd landing)
    day_expiry = None
    night_expiry = None

    # Calculate day currency expiration
    day_landing_flights = Flight.objects.filter(
        pilot=pilot,
        day_landings__gt=0
    ).order_by('-date')

    day_count = 0
    for flight in day_landing_flights:
        day_count += flight.day_landings
        if day_count >= 3:
            day_expiry = flight.date + timedelta(days=90)
            break

    # Calculate night currency expiration
    night_landing_flights = Flight.objects.filter(
        pilot=pilot,
        night_fullstop_landings__gt=0
    ).order_by('-date')

    night_count = 0
    for flight in night_landing_flights:
        night_count += flight.night_fullstop_landings
        if night_count >= 3:
            night_expiry = flight.date + timedelta(days=90)
            break

    return {
        'day_current': day_landings >= 3,
        'day_landings': day_landings,
        'day_expiry': day_expiry,
        'night_current': night_fullstop_landings >= 3,
        'night_landings': night_fullstop_landings,
        'night_expiry': night_expiry,
    }


def check_medical_status(pilot):
    """
    Check medical certificate status.
    Returns the most recent medical and days until expiration.
    """
    from medicals.models import Medical

    try:
        latest_medical = Medical.objects.filter(pilot=pilot).order_by('-examination_date').first()

        if not latest_medical:
            return {
                'has_medical': False,
                'original_class': None,
                'current_class': None,
                'examination_date': None,
                'expiry': None,
                'first_class_expiry': None,
                'second_class_expiry': None,
                'third_class_expiry': None,
                'days_remaining': None,
                'status': 'none'
            }

        current_privilege = latest_medical.get_current_privilege_level()
        next_expiry = latest_medical.get_next_expiration_date()

        if next_expiry:
            days_remaining = (next_expiry - datetime.now().date()).days
        else:
            days_remaining = None

        # Determine status color coding
        if current_privilege is None:
            status = 'expired'
        elif days_remaining is not None:
            if days_remaining < 30:
                status = 'critical'
            elif days_remaining < 60:
                status = 'warning'
            else:
                status = 'current'
        else:
            status = 'expired'

        return {
            'has_medical': True,
            'original_class': latest_medical.classNumber,
            'current_class': current_privilege,
            'examination_date': latest_medical.examination_date,
            'expiry': next_expiry,
            'first_class_expiry': latest_medical.get_first_class_expiry(),
            'second_class_expiry': latest_medical.get_second_class_expiry(),
            'third_class_expiry': latest_medical.get_third_class_expiry(),
            'days_remaining': days_remaining,
            'status': status
        }

    except Exception:
        # If medicals app doesn't have the expected structure
        return {
            'has_medical': False,
            'original_class': None,
            'current_class': None,
            'examination_date': None,
            'expiry': None,
            'first_class_expiry': None,
            'second_class_expiry': None,
            'third_class_expiry': None,
            'days_remaining': None,
            'status': 'none'
        }


def days_until_currency_expires(pilot, currency_type='day'):
    """
    Calculate days until a specific currency type expires.

    Args:
        pilot: Pilot instance
        currency_type: 'day' or 'night'

    Returns:
        Number of days until expiry, or None if not current
    """
    currency = check_passenger_currency(pilot)

    if currency_type == 'day':
        if not currency['day_current']:
            return None
        if currency['day_expiry']:
            return (currency['day_expiry'] - datetime.now().date()).days
    elif currency_type == 'night':
        if not currency['night_current']:
            return None
        if currency['night_expiry']:
            return (currency['night_expiry'] - datetime.now().date()).days

    return None
