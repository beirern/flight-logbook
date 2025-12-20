from django.contrib.auth.models import User
from django.db import models

from pilots.models import Pilot
from planes.models import Plane


# Create your models here.
class Flight(models.Model):
    pilot = models.ForeignKey(Pilot, related_name='as_flight_pilot', on_delete=models.CASCADE)
    instructor = models.ForeignKey(Pilot, related_name='as_flight_instructor', on_delete=models.CASCADE)
    passengers = models.ManyToManyField(Pilot, related_name='as_passenger', blank=True)
    date = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField()
    plane = models.ForeignKey(Plane, on_delete=models.CASCADE)
    route = models.JSONField(default=list)
    pic_time = models.DecimalField(max_digits=19, decimal_places=1)
    sic_time = models.DecimalField(max_digits=19, decimal_places=1)
    flight_training_received = models.DecimalField(max_digits=19, decimal_places=1)
    xc_time = models.DecimalField(max_digits=19, decimal_places=1)
    solo_time = models.DecimalField(max_digits=19, decimal_places=1)
    day_time = models.DecimalField(max_digits=19, decimal_places=1)
    night_time = models.DecimalField(max_digits=19, decimal_places=1)
    actual_instrument_time = models.DecimalField(max_digits=19, decimal_places=1)
    simulated_instrument_time = models.DecimalField(max_digits=19, decimal_places=1)
    day_landings = models.IntegerField()
    day_fullstop_landings = models.IntegerField()
    night_landings = models.IntegerField()
    night_fullstop_landings = models.IntegerField()
    single_engine_land_time = models.DecimalField(max_digits=19, decimal_places=1)
    notes = models.TextField()
    duration = models.DurationField(null=True, blank=True)

class Ground(models.Model):
    pilot = models.ForeignKey(Pilot, related_name='as_ground_pilot', on_delete=models.CASCADE)
    date = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField()
    instructor = models.ForeignKey(Pilot, related_name='as_ground_instructor', on_delete=models.CASCADE)
    subject = models.TextField()
    endorsement = models.TextField()

class Simulator(models.Model):
    pilot = models.ForeignKey(Pilot, related_name='as_sim_pilot', on_delete=models.CASCADE)
    date = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField()
    plane = models.ForeignKey(Plane, on_delete=models.CASCADE)
    route = models.JSONField(default=list)
    simulated_instrument_time = models.DecimalField(max_digits=19, decimal_places=1)

    notes = models.TextField()