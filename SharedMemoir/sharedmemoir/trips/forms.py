
from django import forms
from .models import Trip


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip

        fields = [
            "title",
            "destination_region",
            "trip_type",
            "start_date",
            "end_date",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "destination_region": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "trip_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "End date cannot be earlier than start date."
            )

        return cleaned_data
