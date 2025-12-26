from django.contrib import admin

from medicals.models import Medical


class MedicalAdmin(admin.ModelAdmin):
    list_display = ("__str__", "classNumber", "pilot", "examination_date")


# Register your models here.
admin.site.register(Medical, MedicalAdmin)
