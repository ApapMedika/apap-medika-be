from django.db.models.signals import post_save
from django.dispatch import receiver
from appointment.models import Appointment
from pharmacy.models import Prescription
from .models import Bill

@receiver(post_save, sender=Appointment)
def update_bill_on_appointment_status_change(sender, instance, created, **kwargs):
    """
    Update bill status when appointment status changes
    """
    if not created and instance.status == 1:  # Appointment marked as Done
        # Find related bills
        bills = Bill.objects.filter(appointment=instance, deleted_at__isnull=True)
        for bill in bills:
            bill.update_status()

@receiver(post_save, sender=Prescription)
def update_bill_on_prescription_status_change(sender, instance, created, **kwargs):
    """
    Update bill status when prescription status changes
    """
    if not created and instance.status == 2:  # Prescription marked as Done
        # Find related bills through appointment
        if instance.appointment:
            bills = Bill.objects.filter(
                appointment=instance.appointment,
                prescription=instance,
                deleted_at__isnull=True
            )
            for bill in bills:
                bill.update_status()