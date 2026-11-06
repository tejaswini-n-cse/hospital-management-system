from datetime import time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import Department, DoctorProfile, PatientProfile, User
from appointments.models import (
    Appointment, DoctorAvailability, MedicalRecord, PrescriptionItem,
)
from billing.models import Invoice
from billing.services import create_invoice_for

PASSWORD = "Demo@12345"

DOCTORS = [
    # username, first, last, department, specialization, years, fee
    ("dr.sharma", "Anita", "Sharma", "Cardiology", "Cardiologist", 10, 500),
    ("dr.rao", "Vikram", "Rao", "Dermatology", "Dermatologist", 7, 400),
    ("dr.nair", "Meera", "Nair", "Pediatrics", "Pediatrician", 12, 350),
    ("dr.khan", "Imran", "Khan", "Cardiology", "Interventional Cardiologist", 15, 800),
]

PATIENTS = [
    ("patient.asha", "Asha", "Menon"),
    ("patient.ravi", "Ravi", "Kumar"),
    ("patient.sana", "Sana", "Iqbal"),
]


def make_user(username, first, last, role):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": first, "last_name": last,
            "email": f"{username}@example.com", "role": role,
        },
    )
    if created:
        user.set_password(PASSWORD)
        user.save()
    return user


class Command(BaseCommand):
    help = "Load demo departments, doctors, patients and appointments (development only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is for development only (DEBUG is False).")

        doctors = {}
        for username, first, last, dept_name, spec, years, fee in DOCTORS:
            dept, _ = Department.objects.get_or_create(
                name=dept_name, defaults={"description": f"{dept_name} care."}
            )
            user = make_user(username, first, last, User.Role.DOCTOR)
            profile, _ = DoctorProfile.objects.get_or_create(
                user=user,
                defaults={
                    "department": dept, "specialization": spec,
                    "experience_years": years, "consultation_fee": fee,
                    "bio": f"{spec} with {years} years of experience.",
                },
            )
            if not profile.availabilities.exists():
                for day in range(7):
                    DoctorAvailability.objects.create(
                        doctor=profile, day_of_week=day,
                        start_time=time(9, 0), end_time=time(13, 0), slot_minutes=30,
                    )
            doctors[username] = profile

        patients = {}
        for username, first, last in PATIENTS:
            user = make_user(username, first, last, User.Role.PATIENT)
            PatientProfile.objects.get_or_create(user=user)
            patients[username] = user

        today = timezone.localdate()
        S = Appointment.Status
        plan = [
            # patient, doctor, date offset, time, status, reason
            ("patient.asha", "dr.sharma", -1, time(9, 0), S.COMPLETED, "Chest discomfort"),
            ("patient.asha", "dr.sharma", 3, time(10, 0), S.CONFIRMED, "Follow-up"),
            ("patient.ravi", "dr.sharma", 3, time(10, 30), S.PENDING, "Blood pressure check"),
            ("patient.ravi", "dr.rao", -2, time(9, 30), S.COMPLETED, "Skin rash"),
            ("patient.sana", "dr.nair", 2, time(9, 0), S.CANCELLED, "Child vaccination"),
        ]
        for pat, doc, offset, slot, status, reason in plan:
            appt, _ = Appointment.objects.get_or_create(
                patient=patients[pat], doctor=doctors[doc],
                date=today + timedelta(days=offset), time=slot,
                defaults={"status": status, "reason": reason},
            )
            if status != S.COMPLETED:
                continue

            record, created = MedicalRecord.objects.get_or_create(
                appointment=appt,
                defaults={
                    "diagnosis": "Mild condition, medication advised",
                    "treatment_notes": "Rest, hydration, and review if symptoms persist.",
                    "follow_up_date": today + timedelta(days=14),
                },
            )
            if created:
                PrescriptionItem.objects.create(
                    record=record, medicine="Paracetamol", dosage="500 mg",
                    frequency="Twice a day after food", duration_days=5,
                )
            invoice = create_invoice_for(appt)
            if doc == "dr.rao":  # leave one paid and one unpaid
                Invoice.objects.filter(pk=invoice.pk, status=Invoice.Status.UNPAID).update(
                    status=Invoice.Status.PAID, payment_method=Invoice.Method.UPI,
                    paid_at=timezone.now(),
                )

        self.stdout.write(self.style.SUCCESS("Demo data loaded."))
        self.stdout.write(f"Demo password for every demo account: {PASSWORD}")
        self.stdout.write("Doctors: " + ", ".join(d[0] for d in DOCTORS))
        self.stdout.write("Patients: " + ", ".join(p[0] for p in PATIENTS))