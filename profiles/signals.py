from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EndUser, Admin, Nurse, Patient, Doctor, Pharmacist

@receiver(post_save, sender=EndUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create corresponding profile when EndUser is created
    """
    if created:
        if instance.role == 'ADMIN' and not hasattr(instance, 'admin'):
            Admin.objects.create(user=instance)
        elif instance.role == 'NURSE' and not hasattr(instance, 'nurse'):
            Nurse.objects.create(user=instance)
        elif instance.role == 'PHARMACIST' and not hasattr(instance, 'pharmacist'):
            Pharmacist.objects.create(user=instance)