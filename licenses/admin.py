from django.contrib import admin

from licenses.models import License


class LicenseAdmin(admin.ModelAdmin):
    list_display = ("type", "number", "pilot", "expiration")


# Register your models here.
admin.site.register(License, LicenseAdmin)
