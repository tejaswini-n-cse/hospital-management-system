from datetime import date, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Department, DoctorProfile, User
from accounts.views import role_required

from .forms import BookingForm
from .models import Appointment
from .utils import MAX_DAYS_AHEAD, get_free_slots


def doctor_list(request):
    doctors = DoctorProfile.objects.select_related("user", "department")

    q = request.GET.get("q", "").strip()
    department = request.GET.get("department", "")

    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(specialization__icontains=q)
        )
    if department.isdigit():
        doctors = doctors.filter(department_id=int(department))

    paginator = Paginator(doctors.order_by("user__first_name"), 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "doctors/doctor_list.html", {
        "page_obj": page_obj,
        "departments": Department.objects.all(),
        "q": q,
        "selected_department": department,
        "querystring": params.urlencode(),
    })


def doctor_detail(request, pk):
    doctor = get_object_or_404(
        DoctorProfile.objects.select_related("user", "department"), pk=pk
    )
    availabilities = doctor.availabilities.order_by("day_of_week", "start_time")
    return render(request, "doctors/doctor_detail.html", {
        "doctor": doctor,
        "availabilities": availabilities,
    })


def available_slots(request, pk):
    """JSON endpoint used by JavaScript: free slots for one doctor on one date."""
    doctor = get_object_or_404(DoctorProfile, pk=pk)

    try:
        day = date.fromisoformat(request.GET.get("date", ""))
    except ValueError:
        return JsonResponse({"error": "Invalid date."}, status=400)

    today = timezone.localdate()
    if day < today or day > today + timedelta(days=MAX_DAYS_AHEAD):
        return JsonResponse({"slots": []})

    slots = [slot.strftime("%H:%M") for slot in get_free_slots(doctor, day)]
    return JsonResponse({"slots": slots})


@role_required(User.Role.PATIENT)
def book_appointment(request, pk):
    doctor = get_object_or_404(
        DoctorProfile.objects.select_related("user", "department"), pk=pk
    )

    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            day = form.cleaned_data["date"]
            slot = form.cleaned_data["time"]

            with transaction.atomic():
                # Lock this doctor's row. A second booking for the same doctor
                # waits here until the first one finishes, then sees the new data.
                DoctorProfile.objects.select_for_update().get(pk=doctor.pk)

                if slot not in get_free_slots(doctor, day):
                    form.add_error(
                        None,
                        "Sorry, that slot was just taken or is not available. Please pick another.",
                    )
                elif Appointment.objects.filter(
                    patient=request.user, date=day, time=slot
                ).exclude(status=Appointment.Status.CANCELLED).exists():
                    form.add_error(None, "You already have an appointment at that time.")
                else:
                    Appointment.objects.create(
                        patient=request.user,
                        doctor=doctor,
                        date=day,
                        time=slot,
                        reason=form.cleaned_data["reason"],
                    )
                    messages.success(
                        request,
                        f"Appointment booked with Dr. {doctor.user.get_full_name() or doctor.user.username} "
                        f"on {day:%d %b %Y} at {slot:%H:%M}.",
                    )
                    return redirect("patient_dashboard")
    else:
        form = BookingForm()

    today = timezone.localdate()
    return render(request, "appointments/book.html", {
        "doctor": doctor,
        "form": form,
        "today": today,
        "max_date": today + timedelta(days=MAX_DAYS_AHEAD),
    })