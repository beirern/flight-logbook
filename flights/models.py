from django.contrib.auth.models import User
from django.db import models

from pilots.models import Pilot
from planes.models import Plane, Simulator
from routes.models import Route


# Create your models here.
class Flight(models.Model):
    pilot = models.ForeignKey(
        Pilot, related_name="as_flight_pilot", on_delete=models.CASCADE
    )
    instructor = models.ForeignKey(
        Pilot,
        related_name="as_flight_instructor",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    passengers = models.ManyToManyField(Pilot, related_name="as_passenger", blank=True)
    date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    flight_time = models.DecimalField(max_digits=19, decimal_places=1)
    plane = models.ForeignKey(Plane, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    pic_time = models.DecimalField(max_digits=19, decimal_places=1)
    sic_time = models.DecimalField(max_digits=19, decimal_places=1)
    flight_training_received = models.DecimalField(max_digits=19, decimal_places=1)
    xc_time = models.DecimalField(max_digits=19, decimal_places=1)
    day_time = models.DecimalField(max_digits=19, decimal_places=1)
    night_time = models.DecimalField(max_digits=19, decimal_places=1)
    actual_instrument_time = models.DecimalField(max_digits=19, decimal_places=1)
    simulated_instrument_time = models.DecimalField(max_digits=19, decimal_places=1)
    day_landings = models.IntegerField()
    day_fullstop_landings = models.IntegerField()
    night_landings = models.IntegerField()
    night_fullstop_landings = models.IntegerField()
    notes = models.TextField()
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.date}: {self.plane} {self.flight_time} {self.route}"


class Ground(models.Model):
    pilot = models.ForeignKey(
        Pilot, related_name="as_ground_pilot", on_delete=models.CASCADE
    )
    date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    ground_time = models.DecimalField(max_digits=19, decimal_places=1)
    instructor = models.ForeignKey(
        Pilot, related_name="as_ground_instructor", on_delete=models.CASCADE
    )
    subject = models.TextField()
    duration = models.DurationField(null=True, blank=True)

    def __str__(self):
        return f"{self.date}: {self.subject} {self.ground_time}"


class SimulatorFlight(models.Model):
    pilot = models.ForeignKey(
        Pilot, related_name="as_sim_pilot", on_delete=models.CASCADE
    )
    instructor = models.ForeignKey(
        Pilot, related_name="as_sim_instructor", on_delete=models.CASCADE
    )
    date = models.DateField()
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    sim_time = models.DecimalField(max_digits=19, decimal_places=1)
    plane = models.ForeignKey(Simulator, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    simulated_instrument_time = models.DecimalField(
        max_digits=19,
        decimal_places=1,
    )
    notes = models.TextField()

    def __str__(self):
        return f"{self.date}: {self.sim_time}"
