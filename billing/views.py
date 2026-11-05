from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import DoctorProfile, User
from accounts.views import role_required

from .models import Invoice

ZERO = Decimal("0.00")


@role_required(User.Role.PATIENT)
def invoice_list(request):
    invoices = (
        Invoice.objects.filter(appointment__patient=request.user)
        .select_related("appointment__doctor__user")
        .order_by("-issued_at")
    )
    outstanding = (
        invoices.filter(status=Invoice.Status.UNPAID).aggregate(t=Sum("total"))["t"] or ZERO
    )
    return render(request, "billing/invoice_list.html", {
        "invoices": invoices,
        "outstanding": outstanding,
    })


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "appointment__patient",
            "appointment__doctor__user",
            "appointment__doctor__department",
        ),
        pk=pk,
    )
    appointment = invoice.appointment
    user = request.user

    # only the patient, the treating doctor, or an admin may view it
    allowed = (
        user.is_superuser
        or user == appointment.patient
        or user == appointment.doctor.user
    )
    if not allowed:
        raise PermissionDenied

    return render(request, "billing/invoice_detail.html", {
        "invoice": invoice,
        "appointment": appointment,
        "methods": Invoice.Method.choices,
    })


@require_POST
@role_required(User.Role.PATIENT)
def pay_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, appointment__patient=request.user)
    method = request.POST.get("method")

    if method not in Invoice.Method.values:
        messages.error(request, "Please choose a payment method.")
        return redirect("invoice_detail", pk=invoice.pk)

    # the status filter makes this safe against double clicks
    updated = Invoice.objects.filter(pk=invoice.pk, status=Invoice.Status.UNPAID).update(
        status=Invoice.Status.PAID,
        payment_method=method,
        paid_at=timezone.now(),
    )
    if updated:
        messages.success(request, "Payment recorded. Thank you!")
    else:
        messages.info(request, "This invoice is already paid.")
    return redirect("invoice_detail", pk=invoice.pk)


@role_required(User.Role.DOCTOR)
def doctor_invoices(request):
    profile = DoctorProfile.objects.filter(user=request.user).first()
    if not profile:
        messages.warning(request, "Your doctor profile is not set up yet. Ask the admin.")
        return redirect("doctor_dashboard")

    invoices = (
        Invoice.objects.filter(appointment__doctor=profile)
        .select_related("appointment__patient")
        .order_by("-issued_at")
    )
    collected = invoices.filter(status=Invoice.Status.PAID).aggregate(t=Sum("total"))["t"] or ZERO
    pending = invoices.filter(status=Invoice.Status.UNPAID).aggregate(t=Sum("total"))["t"] or ZERO

    return render(request, "billing/doctor_invoices.html", {
        "invoices": invoices,
        "collected": collected,
        "pending": pending,
    })