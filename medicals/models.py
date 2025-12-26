from django.db import models

from pilots.models import Pilot


class Medical(models.Model):
    class ClassNumbers(models.IntegerChoices):
        FIRST = 1
        SECOND = 2
        THIRD = 3

    classNumber = models.IntegerField(choices=ClassNumbers.choices)
    number = models.IntegerField()
    pilot = models.ForeignKey(Pilot, on_delete=models.CASCADE, related_name="medical")

    def __str__(self):
        res = str(self.pilot)
        if self.classNumber == 1:
            res += " First Class"
        elif self.classNumber == 2:
            res += " Second Class"
        else:
            res += " Third Class"
        return res
