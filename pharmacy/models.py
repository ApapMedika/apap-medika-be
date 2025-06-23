from django.db import models
from common.models import UserActionModel
from profiles.models import Patient, Pharmacist
import uuid

class Medicine(UserActionModel):
    """
    Medicine model
    """
    id = models.CharField(max_length=10, primary_key=True)  # MEDxxxx format
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'medicine'
    
    def __str__(self):
        return f"{self.id} - {self.name}"

class Prescription(UserActionModel):
    """
    Prescription model
    """
    STATUS_CHOICES = [
        (0, 'Created'),
        (1, 'Waiting for Stock'),
        (2, 'Done'),
        (3, 'Cancelled'),
    ]
    
    id = models.CharField(max_length=16, primary_key=True)  # Generated format
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey('appointment.Appointment', on_delete=models.CASCADE, null=True, blank=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    processed_by = models.ForeignKey(Pharmacist, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'prescription'
    
    def __str__(self):
        return f"{self.id} - {self.patient.user.name}"
    
    def get_status_display_custom(self):
        status_map = {
            0: 'Created',
            1: 'Waiting for Stock',
            2: 'Done',
            3: 'Cancelled',
        }
        return status_map.get(self.status, 'Unknown')

class MedicineQuantity(models.Model):
    """
    Junction table for Medicine and Prescription with quantity
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    quantity = models.IntegerField()  # Requested quantity
    fulfilled_quantity = models.IntegerField(default=0)  # Fulfilled quantity
    
    class Meta:
        db_table = 'medicine_quantity'
        unique_together = ['medicine', 'prescription']
    
    def __str__(self):
        return f"{self.prescription.id} - {self.medicine.name} ({self.quantity})"
    
    @property
    def remaining_quantity(self):
        return self.quantity - self.fulfilled_quantity
    
    @property
    def total_price(self):
        return self.fulfilled_quantity * self.medicine.price