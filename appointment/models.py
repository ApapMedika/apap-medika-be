from django.db import models
from common.models import UserActionModel
from profiles.models import Patient, Doctor
import uuid

class Treatment(models.Model):
    """
    Treatment model - static data
    """
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'treatment'
    
    def __str__(self):
        return f"{self.id} - {self.name}"

class Appointment(UserActionModel):
    """
    Appointment model
    """
    STATUS_CHOICES = [
        (0, 'Created'),
        (1, 'Done'),
        (2, 'Cancelled'),
    ]
    
    id = models.CharField(max_length=10, primary_key=True)  # Generated code
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    date = models.DateTimeField()
    diagnosis = models.TextField(blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'appointment'
        unique_together = ['doctor', 'date']
    
    def __str__(self):
        return f"{self.id} - {self.patient.user.name} with {self.doctor.user.name}"
    
    def get_status_display_custom(self):
        status_map = {
            0: 'Created',
            1: 'Done',
            2: 'Cancelled',
        }
        return status_map.get(self.status, 'Unknown')

class AppointmentTreatment(models.Model):
    """
    Junction table for Appointment and Treatment (many-to-many)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE)
    treatment = models.ForeignKey(Treatment, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'appointment_treatment'
        unique_together = ['appointment', 'treatment']
    
    def __str__(self):
        return f"{self.appointment.id} - {self.treatment.name}"