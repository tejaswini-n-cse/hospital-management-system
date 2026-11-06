from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import PatientRegistrationForm
from .models import Department, DoctorProfile, User

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone


def role_required(role):
    """Allow a view only for users with the given role."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.role != role:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def home(request):
    departments = Department.objects.all()
    doctor_count = DoctorProfile.objects.count()
    return render(request, "home.html", {
        "departments": departments,
        "doctor_count": doctor_count,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome! Your account has been created.")
            return redirect("dashboard")
    else:
        form = PatientRegistrationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    """Send each user to the right page for their role."""
    user = request.user
    if user.is_superuser or user.role == User.Role.ADMIN:
        return redirect("admin:index")
    if user.role == User.Role.DOCTOR:
        return redirect("doctor_dashboard")
    return redirect("patient_dashboard")


@role_required(User.Role.PATIENT)
def patient_dashboard(request):
    from appointments.models import Appointment, MedicalRecord
    from billing.models import Invoice

    now = timezone.now()
    all_appts = list(request.user.appointments.select_related("doctor__user"))

    active = (Appointment.Status.PENDING, Appointment.Status.CONFIRMED)
    upcoming_count = sum(1 for a in all_appts if a.status in active and a.starts_at >= now)

    unpaid = Invoice.objects.filter(
        appointment__patient=request.user, status=Invoice.Status.UNPAID
    ).aggregate(total=Sum("total"))["total"] or Decimal("0.00")

    records_count = MedicalRecord.objects.filter(appointment__patient=request.user).count()

    recent = sorted(all_appts, key=lambda a: a.starts_at, reverse=True)[:5]

    return render(request, "dashboards/patient_dashboard.html", {
        "appointments": recent,
        "upcoming_count": upcoming_count,
        "unpaid_total": unpaid,
        "records_count": records_count,
    })


@role_required(User.Role.DOCTOR)
def doctor_dashboard(request):
    from appointments.models import Appointment
    from billing.models import Invoice

    profile = DoctorProfile.objects.filter(user=request.user).first()
    context = {"profile": profile, "appointments": []}

    if profile:
        today = timezone.localdate()
        appts = profile.appointments.select_related("patient")

        context.update({
            "appointments": appts.order_by("-date", "-time")[:8],
            "today_count": appts.filter(date=today).exclude(
                status=Appointment.Status.CANCELLED).count(),
            "pending_count": appts.filter(status=Appointment.Status.PENDING).count(),
            "completed_count": appts.filter(status=Appointment.Status.COMPLETED).count(),
            "earned": Invoice.objects.filter(
                appointment__doctor=profile, status=Invoice.Status.PAID
            ).aggregate(total=Sum("total"))["total"] or Decimal("0.00"),
        })

    return render(request, "dashboards/doctor_dashboard.html", context)