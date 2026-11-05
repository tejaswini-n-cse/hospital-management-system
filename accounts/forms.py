from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

from .models import PatientProfile, User


class PatientRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    date_of_birth = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    gender = forms.ChoiceField(
        required=False, choices=[("", "Select")] + PatientProfile.Gender.choices
    )
    blood_group = forms.CharField(max_length=3, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.PATIENT
        if commit:
            with transaction.atomic():
                user.save()
                PatientProfile.objects.create(
                    user=user,
                    date_of_birth=self.cleaned_data.get("date_of_birth"),
                    gender=self.cleaned_data.get("gender", ""),
                    blood_group=self.cleaned_data.get("blood_group", ""),
                )
        return user