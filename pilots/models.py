from django.db import models


class Pilot(models.Model):
    class RoleChoices(models.TextChoices):
        PILOT = "PI"
        INSTRUCTOR = "I"
        EXAMINER = "E"
        PASSENGER = "PA"

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(choices=RoleChoices.choices, max_length=2)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
