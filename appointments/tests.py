from datetime import time, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Department, DoctorProfile, User
from billing.models import Invoice
from billing.services import create_invoice_for

from .models import Appointment, DoctorAvailability
from .utils import get_free_slots

PASSWORD = "Test@12345"


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        dept = Department.objects.create(name="Cardiology")
        cls.doctor_user = User.objects.create_user(
            "dr_test", password=PASSWORD, first_name="Anita", last_name="Sharma",
            role=User.Role.DOCTOR,
        )
        cls.doctor = DoctorProfile.objects.create(
            user=cls.doctor_user, department=dept, specialization="Cardiologist",
            consultation_fee=Decimal("500.00"),
        )
        # open every weekday 09:00-11:00, so the tests don't depend on today's weekday
        for day in range(7):
            DoctorAvailability.objects.create(
                doctor=cls.doctor, day_of_week=day,
                start_time=time(9, 0), end_time=time(11, 0), slot_minutes=30,
            )
        cls.patient = User.objects.create_user("pat_one", password=PASSWORD, role=User.Role.PATIENT)
        cls.patient2 = User.objects.create_user("pat_two", password=PASSWORD, role=User.Role.PATIENT)
        cls.future_day = timezone.localdate() + timedelta(days=7)

    def book(self, patient, day=None, slot="09:00"):
        self.client.force_login(patient)
        return self.client.post(
            reverse("book_appointment", args=[self.doctor.pk]),
            {"date": (day or self.future_day).isoformat(), "time": slot, "reason": "Checkup"},
        )

    def past_appointment(self, status=Appointment.Status.CONFIRMED):
        return Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            date=timezone.localdate() - timedelta(days=1), time=time(9, 0), status=status,
        )


class SlotTests(BaseTestCase):
    def test_free_slots_for_a_working_day(self):
        self.assertEqual(
            get_free_slots(self.doctor, self.future_day),
            [time(9, 0), time(9, 30), time(10, 0), time(10, 30)],
        )

    def test_booked_slot_is_removed(self):
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=self.future_day, time=time(9, 0)
        )
        self.assertNotIn(time(9, 0), get_free_slots(self.doctor, self.future_day))

    def test_cancelled_slot_is_free_again(self):
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=self.future_day,
            time=time(9, 0), status=Appointment.Status.CANCELLED,
        )
        self.assertIn(time(9, 0), get_free_slots(self.doctor, self.future_day))


class BookingTests(BaseTestCase):
    def test_patient_can_book(self):
        response = self.book(self.patient)
        self.assertRedirects(response, reverse("patient_dashboard"), fetch_redirect_response=False)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_same_slot_cannot_be_booked_twice(self):
        self.book(self.patient)
        response = self.book(self.patient2)
        self.assertEqual(response.status_code, 200)  # form shown again with an error
        self.assertContains(response, "just taken")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("book_appointment", args=[self.doctor.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_doctor_cannot_book(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse("book_appointment", args=[self.doctor.pk]))
        self.assertEqual(response.status_code, 403)


class CancellationTests(BaseTestCase):
    def test_cannot_cancel_within_two_hours(self):
        soon = timezone.localtime() + timedelta(hours=1)
        appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=soon.date(),
            time=soon.time().replace(second=0, microsecond=0),
        )
        self.assertFalse(appt.can_cancel)

    def test_patient_can_cancel_and_slot_is_freed(self):
        appt = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=self.future_day, time=time(9, 0)
        )
        self.client.force_login(self.patient)
        self.client.post(reverse("cancel_appointment", args=[appt.pk]))
        appt.refresh_from_db()
        self.assertEqual(appt.status, Appointment.Status.CANCELLED)
        self.assertIn(time(9, 0), get_free_slots(self.doctor, self.future_day))


class PermissionTests(BaseTestCase):
    def test_patient_cannot_open_doctor_schedule(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("doctor_appointments"))
        self.assertEqual(response.status_code, 403)


class BillingTests(BaseTestCase):
    def complete(self, appt):
        self.client.force_login(self.doctor_user)
        return self.client.post(
            reverse("update_appointment_status", args=[appt.pk]), {"action": "complete"}
        )

    def test_completing_a_visit_creates_the_invoice(self):
        appt = self.past_appointment()
        self.complete(appt)
        invoice = Invoice.objects.get(appointment=appt)
        self.assertEqual(invoice.consultation_fee, Decimal("500.00"))
        self.assertEqual(invoice.tax_amount, Decimal("25.00"))
        self.assertEqual(invoice.total, Decimal("525.00"))

    def test_completing_twice_gives_one_invoice(self):
        appt = self.past_appointment()
        self.complete(appt)
        self.complete(appt)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_create_invoice_for_is_idempotent(self):
        appt = self.past_appointment(status=Appointment.Status.COMPLETED)
        create_invoice_for(appt)
        create_invoice_for(appt)
        self.assertEqual(Invoice.objects.count(), 1)

    def test_other_patient_cannot_view_invoice(self):
        appt = self.past_appointment(status=Appointment.Status.COMPLETED)
        invoice = create_invoice_for(appt)
        self.client.force_login(self.patient2)
        response = self.client.get(reverse("invoice_detail", args=[invoice.pk]))
        self.assertEqual(response.status_code, 403)