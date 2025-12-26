from datetime import date
from dateutil.relativedelta import relativedelta

from django.db import models

from pilots.models import Pilot


class Medical(models.Model):
    class ClassNumbers(models.IntegerChoices):
        FIRST = 1
        SECOND = 2
        THIRD = 3

    classNumber = models.IntegerField(choices=ClassNumbers.choices)
    examination_date = models.DateField()
    examiner_name = models.CharField(max_length=50)
    examiner_designation_number = models.CharField(max_length=9)
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

    def get_first_class_expiry(self):
        """Calculate when 1st class privileges expire (12 calendar months)."""
        if self.classNumber != 1:
            return None
        # Last day of the month, 12 months after examination
        expiry = self.examination_date + relativedelta(months=12)
        # Get last day of that month
        next_month = expiry + relativedelta(months=1, day=1)
        return next_month - relativedelta(days=1)

    def get_second_class_expiry(self):
        """Calculate when 2nd class privileges expire (12 calendar months)."""
        if self.classNumber not in [1, 2]:
            return None
        # Last day of the month, 12 months after examination
        expiry = self.examination_date + relativedelta(months=12)
        # Get last day of that month
        next_month = expiry + relativedelta(months=1, day=1)
        return next_month - relativedelta(days=1)

    def get_third_class_expiry(self):
        """Calculate when 3rd class privileges expire (60 calendar months)."""
        # All medical classes can exercise 3rd class privileges
        # Last day of the month, 60 months after examination
        expiry = self.examination_date + relativedelta(months=60)
        # Get last day of that month
        next_month = expiry + relativedelta(months=1, day=1)
        return next_month - relativedelta(days=1)

    def get_current_privilege_level(self, as_of_date=None):
        """
        Determine the current privilege level this medical allows.

        Returns:
            int: 1, 2, 3, or None if expired
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Check 1st class (only if original cert was 1st class)
        if self.classNumber == 1:
            first_expiry = self.get_first_class_expiry()
            if as_of_date <= first_expiry:
                return 1

        # Check 2nd class (if original cert was 1st or 2nd class)
        if self.classNumber in [1, 2]:
            second_expiry = self.get_second_class_expiry()
            if as_of_date <= second_expiry:
                return 2

        # Check 3rd class (all certs can exercise 3rd class)
        third_expiry = self.get_third_class_expiry()
        if as_of_date <= third_expiry:
            return 3

        # Completely expired
        return None

    def get_next_expiration_date(self, as_of_date=None):
        """Get the next upcoming expiration date for current privileges."""
        if as_of_date is None:
            as_of_date = date.today()

        current_level = self.get_current_privilege_level(as_of_date)

        if current_level == 1:
            return self.get_first_class_expiry()
        elif current_level == 2:
            return self.get_second_class_expiry()
        elif current_level == 3:
            return self.get_third_class_expiry()

        # Already expired
        return None
