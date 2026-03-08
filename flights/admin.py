from django.contrib import admin

from flights.models import Approach, Flight, Ground, SimulatorFlight


class ApproachInline(admin.TabularInline):
    model = Approach
    extra = 1


class FlightAdmin(admin.ModelAdmin):
    inlines = [ApproachInline]
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
        "holds",
        "excluded",
    )
    list_editable = ("excluded",)
    search_fields = (
        "date",
        "plane__tail_number",
        "plane__type",
        "route__name",
        "pilot__first_name",
        "pilot__last_name",
        "instructor__first_name",
        "instructor__last_name",
        "notes",
    )


class GroundAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "pilot",
        "date",
        "ground_time",
        "subject",
    )
    search_fields = (
        "date",
        "subject",
        "pilot__first_name",
        "pilot__last_name",
        "instructor__first_name",
        "instructor__last_name",
    )


class SimulatorFlightAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "pilot",
        "date",
        "sim_time",
        "plane",
    )
    search_fields = (
        "date",
        "plane__tail_number",
        "plane__type",
        "pilot__first_name",
        "pilot__last_name",
        "instructor__first_name",
        "instructor__last_name",
        "notes",
    )


# Register your models here.
admin.site.register(Flight, FlightAdmin)
admin.site.register(Ground, GroundAdmin)
admin.site.register(SimulatorFlight, SimulatorFlightAdmin)
