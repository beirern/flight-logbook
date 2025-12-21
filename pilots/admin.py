from django.contrib import admin

from pilots.models import Pilot


class PilotAdmin(admin.ModelAdmin):
    list_display = ("__str__", "role")


# Register your models here.
admin.site.register(Pilot, PilotAdmin)
