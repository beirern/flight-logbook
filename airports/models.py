from django.db import models


# Create your models here.
class Airport(models.Model):
    code = models.TextField(max_length=4)
    name = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    municipality = models.TextField()
