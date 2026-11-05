from django.urls import path

from . import views

urlpatterns = [
    path("invoices/", views.invoice_list, name="invoice_list"),
    path("invoices/<int:pk>/", views.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/pay/", views.pay_invoice, name="pay_invoice"),
    path("doctor/invoices/", views.doctor_invoices, name="doctor_invoices"),
]