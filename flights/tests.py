from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from flights.forms import FlightForm
from flights.models import Flight
from flights.utils.currency_calculator import check_passenger_currency, days_until_currency_expires
from pilots.models import Pilot
from planes.models import Plane
from routes.models import Airport, Route, RouteWaypoint


class PassengerCurrencyTests(TestCase):
    def setUp(self):
        self.today = date(2026, 10, 18)
        clock = patch("flights.utils.currency_calculator.datetime")
        self.clock = clock.start()
        self.addCleanup(clock.stop)
        self.clock.now.return_value.date.return_value = self.today
        self.pilot = Pilot.objects.create(first_name="Me", last_name="Pilot", role=Pilot.RoleChoices.PILOT)
        self.plane = Plane.objects.create(tail_number="N123AB", type="C172", plane_class=Plane.PlaneClass.SEL)
        self.route = Route.objects.create(name="Local")

    def add_flight(self, days_ago=0, **overrides):
        data = dict(
            pilot=self.pilot, plane=self.plane, route=self.route,
            date=self.today - timedelta(days=days_ago),
            flight_time=1, pic_time=1, sic_time=0, flight_training_received=0,
            xc_time=0, day_time=0, night_time=0, actual_instrument_time=0,
            simulated_instrument_time=0, day_landings=0, day_fullstop_landings=0,
            night_landings=0, night_fullstop_landings=0, notes="",
        )
        data.update(overrides)
        return Flight.objects.create(**data)

    def test_night_fullstop_landings_make_both_currencies_current(self):
        flight = self.add_flight(days_ago=10, night_fullstop_landings=3)
        currency = check_passenger_currency(self.pilot)
        for period in ("day", "night"):
            self.assertTrue(currency[f"{period}_current"])
            self.assertEqual(currency[f"{period}_landings"], 3)
            self.assertEqual(currency[f"{period}_expiry"], flight.date + timedelta(days=90))
            self.assertEqual(days_until_currency_expires(self.pilot, period), 80)

    def test_day_landings_only_count_toward_day_currency(self):
        self.add_flight(day_landings=2, day_fullstop_landings=1)
        currency = check_passenger_currency(self.pilot)
        self.assertTrue(currency["day_current"])
        self.assertEqual(currency["day_landings"], 3)
        self.assertFalse(currency["night_current"])
        self.assertEqual(currency["night_landings"], 0)
        self.assertIsNone(currency["night_expiry"])

    def test_night_non_fullstop_landings_only_count_toward_day_currency(self):
        flight = self.add_flight(night_landings=3)
        currency = check_passenger_currency(self.pilot)
        self.assertTrue(currency["day_current"])
        self.assertEqual(currency["day_landings"], 3)
        self.assertEqual(currency["day_expiry"], flight.date + timedelta(days=90))
        self.assertFalse(currency["night_current"])
        self.assertEqual(currency["night_landings"], 0)
        self.assertIsNone(currency["night_expiry"])

    def test_mixed_landings_use_third_most_recent_landing_for_day_expiry(self):
        self.add_flight(days_ago=1, day_landings=1)
        self.add_flight(days_ago=5, night_landings=1)
        third = self.add_flight(days_ago=20, night_fullstop_landings=1)
        self.add_flight(days_ago=40, day_fullstop_landings=1)
        currency = check_passenger_currency(self.pilot)
        self.assertTrue(currency["day_current"])
        self.assertEqual(currency["day_landings"], 4)
        self.assertEqual(currency["day_expiry"], third.date + timedelta(days=90))
        self.assertFalse(currency["night_current"])
        self.assertEqual(currency["night_landings"], 1)

    def test_excluded_old_and_other_pilot_landings_do_not_grant_currency(self):
        self.add_flight(days_ago=91, night_fullstop_landings=3)
        self.add_flight(excluded=True, night_fullstop_landings=3)
        other_pilot = Pilot.objects.create(first_name="Other", last_name="Pilot", role=Pilot.RoleChoices.PILOT)
        self.add_flight(pilot=other_pilot, night_fullstop_landings=3)
        currency = check_passenger_currency(self.pilot)
        for period in ("day", "night"):
            self.assertFalse(currency[f"{period}_current"])
            self.assertEqual(currency[f"{period}_landings"], 0)
            self.assertEqual(currency[f"{period}_expiry"], self.today - timedelta(days=1))
            self.assertIsNone(days_until_currency_expires(self.pilot, period))


class FlightFormZeroDefaultTests(TestCase):
    """The Flight model has no default=0 on its numeric fields (by design - not
    modified for this feature), so the form must supply the default itself."""

    def setUp(self):
        self.pilot = Pilot.objects.create(pk=1, first_name="Me", last_name="Pilot", role=Pilot.RoleChoices.PILOT)
        self.plane = Plane.objects.create(tail_number="N123AB", type="C172", plane_class=Plane.PlaneClass.SEL)
        self.route = Route.objects.create(name="Local")

    def _base_data(self, **overrides):
        data = {
            "date": "2026-08-20",
            "flight_time": "1.5",
            "plane": self.plane.id,
            "route": self.route.id,
            "flight_training_received": "0",
            "notes": "Pattern work",
        }
        data.update(overrides)
        return data

    def test_blank_numeric_fields_default_to_zero(self):
        form = FlightForm(data=self._base_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["pic_time"], 0)
        self.assertEqual(form.cleaned_data["day_landings"], 0)
        self.assertEqual(form.cleaned_data["holds"], 0)

    def test_provided_numeric_values_are_not_clobbered(self):
        form = FlightForm(data=self._base_data(pic_time="1.5", day_landings="3"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(float(form.cleaned_data["pic_time"]), 1.5)
        self.assertEqual(form.cleaned_data["day_landings"], 3)

    def test_route_is_still_required(self):
        form = FlightForm(data=self._base_data(route=""))
        self.assertFalse(form.is_valid())
        self.assertIn("route", form.errors)

    def test_instructor_field_limited_to_instructor_and_examiner_roles(self):
        form = FlightForm()
        roles = set(form.fields["instructor"].queryset.values_list("role", flat=True).distinct())
        self.assertTrue(roles <= {Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER})

    def test_passengers_field_limited_to_passenger_role(self):
        form = FlightForm()
        roles = set(form.fields["passengers"].queryset.values_list("role", flat=True).distinct())
        self.assertTrue(roles <= {Pilot.RoleChoices.PASSENGER})


class AddFlightViewAccessTests(TestCase):
    def setUp(self):
        self.pilot = Pilot.objects.create(pk=1, first_name="Me", last_name="Pilot", role=Pilot.RoleChoices.PILOT)
        User = get_user_model()
        self.staff_user = User.objects.create_user(username="staff", password="pw", is_staff=True)
        self.regular_user = User.objects.create_user(username="regular", password="pw", is_staff=False)

    def test_anonymous_redirected_to_admin_login(self):
        response = self.client.get(reverse("add_flight"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_non_staff_redirected_to_admin_login(self):
        self.client.login(username="regular", password="pw")
        response = self.client.get(reverse("add_flight"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_staff_can_view_page(self):
        self.client.login(username="staff", password="pw")
        response = self.client.get(reverse("add_flight"))
        self.assertEqual(response.status_code, 200)

    def test_search_endpoints_require_staff(self):
        for url_name in ("search_routes", "search_instructors", "search_passengers", "search_airports"):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 302, url_name)


class SearchEndpointQueryCountTests(TestCase):
    """Guards against the N+1 pattern that makes the admin page slow: search
    endpoints must resolve in a small, constant number of queries regardless
    of how many routes/airports exist."""

    def setUp(self):
        self.pilot = Pilot.objects.create(pk=1, first_name="Me", last_name="Pilot", role=Pilot.RoleChoices.PILOT)
        User = get_user_model()
        self.staff_user = get_user_model().objects.create_user(username="staff", password="pw", is_staff=True)
        self.client.login(username="staff", password="pw")

        for i in range(15):
            airport_a = Airport.objects.create(
                code=f"K{i:03d}", name=f"Airport {i}", latitude=0, longitude=0, country="US", municipality="Town"
            )
            airport_b = Airport.objects.create(
                code=f"J{i:03d}", name=f"Airport J{i}", latitude=0, longitude=0, country="US", municipality="Town"
            )
            route = Route.objects.create(name=f"Route {i}")
            RouteWaypoint.objects.create(route=route, waypoint=airport_a, sequence=1)
            RouteWaypoint.objects.create(route=route, waypoint=airport_b, sequence=2)
            Flight.objects.create(
                pilot=self.pilot,
                date="2026-08-01",
                flight_time=1,
                plane=Plane.objects.create(tail_number=f"N{i}", type="C172", plane_class=Plane.PlaneClass.SEL),
                route=route,
                pic_time=1,
                sic_time=0,
                flight_training_received=0,
                xc_time=0,
                day_time=1,
                night_time=0,
                actual_instrument_time=0,
                simulated_instrument_time=0,
                day_landings=1,
                day_fullstop_landings=1,
                night_landings=0,
                night_fullstop_landings=0,
                notes="",
            )

    def test_route_search_has_bounded_query_count(self):
        # session + user (auth) + pilot lookup + routes query
        # + prefetch_related("route_steps__waypoint") (2 queries) = 6,
        # regardless of how many routes/waypoints exist.
        with self.assertNumQueries(6):
            response = self.client.get(reverse("search_routes"), {"q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.json()["results"]), 8)

    def test_airport_search_has_bounded_query_count(self):
        # session + user (auth) + airports query
        with self.assertNumQueries(3):
            response = self.client.get(reverse("search_airports"), {"q": "K"})
        self.assertEqual(response.status_code, 200)
