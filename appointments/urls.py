from django.urls import path

from . import views

urlpatterns = [
    path("doctors/", views.doctor_list, name="doctor_list"),
    path("doctors/<int:pk>/", views.doctor_detail, name="doctor_detail"),
    path("doctors/<int:pk>/slots/", views.available_slots, name="available_slots"),
    path("doctors/<int:pk>/book/", views.book_appointment, name="book_appointment"),
    path("appointments/", views.my_appointments, name="my_appointments"),
    path("appointments/<int:pk>/cancel/", views.cancel_appointment, name="cancel_appointment"),
        path("doctor/appointments/", views.doctor_appointments, name="doctor_appointments"),
    path("doctor/appointments/<int:pk>/status/", views.update_appointment_status, name="update_appointment_status"),
    path("doctor/appointments/<int:pk>/notes/", views.save_doctor_notes, name="save_doctor_notes"),
]