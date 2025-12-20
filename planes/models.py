from django.db import models

# Create your models here.
class Plane(models.Model):
    tail_number = models.CharField(max_length=6)
    type = models.CharField(max_length=4)

class Simulator(models.Model):
    class SimType(models.TextChoices):
        FTD = 'FTD'
        FFS = 'FFS'
        BATD = 'BATD'
        AATD = 'AATD'

    tail_number = models.CharField(max_length=6)
    type = models.CharField(max_length=20)
    sim_type = models.CharField(choices=SimType.choices, max_length=4)