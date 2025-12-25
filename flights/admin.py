from django.contrib import admin

from flights.models import Flight, Ground, SimulatorFlight


class FlightAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "pilot",
        "date",
        "route",
        "flight_time",
        "plane",
        "pic_time",
        "flight_training_received",
        "day_landings",
        "day_fullstop_landings",
        "night_landings",
        "night_fullstop_landings",
    )


class GroundAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "pilot",
        "date",
        "ground_time",
        "subject",
    )


class SimulatorAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "pilot",
        "date",
        "sim_time",
        "plane",
    )


# Register your models here.
admin.site.register(Flight, FlightAdmin)
admin.site.register(Ground, GroundAdmin)
admin.site.register(SimulatorFlight, SimulatorAdmin)
