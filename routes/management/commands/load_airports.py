"""
Django management command to import airport data from https://ourairports.com/data/

Usage:
    python manage.py load_airports
"""

from django.core.management.base import BaseCommand
import csv

from routes.models import Airport


class Command(BaseCommand):
    help = "Takes airport.csv file from https://ourairports.com/data/ and puts it in DB"  # A helpful description
    file = "airports.csv"

    def handle(self, *args, **options):
        airports = []
        try:
            with open(self.file) as csv_file:
                csv_reader = csv.DictReader(csv_file, delimiter=",")
                count, _ = Airport.objects.all().delete()
                self.stdout.write(
                    self.style.WARNING(f"Deleted {count} existing records.")
                )
                skipped_airports = 0
                for row in csv_reader:
                    if not self._validate_airport(row):
                        skipped_airports += 1
                        continue
                    name = row["name"]
                    latitude = float(row["latitude_deg"])
                    longitude = float(row["longitude_deg"])
                    country = row["iso_country"]
                    municipality = row["municipality"]
                    if row["icao_code"]:
                        code = row["icao_code"]
                    else:
                        code = row["ident"]

                    airports.append(
                        Airport(
                            code=code,
                            name=name,
                            latitude=latitude,
                            longitude=longitude,
                            country=country,
                            municipality=municipality,
                        )
                    )
            Airport.objects.bulk_create(airports)
            self.stdout.write(
                self.style.WARNING(f"Skipped {skipped_airports} airport records")
            )
            self.stdout.write(
                self.style.SUCCESS(f"Imported {len(airports)} airport records")
            )
        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(f"{self.file} not found! Cannot import airport info!")
            )
            exit(1)

    def _validate_airport(self, row):
        """
        Validates airport entry
        :param row: airport info from csv file
        :returns: Whether to add this row to DB
        :rtype: bool
        """
        # For now just get airports with code length <= 4
        if (
            (not row["icao_code"] and (not row["ident"]) or len(row["ident"]) > 4)
            or not row["name"]
            or not row["latitude_deg"]
            or not row["longitude_deg"]
            or not row["municipality"]
            or not row["iso_country"]
        ):
            return False
        return True
