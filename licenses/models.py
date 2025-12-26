from django.db import models

from pilots.models import Pilot


class License(models.Model):
    class LicenseType(models.TextChoices):
        PPL = "PPL", "Private Pilot"
        INS = "INS", "Instrument"
        CFI = "CFI", "Certified Flight Instructor"
        CFII = "CFII", "Certified Flight Instructor w/ Instrument"

    type = models.CharField(max_length=6, choices=LicenseType.choices)
    pilot = models.ForeignKey(Pilot, on_delete=models.CASCADE, related_name="licenses")
    number = models.IntegerField()
    expiration = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.pilot}: {self.type} {self.number}"
