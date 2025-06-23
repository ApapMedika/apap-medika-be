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

class AdminSerializer(serializers.ModelSerializer):
    user = EndUserSerializer()
    
    class Meta:
        model = Admin
        fields = ['user']

class NurseSerializer(serializers.ModelSerializer):
    user = EndUserSerializer()
    
    class Meta:
        model = Nurse
        fields = ['user']

class PatientSerializer(serializers.ModelSerializer):
    user = EndUserSerializer()
    insurance_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['user', 'nik', 'birth_place', 'birth_date', 'p_class', 'insurance_limit']
    
    def get_insurance_limit(self, obj):
        insurance_limits = {
            1: 100000000,  # Class 1 - Rp 100,000,000
            2: 50000000,   # Class 2 - Rp 50,000,000
            3: 25000000,   # Class 3 - Rp 25,000,000
        }
        return insurance_limits.get(obj.p_class, 0)

class DoctorSerializer(serializers.ModelSerializer):
    user = EndUserSerializer()
    specialization_display = serializers.CharField(source='get_specialization_display', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ['id', 'user', 'specialization', 'specialization_display', 'years_of_experience', 'fee', 'schedules']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        # Generate doctor code
        doctor_count = Doctor.objects.count()
        specialization = validated_data['specialization']
        doctor_id = get_doctor_code(specialization, doctor_count + 1)
        validated_data['id'] = doctor_id
        return super().create(validated_data)

class PharmacistSerializer(serializers.ModelSerializer):
    user = EndUserSerializer()
    
    class Meta:
        model = Pharmacist
        fields = ['user']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              username=email, password=password)
            
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
            
            if user.deleted_at:
                msg = 'User account is deactivated.'
                raise serializers.ValidationError(msg, code='authorization')
            
        else:
            msg = 'Must include "email" and "password".'
            raise serializers.ValidationError(msg, code='authorization')
        
        attrs['user'] = user
        return attrs

class SignUpSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6)
    gender = serializers.BooleanField()
    role = serializers.ChoiceField(choices=EndUser.ROLE_CHOICES)
    
    # Patient specific fields
    nik = serializers.CharField(max_length=16, required=False)
    birth_place = serializers.CharField(max_length=255, required=False)
    birth_date = serializers.DateField(required=False)
    p_class = serializers.IntegerField(required=False)
    
    # Doctor specific fields
    specialization = serializers.IntegerField(required=False)
    years_of_experience = serializers.IntegerField(required=False)
    fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    schedules = serializers.ListField(child=serializers.IntegerField(), required=False)
    
    def validate_username(self, value):
        if EndUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value
    
    def validate_email(self, value):
        if EndUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value
    
    def validate_nik(self, value):
        if value and Patient.objects.filter(nik=value).exists():
            raise serializers.ValidationError("NIK already exists.")
        return value
    
    def validate(self, attrs):
        role = attrs.get('role')
        
        if role == 'PATIENT':
            required_fields = ['nik', 'birth_place', 'birth_date', 'p_class']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError(f"{field} is required for patients.")
        
        elif role == 'DOCTOR':
            required_fields = ['specialization', 'years_of_experience', 'fee', 'schedules']
            for field in required_fields:
                if not attrs.get(field):
                    raise serializers.ValidationError(f"{field} is required for doctors.")
        
        return attrs
    
    def create(self, validated_data):
        role = validated_data.pop('role')
        
        # Extract role-specific data
        patient_data = {}
        doctor_data = {}
        
        if role == 'PATIENT':
            patient_data = {
                'nik': validated_data.pop('nik'),
                'birth_place': validated_data.pop('birth_place'),
                'birth_date': validated_data.pop('birth_date'),
                'p_class': validated_data.pop('p_class', 3),
            }
        elif role == 'DOCTOR':
            doctor_data = {
                'specialization': validated_data.pop('specialization'),
                'years_of_experience': validated_data.pop('years_of_experience'),
                'fee': validated_data.pop('fee'),
                'schedules': validated_data.pop('schedules', []),
            }
        
        # Create EndUser
        validated_data['role'] = role
        validated_data['password'] = make_password(validated_data['password'])
        user = EndUser.objects.create(**validated_data)
        
        # Create role-specific profile
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
        
        return user

class UserDetailSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    doctor = DoctorSerializer(read_only=True)
    admin = AdminSerializer(read_only=True)
    nurse = NurseSerializer(read_only=True)
    pharmacist = PharmacistSerializer(read_only=True)
    
    class Meta:
        model = EndUser
        fields = ['id', 'name', 'username', 'email', 'gender', 'role', 'created_at', 'updated_at',
                 'patient', 'doctor', 'admin', 'nurse', 'pharmacist']
        read_only_fields = ['id', 'created_at', 'updated_at']

class UpgradeClassSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField()
    new_class = serializers.IntegerField()
    
    def validate_new_class(self, value):
        if value not in [1, 2, 3]:
            raise serializers.ValidationError("Invalid class. Must be 1, 2, or 3.")
        return value
    
    def validate(self, attrs):
        try:
            patient = Patient.objects.get(user__id=attrs['patient_id'])
            if patient.p_class <= attrs['new_class']:
                raise serializers.ValidationError("Can only upgrade to higher class.")
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found.")
        
        attrs['patient'] = patient
        return attrs