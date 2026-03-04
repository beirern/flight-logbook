from django.contrib import admin

from licenses.models import License


class LicenseAdmin(admin.ModelAdmin):
    list_display = ("type", "number", "pilot", "expiration")
    search_fields = ("number", "pilot__first_name", "pilot__last_name")


# Register your models here.
admin.site.register(License, LicenseAdmin)
