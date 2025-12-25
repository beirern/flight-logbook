from django.db import models


# Create your models here.
class Airport(models.Model):
    code = models.CharField(max_length=4)
    name = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    country = models.CharField(max_length=2)
    municipality = models.TextField()

    def __str__(self):
        return f"{self.code} - {self.name}"


class Route(models.Model):
    name = models.TextField()
    waypoints = models.ManyToManyField(
        Airport, through="RouteWaypoint", related_name="flights_through"
    )

    def __str__(self):
        # 1. Fetch the waypoint codes associated with this route in order
        # We use 'route_steps' because that is the related_name on the RouteWaypoint model
        stops = (
            self.route_steps.all()
            .order_by("sequence")
            .values_list("waypoint__code", flat=True)
        )

        # 2. Join them: "KBFI -> KRNT -> KBFI"
        path_string = " -> ".join(stops) if stops else "No waypoints assigned"

        # 3. Return the name + the path
        return f"{self.name}: ({path_string})"


class RouteWaypoint(models.Model):
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE, related_name="route_steps"
    )
    waypoint = models.ForeignKey(Airport, on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()

    class Meta:
        ordering = ["sequence"]
        unique_together = [["route", "sequence"]]
