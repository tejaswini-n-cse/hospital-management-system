from django.db import models


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"

    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.PROTECT, related_name="invoice"
    )
    # amounts are copied at billing time, so later fee changes don't affect old invoices
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=9, decimal_places=2)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.UNPAID)
    payment_method = models.CharField(max_length=10, choices=Method.choices, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    @property
    def invoice_number(self):
        return f"INV-{self.issued_at:%Y}-{self.pk:05d}"

    def __str__(self):
        return self.invoice_number