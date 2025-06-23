from django.db import models
from common.models import UserActionModel
from profiles.models import Patient
import uuid

class Coverage(models.Model):
    """
    Coverage model - static data for insurance coverage types
    """
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    coverage_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'coverage'
    
    def __str__(self):
        return f"{self.id} - {self.name}"

class Company(UserActionModel):
    """
    Insurance Company model
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    contact = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.TextField()
    
    class Meta:
        db_table = 'company'
    
    def __str__(self):
        return self.name
    
    @property
    def total_coverage(self):
        """
        Calculate total coverage amount from all company coverages
        """
        return sum(cc.coverage.coverage_amount for cc in self.companycoverage_set.all())
    
    @property
    def policy_count(self):
        """
        Get number of policies for this company
        """
        return self.policy_set.filter(deleted_at__isnull=True).count()

class CompanyCoverage(models.Model):
    """
    Junction table for Company and Coverage (many-to-many)
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    coverage = models.ForeignKey(Coverage, on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'company_coverage'
        unique_together = ['company', 'coverage']
    
    def __str__(self):
        return f"{self.company.name} - {self.coverage.name}"

class Policy(UserActionModel):
    """
    Insurance Policy model
    """
    STATUS_CHOICES = [
        (0, 'Created'),
        (1, 'Partially Claimed'),
        (2, 'Fully Claimed'),
        (3, 'Expired'),
        (4, 'Cancelled'),
    ]
    
    id = models.CharField(max_length=12, primary_key=True)  # Generated format
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    expiry_date = models.DateField()
    total_coverage = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_covered = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'policy'
    
    def __str__(self):
        return f"{self.id} - {self.patient.user.name}"
    
    def get_status_display_custom(self):
        status_map = {
            0: 'Created',
            1: 'Partially Claimed',
            2: 'Fully Claimed',
            3: 'Expired',
            4: 'Cancelled',
        }
        return status_map.get(self.status, 'Unknown')
    
    def update_status(self):
        """
        Update policy status based on business logic
        """
        from datetime import date
        
        # Check if expired
        if self.expiry_date < date.today() and self.status not in [2, 4]:
            self.status = 3  # Expired
        # Check if fully claimed
        elif self.total_covered >= self.total_coverage and self.status != 4:
            self.status = 2  # Fully Claimed
        # Check if partially claimed
        elif self.total_covered > 0 and self.status not in [2, 3, 4]:
            self.status = 1  # Partially Claimed
        
        self.save()
    
    def get_available_coverage(self):
        """
        Get remaining coverage amount
        """
        return self.total_coverage - self.total_covered

class PolicyCoverage(models.Model):
    """
    Junction table for Policy and Coverage with usage tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    coverage = models.ForeignKey(Coverage, on_delete=models.CASCADE)
    used = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'policy_coverage'
        unique_together = ['policy', 'coverage']
    
    def __str__(self):
        return f"{self.policy.id} - {self.coverage.name}"