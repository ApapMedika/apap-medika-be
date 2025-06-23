from rest_framework import serializers
from django.utils import timezone
from .models import Coverage, Company, CompanyCoverage, Policy, PolicyCoverage
from profiles.models import Patient, EndUser

class CoverageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coverage
        fields = ['id', 'name', 'coverage_amount']

class CompanyCoverageSerializer(serializers.ModelSerializer):
    coverage_name = serializers.CharField(source='coverage.name', read_only=True)
    coverage_amount = serializers.DecimalField(source='coverage.coverage_amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CompanyCoverage
        fields = ['id', 'coverage', 'coverage_name', 'coverage_amount']

class CompanySerializer(serializers.ModelSerializer):
    coverages = CompanyCoverageSerializer(source='companycoverage_set', many=True, read_only=True)
    total_coverage = serializers.ReadOnlyField()
    policy_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Company
        fields = ['id', 'name', 'contact', 'email', 'address', 'total_coverage', 'policy_count', 'coverages',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'created_at', 'updated_at']

class CreateCompanySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    contact = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    address = serializers.CharField()
    coverages = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    
    def validate_coverages(self, value):
        """
        Validate that all coverage IDs exist
        """
        for coverage_id in value:
            try:
                Coverage.objects.get(id=coverage_id)
            except Coverage.DoesNotExist:
                raise serializers.ValidationError(f"Coverage with ID {coverage_id} does not exist.")
        
        # Check for duplicates
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate coverages are not allowed.")
        
        return value
    
    def create(self, validated_data):
        coverages = validated_data.pop('coverages')
        
        # Set user fields
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user.username
            validated_data['updated_by'] = request.user.username
        
        # Create company
        company = Company.objects.create(**validated_data)
        
        # Add coverages
        for coverage_id in coverages:
            coverage = Coverage.objects.get(id=coverage_id)
            CompanyCoverage.objects.create(
                company=company,
                coverage=coverage
            )
        
        return company

class UpdateCompanySerializer(serializers.ModelSerializer):
    coverages = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        required=False
    )
    
    class Meta:
        model = Company
        fields = ['name', 'contact', 'email', 'address', 'coverages']
    
    def validate_coverages(self, value):
        """
        Validate that all coverage IDs exist
        """
        if value:
            for coverage_id in value:
                try:
                    Coverage.objects.get(id=coverage_id)
                except Coverage.DoesNotExist:
                    raise serializers.ValidationError(f"Coverage with ID {coverage_id} does not exist.")
            
            # Check for duplicates
            if len(set(value)) != len(value):
                raise serializers.ValidationError("Duplicate coverages are not allowed.")
        
        return value
    
    def validate(self, attrs):
        # Check if company has related policies (cannot change coverages)
        if 'coverages' in attrs and self.instance.policy_count > 0:
            raise serializers.ValidationError(
                "Cannot change coverages for company with existing policies."
            )
        
        return attrs
    
    def update(self, instance, validated_data):
        coverages = validated_data.pop('coverages', None)
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user.username
        
        # Update company fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update coverages if provided
        if coverages is not None:
            # Remove existing coverages
            instance.companycoverage_set.all().delete()
            
            # Add new coverages
            for coverage_id in coverages:
                coverage = Coverage.objects.get(id=coverage_id)
                CompanyCoverage.objects.create(
                    company=instance,
                    coverage=coverage
                )
        
        return instance

class PolicyCoverageSerializer(serializers.ModelSerializer):
    coverage_name = serializers.CharField(source='coverage.name', read_only=True)
    coverage_amount = serializers.DecimalField(source='coverage.coverage_amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PolicyCoverage
        fields = ['id', 'coverage', 'coverage_name', 'coverage_amount', 'used']

class PolicySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    patient_nik = serializers.CharField(source='patient.nik', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display_custom', read_only=True)
    coverages = PolicyCoverageSerializer(source='policycoverage_set', many=True, read_only=True)
    available_coverage = serializers.SerializerMethodField()
    
    class Meta:
        model = Policy
        fields = ['id', 'patient', 'patient_name', 'patient_nik', 'company', 'company_name',
                 'status', 'status_display', 'expiry_date', 'total_coverage', 'total_covered',
                 'available_coverage', 'coverages',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'total_coverage', 'total_covered', 'status', 'created_at', 'updated_at']
    
    def get_available_coverage(self, obj):
        return obj.get_available_coverage()

class CreatePolicySerializer(serializers.Serializer):
    # Existing patient
    patient_nik = serializers.CharField(max_length=16, required=False)
    
    # New patient data
    patient_name = serializers.CharField(required=False)
    patient_email = serializers.EmailField(required=False)
    patient_gender = serializers.BooleanField(required=False)
    patient_birth_place = serializers.CharField(required=False)
    patient_birth_date = serializers.DateField(required=False)
    patient_class = serializers.IntegerField(required=False)
    
    # Policy data
    company = serializers.UUIDField()
    expiry_date = serializers.DateField()
    
    def validate_company(self, value):
        try:
            company = Company.objects.get(id=value, deleted_at__isnull=True)
            return company
        except Company.DoesNotExist:
            raise serializers.ValidationError("Company not found.")
    
    def validate_expiry_date(self, value):
        if value <= timezone.now().date():
            raise serializers.ValidationError("Expiry date must be in the future.")
        
        return value
    
    def validate(self, attrs):
        patient_nik = attrs.get('patient_nik')
        company = attrs.get('company')
        
        # Either patient_nik or new patient data must be provided
        if not patient_nik and not all([
            attrs.get('patient_name'),
            attrs.get('patient_email'),
            attrs.get('patient_birth_place'),
            attrs.get('patient_birth_date')
        ]):
            raise serializers.ValidationError(
                "Either patient_nik or complete new patient data must be provided."
            )
        
        # Get or validate patient
        if patient_nik:
            try:
                patient = Patient.objects.get(nik=patient_nik, user__deleted_at__isnull=True)
                attrs['patient'] = patient
            except Patient.DoesNotExist:
                raise serializers.ValidationError("Patient with this NIK not found.")
        
        # Check if patient already has policy with this company
        if 'patient' in attrs and company:
            existing_policy = Policy.objects.filter(
                patient=attrs['patient'],
                company=company,
                status__in=[0, 1, 2],  # Created, Partially Claimed, Fully Claimed
                deleted_at__isnull=True
            ).exists()
            
            if existing_policy:
                raise serializers.ValidationError(
                    "Patient already has an active policy with this company."
                )
        
        # Check patient's available insurance limit
        if 'patient' in attrs and company:
            patient = attrs['patient']
            
            # Calculate patient's insurance limit
            insurance_limits = {1: 100000000, 2: 50000000, 3: 25000000}
            total_limit = insurance_limits.get(patient.p_class, 0)
            
            # Calculate used coverage
            used_coverage = Policy.objects.filter(
                patient=patient,
                status__in=[0, 1, 2],  # Exclude cancelled and expired
                deleted_at__isnull=True
            ).aggregate(
                total=models.Sum('total_coverage')
            )['total'] or 0
            
            available_limit = total_limit - used_coverage
            
            if company.total_coverage > available_limit:
                raise serializers.ValidationError(
                    f"Company total coverage (Rp {company.total_coverage:,.2f}) exceeds "
                    f"patient's available limit (Rp {available_limit:,.2f}). "
                    f"Please upgrade patient class first."
                )
        
        return attrs
    
    def create(self, validated_data):
        from django.contrib.auth.hashers import make_password
        from django.db import transaction
        
        with transaction.atomic():
            # Get or create patient
            if 'patient' in validated_data:
                patient = validated_data['patient']
            else:
                # Create new patient
                user_data = {
                    'name': validated_data['patient_name'],
                    'username': validated_data['patient_nik'],
                    'email': validated_data['patient_email'],
                    'gender': validated_data['patient_gender'],
                    'role': 'PATIENT',
                    'password': make_password('defaultpassword123')
                }
                user = EndUser.objects.create(**user_data)
                
                patient_data = {
                    'user': user,
                    'nik': validated_data['patient_nik'],
                    'birth_place': validated_data['patient_birth_place'],
                    'birth_date': validated_data['patient_birth_date'],
                    'p_class': validated_data.get('patient_class', 3)
                }
                patient = Patient.objects.create(**patient_data)
            
            # Generate policy ID
            company = validated_data['company']
            
            # Get patient initials
            name_parts = patient.user.name.strip().split()
            if len(name_parts) >= 2:
                patient_initials = (name_parts[0][:1] + name_parts[-1][:1]).upper()
            else:
                patient_initials = name_parts[0][:2].upper()
            
            # Get company initials
            company_initials = company.name[:3].upper()
            
            # Get sequence
            total_policies = Policy.objects.count()
            sequence = str(total_policies + 1).zfill(4)
            
            policy_id = f"POL{patient_initials}{company_initials}{sequence}"
            
            # Create policy
            policy_data = {
                'id': policy_id,
                'patient': patient,
                'company': company,
                'expiry_date': validated_data['expiry_date'],
                'total_coverage': company.total_coverage,
                'status': 0,  # Created
            }
            
            # Set user fields
            request = self.context.get('request')
            if request and request.user:
                policy_data['created_by'] = request.user.username
                policy_data['updated_by'] = request.user.username
            
            policy = Policy.objects.create(**policy_data)
            
            # Create policy coverages
            for company_coverage in company.companycoverage_set.all():
                PolicyCoverage.objects.create(
                    policy=policy,
                    coverage=company_coverage.coverage,
                    used=False
                )
            
            return policy

class UpdatePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = ['expiry_date']
    
    def validate_expiry_date(self, value):
        if value <= timezone.now().date():
            raise serializers.ValidationError("Expiry date must be in the future.")
        
        return value
    
    def update(self, instance, validated_data):
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user.username
        
        # Update and recalculate status if expired
        instance = super().update(instance, validated_data)
        instance.update_status()
        
        return instance

class PolicyForTreatmentsSerializer(serializers.Serializer):
    treatments = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    
    def validate_treatments(self, value):
        """
        Validate that all treatment names exist in coverages
        """
        for treatment_name in value:
            if not Coverage.objects.filter(name=treatment_name).exists():
                raise serializers.ValidationError(f"Treatment '{treatment_name}' not found in coverages.")
        
        return value