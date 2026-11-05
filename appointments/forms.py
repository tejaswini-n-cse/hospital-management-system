from datetime import timedelta

from django import forms
from django.utils import timezone

from .utils import MAX_DAYS_AHEAD


class BookingForm(forms.Form):
    date = forms.DateField()
    time = forms.TimeField(input_formats=["%H:%M"])
    reason = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Briefly describe your problem (optional)"}),
    )

    def clean_date(self):
        day = self.cleaned_data["date"]
        today = timezone.localdate()
        if day < today:
            raise forms.ValidationError("Please choose today or a future date.")
        if day > today + timedelta(days=MAX_DAYS_AHEAD):
            raise forms.ValidationError(f"You can book up to {MAX_DAYS_AHEAD} days ahead.")
        return day
    