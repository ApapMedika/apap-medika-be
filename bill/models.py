from django.db import models
from common.models import UserActionModel
from profiles.models import Patient
import uuid

class Bill(UserActionModel):
    """
    Bill model for patient payments
    """
    STATUS_CHOICES = [
        ('TREATMENT_IN_PROGRESS', 'Treatment In Progress'),
        ('UNPAID', 'Unpaid'),
        ('PAID', 'Paid'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey('appointment.Appointment', on_delete=models.CASCADE, null=True, blank=True)
    prescription = models.ForeignKey('pharmacy.Prescription', on_delete=models.CASCADE, null=True, blank=True)
    reservation = models.ForeignKey('hospitalization.Reservation', on_delete=models.CASCADE, null=True, blank=True)
    policy = models.ForeignKey('insurance.Policy', on_delete=models.SET_NULL, null=True, blank=True)
    
    appointment_total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prescription_total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reservation_total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='TREATMENT_IN_PROGRESS')
    
    class Meta:
        db_table = 'bill'
    
    def __str__(self):
        return f"Bill {self.id} - {self.patient.user.name}"
    
    def calculate_subtotal(self):
        """
        Calculate subtotal from all components
        """
        return self.appointment_total_fee + self.prescription_total_price + self.reservation_total_fee
    
    def calculate_coverage_discount(self):
        """
        Calculate discount from insurance policy coverage
        """
        if not self.policy or not self.appointment:
            return 0
        
        total_discount = 0
        
        # Check covered treatments
        for app_treatment in self.appointment.appointmenttreatment_set.all():
            treatment_name = app_treatment.treatment.name
            
            # Check if policy covers this treatment
            policy_coverage = self.policy.policycoverage_set.filter(
                coverage__name=treatment_name,
                used=False
            ).first()
            
            if policy_coverage:
                coverage_amount = min(app_treatment.treatment.price, policy_coverage.coverage.coverage_amount)
                total_discount += coverage_amount
        
        return total_discount
    
    def update_status(self):
        """
        Update bill status based on business logic
        """
        # Check if all related services are done
        appointment_done = not self.appointment or self.appointment.status == 1
        prescription_done = not self.prescription or self.prescription.status == 2
        reservation_done = True  # Reservations don't have completion status
        
        if appointment_done and prescription_done and reservation_done:
            if self.status == 'TREATMENT_IN_PROGRESS':
                self.status = 'UNPAID'
                self.subtotal = self.calculate_subtotal()
                
                # Update fee components
                if self.appointment:
                    self.appointment_total_fee = self.appointment.total_fee
                if self.prescription:
                    self.prescription_total_price = self.prescription.total_price
                if self.reservation:
                    self.reservation_total_fee = self.reservation.total_fee
                
                # Calculate total amount due (without policy applied yet)
                self.total_amount_due = self.subtotal
                self.save()
    
    def apply_policy_coverage(self):
        """
        Apply policy coverage and update total amount due
        """
        if self.policy and self.status == 'UNPAID':
            discount = self.calculate_coverage_discount()
            self.total_amount_due = self.subtotal - discount
            self.save()
    
    def pay(self):
        """
        Mark bill as paid and update policy coverage
        """
        if self.status == 'UNPAID':
            self.status = 'PAID'
            
            # Update policy coverage if applied
            if self.policy and self.appointment:
                covered_amount = self.calculate_coverage_discount()
                
                # Update policy total covered
                self.policy.total_covered += covered_amount
                
                # Update policy status
                if self.policy.status == 0:  # If it's still "Created"
                    self.policy.status = 1  # Change to "Partially Claimed"
                
                self.policy.update_status()
                
                # Mark coverages as used and create covered treatment records
                for app_treatment in self.appointment.appointmenttreatment_set.all():
                    treatment_name = app_treatment.treatment.name
                    policy_coverage = self.policy.policycoverage_set.filter(
                        coverage__name=treatment_name,
                        used=False
                    ).first()
                    
                    if policy_coverage:
                        # Mark as used
                        policy_coverage.used = True
                        policy_coverage.save()
                        
                        # Create covered treatment record
                        coverage_amount = min(app_treatment.treatment.price, policy_coverage.coverage.coverage_amount)
                        BillCoveredTreatment.objects.create(
                            bill=self,
                            treatment_name=treatment_name,
                            treatment_price=app_treatment.treatment.price,
                            coverage_amount=coverage_amount
                        )
            
            self.save()

class BillCoveredTreatment(models.Model):
    """
    Model to store covered treatments for a bill
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='covered_treatments')
    treatment_name = models.CharField(max_length=255)
    treatment_price = models.DecimalField(max_digits=10, decimal_places=2)
    coverage_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'bill_covered_treatment'
    
    def __str__(self):
        return f"{self.bill.id} - {self.treatment_name}"