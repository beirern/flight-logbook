from django.db import models


class Plane(models.Model):
    class PlaneClass(models.TextChoices):
        SEL = "Single Engine Land"
        MEL = "Multi Engine Land"

    tail_number = models.CharField(max_length=6)
    type = models.CharField(max_length=4)
    plane_class = models.CharField(choices=PlaneClass.choices, max_length=20)

    def __str__(self):
        return self.tail_number


class Simulator(models.Model):
    class SimClass(models.TextChoices):
        FTD = "FTD"
        FFS = "FFS"
        BATD = "BATD"
        AATD = "AATD"

    tail_number = models.CharField(max_length=6)
    type = models.CharField(max_length=20)
    sim_class = models.CharField(choices=SimClass.choices, max_length=4)

    def __str__(self):
        return self.tail_number
