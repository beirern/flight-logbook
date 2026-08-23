from django import forms
from django.forms import inlineformset_factory

from flights.models import Approach, Flight
from pilots.models import Pilot

# These numeric fields have no model-level default, which forces the Django
# admin form to require typing "0" into every one of them for a routine local
# flight. We default them to 0 here at the form layer only (no model migration).
NUMERIC_DEFAULT_ZERO_FIELDS = [
    "pic_time",
    "sic_time",
    "xc_time",
    "day_time",
    "night_time",
    "actual_instrument_time",
    "simulated_instrument_time",
    "day_landings",
    "day_fullstop_landings",
    "night_landings",
    "night_fullstop_landings",
    "holds",
]


class FlightForm(forms.ModelForm):
    class Meta:
        model = Flight
        fields = [
            "date",
            "time_start",
            "time_end",
            "flight_time",
            "plane",
            "route",
            "instructor",
            "passengers",
            "pic_time",
            "sic_time",
            "flight_training_received",
            "xc_time",
            "day_time",
            "night_time",
            "actual_instrument_time",
            "simulated_instrument_time",
            "day_landings",
            "day_fullstop_landings",
            "night_landings",
            "night_fullstop_landings",
            "holds",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "time_start": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "time_end": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "plane": forms.Select(attrs={"class": "form-select"}),
            # route/instructor/passengers are driven by JS typeahead widgets in the
            # template; HiddenInput never renders <option> tags, so the field's
            # queryset is used only for validating the submitted PK(s) - it's never
            # iterated to build a dropdown. This is what avoids the N+1 Route.__str__
            # cost that makes the admin page slow.
            "route": forms.HiddenInput(),
            "instructor": forms.HiddenInput(),
            "passengers": forms.MultipleHiddenInput(),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["instructor"].queryset = Pilot.objects.filter(
            role__in=[Pilot.RoleChoices.INSTRUCTOR, Pilot.RoleChoices.EXAMINER]
        )
        self.fields["passengers"].queryset = Pilot.objects.filter(role=Pilot.RoleChoices.PASSENGER)
        self.fields["instructor"].required = False
        self.fields["passengers"].required = False
        for name in NUMERIC_DEFAULT_ZERO_FIELDS:
            self.fields[name].required = False

    def clean(self):
        cleaned = super().clean()
        for name in NUMERIC_DEFAULT_ZERO_FIELDS:
            if cleaned.get(name) in (None, ""):
                cleaned[name] = 0
        return cleaned


ApproachFormSet = inlineformset_factory(
    Flight,
    Approach,
    fields=["airport", "type"],
    widgets={
        "airport": forms.HiddenInput(),
        "type": forms.TextInput(
            attrs={"class": "form-control form-control-sm", "placeholder": "e.g. ILS, RNAV, VOR"}
        ),
    },
    extra=1,
    can_delete=True,
)
