from datetime import datetime, timedelta

from django.utils import timezone

from .models import Appointment

MAX_DAYS_AHEAD = 60


def get_free_slots(doctor, day):
    """Return a sorted list of free time slots for a doctor on a given date."""
    availabilities = doctor.availabilities.filter(day_of_week=day.weekday())

    booked = set(
        Appointment.objects.filter(doctor=doctor, date=day)
        .exclude(status=Appointment.Status.CANCELLED)
        .values_list("time", flat=True)
    )

    now = timezone.localtime()
    slots = set()

    for availability in availabilities:
        if availability.slot_minutes <= 0:
            continue
        step = timedelta(minutes=availability.slot_minutes)
        current = datetime.combine(day, availability.start_time)
        end = datetime.combine(day, availability.end_time)

        while current + step <= end:
            slot = current.time()
            is_past = day == now.date() and slot <= now.time()
            if slot not in booked and not is_past:
                slots.add(slot)
            current += step

    return sorted(slots)