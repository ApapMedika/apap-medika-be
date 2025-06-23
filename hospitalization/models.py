from django.db import models
from common.models import UserActionModel
from profiles.models import Patient, Nurse
import uuid

class Room(UserActionModel):
    """
    Room model for hospital reservations
    """
    id = models.CharField(max_length=10, primary_key=True)  # RMxxxx format
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    max_capacity = models.IntegerField()
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'room'
    
    def __str__(self):
        return f"{self.id} - {self.name}"
    
    def get_available_capacity(self, date_in, date_out):
        """
        Get available capacity for given date range
        """
        from django.db.models import Count
        
        reservations = self.reservation_set.filter(
            deleted_at__isnull=True,
            date_in__lte=date_out,
            date_out__gte=date_in
        ).count()
        
        return self.max_capacity - reservations

class Facility(UserActionModel):
    """
    Facility model for additional room services
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'facility'
    
    def __str__(self):
        return f"{self.name} - Rp {self.fee}"

class Reservation(UserActionModel):
    """
    Reservation model for hospital room bookings
    """
    id = models.CharField(max_length=16, primary_key=True)  # Generated format
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    appointment = models.ForeignKey('appointment.Appointment', on_delete=models.CASCADE, null=True, blank=True)
    assigned_nurse = models.ForeignKey(Nurse, on_delete=models.SET_NULL, null=True, blank=True)
    date_in = models.DateField()
    date_out = models.DateField()
    total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'reservation'
    
    def __str__(self):
        return f"{self.id} - {self.patient.user.name} in {self.room.name}"
    
    def calculate_total_fee(self):
        """
        Calculate total fee including room and facilities
        """
        from datetime import timedelta
        
        # Calculate room cost
        days = (self.date_out - self.date_in).days + 1
        room_cost = self.room.price_per_day * days
        
        # Calculate facilities cost
        facilities_cost = sum(rf.facility.fee for rf in self.reservationfacility_set.all())
        
        return room_cost + facilities_cost
    
    def save(self, *args, **kwargs):
        if not self.total_fee:
            self.total_fee = self.calculate_total_fee()
        super().save(*args, **kwargs)

class ReservationFacility(models.Model):
    """
    Junction table for Reservation and Facility (many-to-many)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'reservation_facility'
        unique_together = ['reservation', 'facility']
    
    def __str__(self):
        return f"{self.reservation.id} - {self.facility.name}"