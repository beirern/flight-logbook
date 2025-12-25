"""
Django management command to export the flight logbook as a static site.

Usage:
    python manage.py export_static
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

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


class Command(BaseCommand):
    help = 'Export flight logbook as a static site for GitHub Pages deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='static_site',
            help='Output directory for static site (default: static_site/)'
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir'])

        self.stdout.write(self.style.SUCCESS('Starting static site export...'))

        # Get pilot (hardcoded to pk=1 for single-user mode)
        try:
            pilot = Pilot.objects.get(pk=1)
        except Pilot.DoesNotExist:
            self.stdout.write(self.style.ERROR('No pilot found with pk=1. Please create a pilot in the admin.'))
            return

        # Create output directories
        self._create_directories(output_dir)

        # Export data to JSON
        self._export_json_data(pilot, output_dir)

        # Render HTML pages
        self._render_html_pages(pilot, output_dir)

        # Copy static assets
        self._copy_static_assets(output_dir)

        # Create .nojekyll file
        (output_dir / '.nojekyll').touch()

        self.stdout.write(self.style.SUCCESS(f'\nStatic site exported successfully to {output_dir}/'))
        self.stdout.write(self.style.SUCCESS(f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'))

    def _create_directories(self, output_dir):
        """Create necessary directory structure."""
        self.stdout.write('Creating directory structure...')

        directories = [
            output_dir,
            output_dir / 'data',
            output_dir / 'assets',
            output_dir / 'assets' / 'css',
            output_dir / 'assets' / 'js',
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS('  ✓ Directories created'))

    def _export_json_data(self, pilot, output_dir):
        """Export flight data and statistics to JSON files."""
        self.stdout.write('Exporting JSON data...')

        data_dir = output_dir / 'data'

        # Export all flights
        flights = Flight.objects.filter(pilot=pilot).select_related('plane', 'instructor').prefetch_related('passengers').order_by('-date')
        flights_data = []

        for flight in flights:
            flights_data.append({
                'date': flight.date.isoformat(),
                'plane': str(flight.plane),
                'flight_time': float(flight.flight_time),
                'pic_time': float(flight.pic_time),
                'sic_time': float(flight.sic_time),
                'dual_time': float(flight.flight_training_received),
                'xc_time': float(flight.xc_time),
                'day_time': float(flight.day_time),
                'night_time': float(flight.night_time),
                'actual_instrument_time': float(flight.actual_instrument_time),
                'simulated_instrument_time': float(flight.simulated_instrument_time),
                'day_landings': flight.day_landings,
                'day_fullstop_landings': flight.day_fullstop_landings,
                'night_landings': flight.night_landings,
                'night_fullstop_landings': flight.night_fullstop_landings,
                'route': str(flight.route),
                'instructor': str(flight.instructor) if flight.instructor else None,
                'passengers': [str(p) for p in flight.passengers.all()],
                'notes': flight.notes,
            })

        with open(data_dir / 'flights.json', 'w') as f:
            json.dump(flights_data, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {len(flights_data)} flights'))

        # Export dashboard statistics
        stats = {
            'total_times': get_total_times(pilot),
            'currency': self._serialize_currency(check_passenger_currency(pilot)),
            'medical': self._serialize_medical(check_medical_status(pilot)),
            'ir_progress': get_instrument_rating_progress(pilot),
            'commercial_progress': get_commercial_license_progress(pilot),
            'instrument_breakdown': get_instrument_breakdown(pilot),
            'days_since_last_flight': get_days_since_last_flight(pilot),
            'last_updated': datetime.now().isoformat(),
        }

        with open(data_dir / 'stats.json', 'w') as f:
            json.dump(stats, f, indent=2)

        self.stdout.write(self.style.SUCCESS('  ✓ Exported statistics'))

        # Export chart data
        monthly_data = get_monthly_breakdown(pilot, months=12)
        cumulative_data = get_cumulative_time_data(pilot)
        aircraft_breakdown = get_aircraft_breakdown(pilot)

        charts = {
            'monthly_labels': [entry['month'] for entry in monthly_data],
            'monthly_hours': [entry['hours'] for entry in monthly_data],
            'cumulative_data': cumulative_data,
            'aircraft_breakdown': [{'name': aircraft['tail_number'], 'type': aircraft['type'], 'hours': aircraft['hours']} for aircraft in aircraft_breakdown],
        }

        with open(data_dir / 'charts.json', 'w') as f:
            json.dump(charts, f, indent=2)

        self.stdout.write(self.style.SUCCESS('  ✓ Exported chart data'))

        # Export leaderboards
        passenger_leaderboard = get_passenger_leaderboard(pilot, limit=10)
        instructor_leaderboard = get_instructor_leaderboard(pilot, limit=10)

        leaderboards = {
            'passengers': [
                {
                    'name': str(entry['pilot']),
                    'flight_count': entry['flight_count'],
                    'total_time': entry['total_time']
                }
                for entry in passenger_leaderboard
            ],
            'instructors': [
                {
                    'name': str(entry['pilot']),
                    'flight_count': entry['flight_count'],
                    'total_time': entry['total_time']
                }
                for entry in instructor_leaderboard
            ],
        }

        with open(data_dir / 'leaderboards.json', 'w') as f:
            json.dump(leaderboards, f, indent=2)

        self.stdout.write(self.style.SUCCESS('  ✓ Exported leaderboards'))

        # Export routes data for map
        flights_with_routes = Flight.objects.filter(pilot=pilot).select_related('route').prefetch_related('route__waypoints')
        unique_routes = {}
        route_counts = {}
        airport_visits = {}

        for flight in flights_with_routes:
            if flight.route:
                route_id = flight.route.id

                # Count flights for this route
                route_counts[route_id] = route_counts.get(route_id, 0) + 1

                # Count airport visits for this flight
                waypoints = flight.route.waypoints.all()
                for waypoint in waypoints:
                    airport_visits[waypoint.code] = airport_visits.get(waypoint.code, 0) + 1

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

        routes_list = list(unique_routes.values())

        with open(data_dir / 'routes.json', 'w') as f:
            json.dump(routes_list, f, indent=2)

        self.stdout.write(self.style.SUCCESS(f'  ✓ Exported {len(routes_list)} unique routes'))

    def _serialize_currency(self, currency):
        """Serialize currency data (convert dates to ISO format)."""
        return {
            'day_current': currency['day_current'],
            'day_landings': currency['day_landings'],
            'day_expiry': currency['day_expiry'].isoformat() if currency['day_expiry'] else None,
            'night_current': currency['night_current'],
            'night_landings': currency['night_landings'],
            'night_expiry': currency['night_expiry'].isoformat() if currency['night_expiry'] else None,
        }

    def _serialize_medical(self, medical):
        """Serialize medical data (convert dates to ISO format)."""
        return {
            'has_medical': medical['has_medical'],
            'class': medical['class'],
            'expiry': medical['expiry'].isoformat() if medical['expiry'] else None,
            'days_remaining': medical['days_remaining'],
            'status': medical['status'],
        }

    def _render_html_pages(self, pilot, output_dir):
        """Render HTML pages from Django templates."""
        self.stdout.write('Rendering HTML pages...')

        # Gather context data for dashboard
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

        dashboard_context = {
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
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_static': True,  # Flag to indicate static rendering
        }

        # Render dashboard
        dashboard_html = render_to_string('flights/dashboard.html', dashboard_context)
        with open(output_dir / 'index.html', 'w') as f:
            f.write(dashboard_html)

        self.stdout.write(self.style.SUCCESS('  ✓ Rendered dashboard (index.html)'))

        # Render logbook
        flights = Flight.objects.filter(pilot=pilot).select_related('plane', 'instructor').order_by('-date')

        logbook_context = {
            'flights': flights,
            'is_static': True,  # Flag to indicate static rendering
        }

        logbook_html = render_to_string('flights/logbook.html', logbook_context)
        with open(output_dir / 'logbook.html', 'w') as f:
            f.write(logbook_html)

        self.stdout.write(self.style.SUCCESS('  ✓ Rendered logbook (logbook.html)'))

        # Render routes map
        routes_context = {
            'is_static': True,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        routes_html = render_to_string('flights/routes_map.html', routes_context)
        with open(output_dir / 'routes.html', 'w') as f:
            f.write(routes_html)

        self.stdout.write(self.style.SUCCESS('  ✓ Rendered routes map (routes.html)'))

    def _copy_static_assets(self, output_dir):
        """Copy static assets (CSS, JS, images) to output directory."""
        self.stdout.write('Copying static assets...')

        # Check if staticfiles directory exists (after collectstatic)
        staticfiles_dir = Path(settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT else None

        if staticfiles_dir and staticfiles_dir.exists():
            # Copy from collected static files
            dest_assets = output_dir / 'assets'

            # Copy CSS
            css_src = staticfiles_dir / 'css'
            if css_src.exists():
                shutil.copytree(css_src, dest_assets / 'css', dirs_exist_ok=True)

            # Copy JS
            js_src = staticfiles_dir / 'js'
            if js_src.exists():
                shutil.copytree(js_src, dest_assets / 'js', dirs_exist_ok=True)

            # Copy images if they exist
            img_src = staticfiles_dir / 'images'
            if img_src.exists():
                shutil.copytree(img_src, dest_assets / 'images', dirs_exist_ok=True)

            self.stdout.write(self.style.SUCCESS('  ✓ Static assets copied'))
        else:
            self.stdout.write(self.style.WARNING('  ⚠ Static files not found. Run "python manage.py collectstatic" first, or assets will be loaded from CDN.'))
