from django.contrib import admin

from routes.models import Airport, Route, RouteWaypoint


# Register your models here.
class AirportAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "country", "municipality", "latitude", "longitude")
    ordering = ["code"]
    search_fields = ("code", "name", "country", "municipality")


class RouteAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ("name",)

    def get_queryset(self, request):
        # We tell Django: "When you fetch Routes, grab the waypoints too!"
        qs = super().get_queryset(request)
        return qs.prefetch_related("route_steps__waypoint")


class RouteWaypointAdmin(admin.ModelAdmin):
    list_display = ("route", "waypoint", "sequence")
    search_fields = ("route__name", "waypoint__code", "waypoint__name")


admin.site.register(Airport, AirportAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(RouteWaypoint, RouteWaypointAdmin)
