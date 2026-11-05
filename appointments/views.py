from billing.services import create_invoice_for
from datetime import date, timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Department, DoctorProfile, User
from accounts.views import role_required
from datetime import datetime

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


@role_required(User.Role.PATIENT)
def my_appointments(request):
    tab = request.GET.get("tab", "upcoming")
    now = timezone.now()

    appointments = list(
        Appointment.objects.filter(patient=request.user)
        .select_related("doctor__user", "doctor__department", "invoice")
    )

    upcoming = sorted(
        [a for a in appointments
         if a.status != Appointment.Status.CANCELLED and a.starts_at >= now],
        key=lambda a: a.starts_at,
    )
    past = sorted(
        [a for a in appointments
         if a.status == Appointment.Status.CANCELLED or a.starts_at < now],
        key=lambda a: a.starts_at,
        reverse=True,
    )

    return render(request, "appointments/my_appointments.html", {
        "tab": "past" if tab == "past" else "upcoming",
        "upcoming": upcoming,
        "past": past,
    })


@require_POST
@role_required(User.Role.PATIENT)
def cancel_appointment(request, pk):
    # only the patient who owns it can cancel it
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)

    if appointment.can_cancel:
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status"])
        messages.success(request, "Your appointment has been cancelled.")
    else:
        messages.error(
            request,
            "This appointment can no longer be cancelled. Cancellation closes "
            f"{Appointment.CANCEL_BEFORE_HOURS} hours before the visit.",
        )
    return redirect("my_appointments")

def _doctor_profile_or_404(user):
    return get_object_or_404(DoctorProfile, user=user)


@role_required(User.Role.DOCTOR)
def doctor_appointments(request):
    profile = DoctorProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Your doctor profile is not set up yet. Ask the admin.")
        return redirect("doctor_dashboard")

    tab = request.GET.get("tab", "today")
    if tab not in ("today", "upcoming", "history"):
        tab = "today"

    today = timezone.localdate()
    now = timezone.now()

    appointments = list(
        profile.appointments.select_related("patient", "patient__patient_profile")
    )

    active = (Appointment.Status.PENDING, Appointment.Status.CONFIRMED)

    today_list = sorted(
        [a for a in appointments if a.date == today and a.status != Appointment.Status.CANCELLED],
        key=lambda a: a.starts_at,
    )
    upcoming_list = sorted(
        [a for a in appointments if a.date > today and a.status in active],
        key=lambda a: a.starts_at,
    )
    history_list = sorted(
        [a for a in appointments
         if a.status in (Appointment.Status.COMPLETED, Appointment.Status.CANCELLED)
         or (a.date < today and a.status in active)],
        key=lambda a: a.starts_at,
        reverse=True,
    )

    return render(request, "appointments/doctor_appointments.html", {
        "profile": profile,
        "tab": tab,
        "today_list": today_list,
        "upcoming_list": upcoming_list,
        "history_list": history_list,
    })


@require_POST
@role_required(User.Role.DOCTOR)
def update_appointment_status(request, pk):
    profile = _doctor_profile_or_404(request.user)
    # only this doctor's own appointments can be changed
    appointment = get_object_or_404(Appointment, pk=pk, doctor=profile)
    action = request.POST.get("action")
    redirect_to = request.POST.get("next") or "doctor_appointments"

    if action == "confirm" and appointment.can_confirm:
        new_status, text = Appointment.Status.CONFIRMED, "Appointment confirmed."
    elif action == "complete" and appointment.can_complete:
        new_status, text = Appointment.Status.COMPLETED, "Appointment completed. Invoice created."
    elif action == "cancel" and appointment.doctor_can_cancel:
        new_status, text = Appointment.Status.CANCELLED, "Appointment cancelled. The slot is free again."
    else:
        messages.error(request, "That action is not allowed for this appointment.")
        return redirect(redirect_to)

    with transaction.atomic():
        appointment.status = new_status
        appointment.save(update_fields=["status"])
        if new_status == Appointment.Status.COMPLETED:
            create_invoice_for(appointment)

    messages.success(request, text)
    return redirect(redirect_to)


@require_POST
@role_required(User.Role.DOCTOR)
def save_doctor_notes(request, pk):
    profile = _doctor_profile_or_404(request.user)
    appointment = get_object_or_404(Appointment, pk=pk, doctor=profile)

    appointment.doctor_notes = request.POST.get("doctor_notes", "").strip()[:2000]
    appointment.save(update_fields=["doctor_notes"])
    messages.success(request, "Notes saved.")
    return redirect(request.POST.get("next") or "doctor_appointments")