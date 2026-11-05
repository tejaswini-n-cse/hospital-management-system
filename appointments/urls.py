from django.urls import path

from . import views

urlpatterns = [
    path("doctors/", views.doctor_list, name="doctor_list"),
    path("doctors/<int:pk>/", views.doctor_detail, name="doctor_detail"),
    path("doctors/<int:pk>/slots/", views.available_slots, name="available_slots"),
    path("doctors/<int:pk>/book/", views.book_appointment, name="book_appointment"),
]