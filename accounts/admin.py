from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, DoctorProfile, PatientProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Role", {"fields": ("role", "phone")}),)
    list_display = ("username", "email", "role", "is_active")
    list_filter = ("role", "is_active")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "specialization", "consultation_fee")
    list_filter = ("department",)
    search_fields = ("user__username", "user__first_name", "specialization")


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "gender", "blood_group")