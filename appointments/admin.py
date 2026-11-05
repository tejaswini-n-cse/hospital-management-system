from django.contrib import admin

from .models import Appointment, DoctorAvailability, MedicalRecord, PrescriptionItem


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("doctor", "day_of_week", "start_time", "end_time", "slot_minutes")
    list_filter = ("day_of_week", "doctor")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("patient", "doctor", "date", "time", "status")
    list_filter = ("status", "date", "doctor")
    search_fields = ("patient__username", "doctor__user__username")


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ("appointment", "diagnosis", "follow_up_date", "created_at")
    search_fields = ("diagnosis", "appointment__patient__username")
    inlines = [PrescriptionItemInline]