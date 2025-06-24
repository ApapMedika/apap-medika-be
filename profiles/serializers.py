from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from .models import EndUser, Admin, Nurse, Patient, Doctor, Pharmacist
from common.utils import generate_jwt_token, get_doctor_code

class EndUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = EndUser
        fields = ['id', 'name', 'username', 'email', 'gender', 'role', 'password', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class PatientDetailSerializer(serializers.ModelSerializer):
    insurance_limit = serializers.SerializerMethodField()
    available_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['nik', 'birth_place', 'birth_date', 'p_class', 'insurance_limit', 'available_limit']
    
    def get_insurance_limit(self, obj):
        return obj.insurance_limit
    
    def get_available_limit(self, obj):
        return obj.get_available_insurance_limit()

class DoctorDetailSerializer(serializers.ModelSerializer):
    specialization_display = serializers.CharField(source='get_specialization_display', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ['id', 'specialization', 'specialization_display', 'years_of_experience', 'fee', 'schedules']

class UserDetailSerializer(serializers.ModelSerializer):
    patient = PatientDetailSerializer(read_only=True)
    doctor = DoctorDetailSerializer(read_only=True)
    
    class Meta:
        model = EndUser
        fields = ['id', 'name', 'username', 'email', 'gender', 'role', 'created_at', 'updated_at', 'patient', 'doctor']
        read_only_fields = ['id', 'created_at', 'updated_at']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid email or password.', code='authorization')
            
            if user.deleted_at:
                raise serializers.ValidationError('User account is deactivated.', code='authorization')
            
        else:
            raise serializers.ValidationError('Must include "email" and "password".', code='authorization')
        
        attrs['user'] = user
        return attrs

class SignUpSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6)
    gender = serializers.BooleanField()
    role = serializers.ChoiceField(choices=[choice[0] for choice in EndUser.ROLE_CHOICES])
    
    # Nested patient data
    patient_data = serializers.DictField(required=False)
    # Nested doctor data  
    doctor_data = serializers.DictField(required=False)
    
    def validate_username(self, value):
        if EndUser.objects.filter(username=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        if EndUser.objects.filter(email=value, deleted_at__isnull=True).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate(self, attrs):
        role = attrs.get('role')
        patient_data = attrs.get('patient_data', {})
        doctor_data = attrs.get('doctor_data', {})
        
        if role == 'PATIENT':
            # Validate patient data
            required_fields = ['nik', 'birth_place', 'birth_date', 'p_class']
            for field in required_fields:
                if not patient_data.get(field):
                    raise serializers.ValidationError(f"Patient {field} is required.")
            
            # Check if NIK already exists
            nik = patient_data.get('nik')
            if Patient.objects.filter(nik=nik).exists():
                raise serializers.ValidationError("NIK already exists.")
            
            # Validate NIK format (16 digits)
            if len(nik) != 16 or not nik.isdigit():
                raise serializers.ValidationError("NIK must be exactly 16 digits.")
        
        elif role == 'DOCTOR':
            # Validate doctor data
            required_fields = ['specialization', 'years_of_experience', 'fee', 'schedules']
            for field in required_fields:
                if field not in doctor_data:
                    raise serializers.ValidationError(f"Doctor {field} is required.")
            
            # Validate schedules is a list
            if not isinstance(doctor_data.get('schedules'), list):
                raise serializers.ValidationError("Doctor schedules must be a list.")
        
        return attrs
    
    def create(self, validated_data):
        role = validated_data.pop('role')
        patient_data = validated_data.pop('patient_data', {})
        doctor_data = validated_data.pop('doctor_data', {})
        
        # Create EndUser
        validated_data['role'] = role
        validated_data['password'] = make_password(validated_data['password'])
        user = EndUser.objects.create(**validated_data)
        
        # Create role-specific profile
        try:
            if role == 'ADMIN':
                Admin.objects.create(user=user)
            elif role == 'NURSE':
                Nurse.objects.create(user=user)
            elif role == 'PATIENT':
                Patient.objects.create(user=user, **patient_data)
            elif role == 'DOCTOR':
                # Generate doctor code
                doctor_count = Doctor.objects.count()
                doctor_id = get_doctor_code(doctor_data['specialization'], doctor_count + 1)
                Doctor.objects.create(id=doctor_id, user=user, **doctor_data)
            elif role == 'PHARMACIST':
                Pharmacist.objects.create(user=user)
        except Exception as e:
            # If profile creation fails, delete the user
            user.delete()
            raise serializers.ValidationError(f"Failed to create {role.lower()} profile: {str(e)}")
        
        return user

class PatientSerializer(serializers.ModelSerializer):
    user = EndUserSerializer(read_only=True)
    insurance_limit = serializers.SerializerMethodField()
    available_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['user', 'nik', 'birth_place', 'birth_date', 'p_class', 'insurance_limit', 'available_limit']
    
    def get_insurance_limit(self, obj):
        return obj.insurance_limit
    
    def get_available_limit(self, obj):
        return obj.get_available_insurance_limit()

class DoctorSerializer(serializers.ModelSerializer):
    user = EndUserSerializer(read_only=True)
    specialization_display = serializers.CharField(source='get_specialization_display', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ['id', 'user', 'specialization', 'specialization_display', 'years_of_experience', 'fee', 'schedules']

class UpgradeClassSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    new_class = serializers.IntegerField()
    
    def validate_new_class(self, value):
        if value not in [1, 2, 3]:
            raise serializers.ValidationError("Invalid class. Must be 1, 2, or 3.")
        return value
    
    def validate(self, attrs):
        try:
            patient = Patient.objects.get(user__id=attrs['patient_id'], user__deleted_at__isnull=True)
            if patient.p_class <= attrs['new_class']:
                raise serializers.ValidationError("Can only upgrade to higher class.")
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")
        
        attrs['patient'] = patient
        return attrs