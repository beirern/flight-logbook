from django.db import models
from medicals.models import Medical
from licenses.models import License


# Create your models here.
class Pilot(models.Model):
    class RoleChoices(models.TextChoices):
        PILOT = "PI"
        INSTRUCTOR = "I"
        EXAMINER = "E"
        PASSENGER = "PA"

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    role = models.CharField(choices=RoleChoices.choices, max_length=2)
    medical_certificate = models.ForeignKey(
        Medical, on_delete=models.CASCADE, null=True, blank=True
    )
    licenses = models.ManyToManyField(License, related_name="licenses", blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
