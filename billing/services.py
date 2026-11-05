from decimal import ROUND_HALF_UP, Decimal

from .models import Invoice

TAX_PERCENT = Decimal("5.00")  # change this, or set it to 0 for no tax


def create_invoice_for(appointment):
    """Create the invoice for a completed appointment (safe to call twice)."""
    fee = appointment.doctor.consultation_fee
    tax = (fee * TAX_PERCENT / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    invoice, _ = Invoice.objects.get_or_create(
        appointment=appointment,
        defaults={
            "consultation_fee": fee,
            "tax_percent": TAX_PERCENT,
            "tax_amount": tax,
            "total": fee + tax,
        },
    )
    return invoice