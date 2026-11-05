from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render

from .forms import PatientRegistrationForm
from .models import Department, DoctorProfile, User


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
    appointments = request.user.appointments.select_related("doctor__user")[:5]
    return render(request, "dashboards/patient_dashboard.html", {
        "appointments": appointments,
    })


@role_required(User.Role.DOCTOR)
def doctor_dashboard(request):
    profile = DoctorProfile.objects.filter(user=request.user).first()
    appointments = []
    if profile:
        appointments = profile.appointments.select_related("patient")[:10]
    return render(request, "dashboards/doctor_dashboard.html", {
        "profile": profile,
        "appointments": appointments,
    })