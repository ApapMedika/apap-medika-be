from django.contrib.auth.models import AbstractUser
from django.db import models
from common.models import TimestampedModel
import uuid

class EndUser(AbstractUser):
    """
    Custom user model that extends AbstractUser
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('NURSE', 'Nurse'),
        ('PATIENT', 'Patient'),
        ('DOCTOR', 'Doctor'),
        ('PHARMACIST', 'Pharmacist'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    gender = models.BooleanField()  # True: Female, False: Male
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        db_table = 'end_user'
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    @property
    def is_admin(self):
        return self.role == 'ADMIN'
    
    @property
    def is_doctor(self):
        return self.role == 'DOCTOR'
    
    @property
    def is_nurse(self):
        return self.role == 'NURSE'
    
    @property
    def is_patient(self):
        return self.role == 'PATIENT'
    
    @property
    def is_pharmacist(self):
        return self.role == 'PHARMACIST'

class Admin(models.Model):
    """
    Admin profile
    """
    user = models.OneToOneField(EndUser, on_delete=models.CASCADE, primary_key=True)
    
    class Meta:
        db_table = 'admin'
    
    def __str__(self):
        return f"Admin: {self.user.name}"

class Nurse(models.Model):
    """
    Nurse profile
    """
    user = models.OneToOneField(EndUser, on_delete=models.CASCADE, primary_key=True)
    
    class Meta:
        db_table = 'nurse'
    
    def __str__(self):
        return f"Nurse: {self.user.name}"

class Patient(models.Model):
    """
    Patient profile
    """
    PATIENT_CLASS_CHOICES = [
        (1, 'Class 1'),  # Limit: Rp 100,000,000
        (2, 'Class 2'),  # Limit: Rp 50,000,000
        (3, 'Class 3'),  # Limit: Rp 25,000,000
    ]
    
    user = models.OneToOneField(EndUser, on_delete=models.CASCADE, primary_key=True)
    nik = models.CharField(max_length=16, unique=True)
    birth_place = models.CharField(max_length=255)
    birth_date = models.DateField()
    p_class = models.IntegerField(choices=PATIENT_CLASS_CHOICES, default=3)
    
    class Meta:
        db_table = 'patient'
    
    def __str__(self):
        return f"Patient: {self.user.name} ({self.nik})"
    
    @property
    def insurance_limit(self):
        """Get insurance limit based on patient class"""
        limits = {1: 100000000, 2: 50000000, 3: 25000000}
        return limits.get(self.p_class, 0)
    
    def get_available_insurance_limit(self):
        """Calculate available insurance limit"""
        total_coverage_used = 0
        # Import here to avoid circular import
        from insurance.models import Policy
        
        active_policies = Policy.objects.filter(
            patient=self,
            status__in=[0, 1, 2],  # Created, Partially Claimed, Fully Claimed
            deleted_at__isnull=True
        )
        
        for policy in active_policies:
            total_coverage_used += policy.total_coverage
        
        return self.insurance_limit - total_coverage_used

class Doctor(models.Model):
    """
    Doctor profile
    """
    SPECIALIZATION_CHOICES = [
        (0, 'General Practitioner'),
        (1, 'Dentist'),
        (2, 'Pediatrician'),
        (3, 'Surgery'),
        (4, 'Plastic, Reconstructive, and Aesthetic Surgery'),
        (5, 'Heart and Blood Vessels'),
        (6, 'Skin and Venereal Diseases'),
        (7, 'Eyes'),
        (8, 'Obstetrics and Gynecology'),
        (9, 'Internal Medicine'),
        (10, 'Lungs'),
        (11, 'Ear, Nose, Throat, Head and Neck Surgery'),
        (12, 'Radiology'),
        (13, 'Mental Health'),
        (14, 'Anesthesia'),
        (15, 'Neurology'),
        (16, 'Urology'),
    ]
    
    SCHEDULE_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    id = models.CharField(max_length=6, primary_key=True)  # Generated code
    user = models.OneToOneField(EndUser, on_delete=models.CASCADE)
    specialization = models.IntegerField(choices=SPECIALIZATION_CHOICES)
    years_of_experience = models.IntegerField()
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    schedules = models.JSONField(default=list)  # List of schedule days
    
    class Meta:
        db_table = 'doctor'
    
    def __str__(self):
        return f"Dr. {self.user.name} ({self.get_specialization_display()})"
    
    @property
    def specialization_code(self):
        """Get 3-letter code for specialization"""
        codes = {
            0: "UMM", 1: "GGI", 2: "ANK", 3: "BDH", 4: "PRE", 5: "JPD",
            6: "KKL", 7: "MTA", 8: "OBG", 9: "PDL", 10: "PRU", 11: "ENT",
            12: "RAD", 13: "KSJ", 14: "ANS", 15: "NRO", 16: "URO"
        }
        return codes.get(self.specialization, "UMM")

class Pharmacist(models.Model):
    """
    Pharmacist profile
    """
    user = models.OneToOneField(EndUser, on_delete=models.CASCADE, primary_key=True)
    
    class Meta:
        db_table = 'pharmacist'
    
    def __str__(self):
        return f"Pharmacist: {self.user.name}"