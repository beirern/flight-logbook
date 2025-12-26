from django.db import models

from pilots.models import Pilot


class License(models.Model):
    class LicenseType(models.TextChoices):
        PPL = "Private"
        INS = "Instrument"
        CFI = "Certified Flight Instructor"
        CFII = "Certified Flight Instructor w/ Instrument"

    type = models.CharField(max_length=6)
    pilot = models.ForeignKey(Pilot, on_delete=models.CASCADE, related_name="licenses")
    number = models.IntegerField()
    expiration = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.pilot}: {self.type} {self.number}"
