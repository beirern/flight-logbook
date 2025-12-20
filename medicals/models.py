from django.db import models

# Create your models here.
class Medical(models.Model):
    class ClassNumbers(models.IntegerChoices):
        FIRST = 1
        SECOND = 2
        THIRD = 3

    classNumber = models.IntegerField(choices=ClassNumbers.choices)
    expiration_years = models.PositiveSmallIntegerField(null=True, blank=True)