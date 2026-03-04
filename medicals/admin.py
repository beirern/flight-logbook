from django.contrib import admin

from medicals.models import Medical


class MedicalAdmin(admin.ModelAdmin):
    list_display = ("__str__", "classNumber", "pilot", "examination_date")
    search_fields = ("pilot__first_name", "pilot__last_name", "examiner_name")


# Register your models here.
admin.site.register(Medical, MedicalAdmin)
