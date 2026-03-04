from django.contrib import admin

from planes.models import Plane, Simulator


class PlaneAdmin(admin.ModelAdmin):
    list_display = ("tail_number", "type", "plane_class")
    search_fields = ("tail_number", "type")


class SimulatorAdmin(admin.ModelAdmin):
    list_display = ("tail_number", "type", "sim_class")
    search_fields = ("tail_number", "type")


# Register your models here.
admin.site.register(Plane, PlaneAdmin)
admin.site.register(Simulator, SimulatorAdmin)
