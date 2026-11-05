from django.contrib import admin
from django.utils import timezone

from .models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "patient", "doctor", "total", "status", "issued_at")
    list_filter = ("status", "payment_method")
    search_fields = ("appointment__patient__username", "appointment__doctor__user__username")
    readonly_fields = ("appointment", "consultation_fee", "tax_percent", "tax_amount", "total", "issued_at")
    actions = ["mark_paid"]

    @admin.display(description="Invoice no.")
    def number(self, obj):
        return obj.invoice_number

    @admin.display(description="Patient")
    def patient(self, obj):
        return obj.appointment.patient

    @admin.display(description="Doctor")
    def doctor(self, obj):
        return obj.appointment.doctor

    def has_add_permission(self, request):
        return False  # invoices are only created automatically

    @admin.action(description="Mark selected invoices as paid (cash)")
    def mark_paid(self, request, queryset):
        count = queryset.filter(status=Invoice.Status.UNPAID).update(
            status=Invoice.Status.PAID,
            payment_method=Invoice.Method.CASH,
            paid_at=timezone.now(),
        )
        self.message_user(request, f"{count} invoice(s) marked as paid.")