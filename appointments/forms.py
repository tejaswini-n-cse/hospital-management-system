from datetime import timedelta

from django import forms
from django.utils import timezone

from django.forms import inlineformset_factory

from .models import MedicalRecord, PrescriptionItem

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


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ["diagnosis", "symptoms", "treatment_notes", "follow_up_date"]
        widgets = {
            "symptoms": forms.Textarea(attrs={"rows": 2}),
            "treatment_notes": forms.Textarea(attrs={"rows": 3}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_follow_up_date(self):
        day = self.cleaned_data.get("follow_up_date")
        if day and day < timezone.localdate():
            raise forms.ValidationError("Follow-up date cannot be in the past.")
        return day


PrescriptionFormSet = inlineformset_factory(
    MedicalRecord,
    PrescriptionItem,
    fields=["medicine", "dosage", "frequency", "duration_days", "instructions"],
    extra=3,
    can_delete=True,
)