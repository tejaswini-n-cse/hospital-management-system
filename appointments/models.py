from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import DoctorProfile


class DoctorAvailability(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="availabilities")
    day_of_week = models.PositiveSmallIntegerField(choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(default=30)

    class Meta:
        ordering = ["doctor", "day_of_week", "start_time"]
        verbose_name_plural = "Doctor availabilities"

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}"


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    CANCEL_BEFORE_HOURS = 2

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name="appointments")
    date = models.DateField()
    time = models.TimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    doctor_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-time"]
        indexes = [models.Index(fields=["doctor", "date", "time"])]

    def __str__(self):
        return f"{self.patient} with {self.doctor} on {self.date} at {self.time:%H:%M}"

    @property
    def starts_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.time))

    @property
    def is_upcoming(self):
        return self.starts_at >= timezone.now()

    @property
    def can_cancel(self):
        if self.status not in (self.Status.PENDING, self.Status.CONFIRMED):
            return False
        limit = self.starts_at - timedelta(hours=self.CANCEL_BEFORE_HOURS)
        return timezone.now() < limit