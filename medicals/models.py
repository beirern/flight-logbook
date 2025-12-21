from django.db import models


# Create your models here.
class Medical(models.Model):
    class ClassNumbers(models.IntegerChoices):
        FIRST = 1
        SECOND = 2
        THIRD = 3

    classNumber = models.IntegerField(choices=ClassNumbers.choices)
    expiration_years = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        if self.classNumber == 1:
            return "First Class"
        elif self.classNumber == 2:
            return "Second Class"
        return "Third Class"
