from django.db import models


class License(models.Model):
    name = models.CharField(max_length=50)
    number = models.IntegerField()
    expiration = models.DateField()

    def __str__(self):
        return self.name
