from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Treatment, Appointment, AppointmentTreatment
from profiles.models import Patient, Doctor, EndUser

class TreatmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Treatment
        fields = ['id', 'name', 'price']

class AppointmentTreatmentSerializer(serializers.ModelSerializer):
    treatment_name = serializers.CharField(source='treatment.name', read_only=True)
    treatment_price = serializers.DecimalField(source='treatment.price', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = AppointmentTreatment
        fields = ['id', 'treatment', 'treatment_name', 'treatment_price']

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.name', read_only=True)
    doctor_specialization = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    patient_nik = serializers.CharField(source='patient.nik', read_only=True)
    status_display = serializers.CharField(source='get_status_display_custom', read_only=True)
    treatments = AppointmentTreatmentSerializer(source='appointmenttreatment_set', many=True, read_only=True)
    
    class Meta:
        model = Appointment
        fields = ['id', 'doctor', 'doctor_name', 'doctor_specialization', 'patient', 'patient_name', 'patient_nik',
                 'date', 'diagnosis', 'status', 'status_display', 'total_fee', 'treatments',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'total_fee', 'created_at', 'updated_at']
    
    def get_doctor_specialization(self, obj):
        spec_map = {
            0: "General Practitioner (dr.)",
            1: "Dentist (drg.)",
            2: "Pediatrician (Sp.A)",
            3: "Surgery (Sp.B)",
            4: "Plastic, Reconstructive, and Aesthetic Surgery (Sp.BP-RE)",
            5: "Heart and Blood Vessels (Sp.JP)",
            6: "Skin and Venereal Diseases (Sp.KK)",
            7: "Eyes (Sp.M)",
            8: "Obstetrics and Gynecology (Sp.OG)",
            9: "Internal Medicine (Sp.PD)",
            10: "Lungs (Sp.P)",
            11: "Ear, Nose, Throat, Head and Neck Surgery (Sp.THT-KL)",
            12: "Radiology (Sp.Rad)",
            13: "Mental Health (Sp.KJ)",
            14: "Anesthesia (Sp.An)",
            15: "Neurology (Sp.N)",
            16: "Urology (Sp.U)",
        }
        return spec_map.get(obj.doctor.specialization, "Unknown")

class CreateAppointmentSerializer(serializers.Serializer):
    # Existing patient
    patient_nik = serializers.CharField(max_length=16, required=False)
    
    # New patient data
    patient_name = serializers.CharField(required=False)
    patient_email = serializers.EmailField(required=False)
    patient_gender = serializers.BooleanField(required=False)
    patient_birth_place = serializers.CharField(required=False)
    patient_birth_date = serializers.DateField(required=False)
    patient_class = serializers.IntegerField(required=False)
    
    # Appointment data
    doctor = serializers.CharField()
    date = serializers.DateTimeField()
    
    def validate_doctor(self, value):
        try:
            doctor = Doctor.objects.get(id=value, user__deleted_at__isnull=True)
            return doctor
        except Doctor.DoesNotExist:
            raise serializers.ValidationError("Doctor not found.")
    
    def validate_date(self, value):
        # Check if date is in the future
        if value <= timezone.now():
            raise serializers.ValidationError("Appointment date must be in the future.")
        
        return value
    
    def validate(self, attrs):
        doctor = attrs.get('doctor')
        date = attrs.get('date')
        patient_nik = attrs.get('patient_nik')
        
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
        
        # Check if doctor is available on this date
        if date and doctor:
            # Check if doctor practices on this day
            weekday = date.weekday()
            if weekday not in doctor.schedules:
                raise serializers.ValidationError(
                    f"Doctor does not practice on {date.strftime('%A')}."
                )
            
            # Check for duplicate appointment
            if Appointment.objects.filter(
                doctor=doctor,
                date=date,
                deleted_at__isnull=True
            ).exists():
                raise serializers.ValidationError(
                    "Doctor already has an appointment at this time."
                )
        
        # Get or validate patient
        if patient_nik:
            try:
                patient = Patient.objects.get(nik=patient_nik, user__deleted_at__isnull=True)
                attrs['patient'] = patient
            except Patient.DoesNotExist:
                raise serializers.ValidationError("Patient with this NIK not found.")
        
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
            
            # Generate appointment ID
            doctor = validated_data['doctor']
            date = validated_data['date']
            
            # Get specialty code
            specialty_codes = {
                0: "UMM", 1: "GGI", 2: "ANK", 3: "BDH", 4: "PRE", 5: "JPD",
                6: "KKL", 7: "MTA", 8: "OBG", 9: "PDL", 10: "PRU", 11: "ENT",
                12: "RAD", 13: "KSJ", 14: "ANS", 15: "NRO", 16: "URO"
            }
            specialty_code = specialty_codes.get(doctor.specialization, "UMM")
            
            # Get date string (DDMM)
            date_str = date.strftime("%d%m")
            
            # Get sequence number for this doctor and date
            same_day_appointments = Appointment.objects.filter(
                doctor=doctor,
                date__date=date.date(),
                deleted_at__isnull=True
            ).count()
            sequence = str(same_day_appointments + 1).zfill(3)
            
            appointment_id = f"{specialty_code}{date_str}{sequence}"
            
            # Create appointment
            appointment_data = {
                'id': appointment_id,
                'doctor': doctor,
                'patient': patient,
                'date': date,
                'status': 0,  # Created
            }
            
            # Set user fields
            request = self.context.get('request')
            if request and request.user:
                appointment_data['created_by'] = request.user.username
                appointment_data['updated_by'] = request.user.username
            
            appointment = Appointment.objects.create(**appointment_data)
            
            # Create bill for this appointment
            from bill.models import Bill
            Bill.objects.create(
                patient=patient,
                appointment=appointment,
                status='TREATMENT_IN_PROGRESS',
                created_by=appointment_data.get('created_by'),
                updated_by=appointment_data.get('updated_by')
            )
            
            return appointment

class UpdateAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ['doctor', 'date']
    
    def validate_date(self, value):
        # Check if appointment can be updated (not within 1 day)
        if value <= timezone.now() + timedelta(days=1):
            raise serializers.ValidationError(
                "Cannot update appointment within 1 day of appointment date."
            )
        
        return value
    
    def validate(self, attrs):
        doctor = attrs.get('doctor')
        date = attrs.get('date')
        
        if date and doctor:
            # Check if doctor practices on this day
            weekday = date.weekday()
            if weekday not in doctor.schedules:
                raise serializers.ValidationError(
                    f"Doctor does not practice on {date.strftime('%A')}."
                )
            
            # Check for duplicate appointment (excluding current)
            existing = Appointment.objects.filter(
                doctor=doctor,
                date=date,
                deleted_at__isnull=True
            ).exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise serializers.ValidationError(
                    "Doctor already has an appointment at this time."
                )
        
        return attrs
    
    def update(self, instance, validated_data):
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user.username
        
        return super().update(instance, validated_data)

class UpdateDiagnosisTreatmentSerializer(serializers.Serializer):
    diagnosis = serializers.CharField()
    treatments = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    
    def validate_treatments(self, value):
        """
        Validate that all treatment IDs exist
        """
        for treatment_id in value:
            try:
                Treatment.objects.get(id=treatment_id)
            except Treatment.DoesNotExist:
                raise serializers.ValidationError(f"Treatment with ID {treatment_id} does not exist.")
        
        return value
    
    def update(self, instance, validated_data):
        if instance.status != 0:
            raise serializers.ValidationError(
                "Can only update diagnosis and treatments for appointments with Created status."
            )
        
        # Update diagnosis
        instance.diagnosis = validated_data['diagnosis']
        
        # Clear existing treatments
        instance.appointmenttreatment_set.all().delete()
        
        # Add new treatments
        total_fee = 0
        for treatment_id in validated_data['treatments']:
            treatment = Treatment.objects.get(id=treatment_id)
            AppointmentTreatment.objects.create(
                appointment=instance,
                treatment=treatment
            )
            total_fee += treatment.price
        
        instance.total_fee = total_fee
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            instance.updated_by = request.user.username
        
        instance.save()
        return instance

class UpdateAppointmentStatusSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['done', 'cancel'])
    
    def validate(self, attrs):
        action = attrs['action']
        instance = self.instance
        
        if action == 'done':
            if not instance.diagnosis or not instance.appointmenttreatment_set.exists():
                raise serializers.ValidationError(
                    "Cannot mark appointment as done without diagnosis and treatments."
                )
        elif action == 'cancel':
            # Check if within 1 day of appointment
            if instance.date <= timezone.now() + timedelta(days=1):
                raise serializers.ValidationError(
                    "Cannot cancel appointment within 1 day of appointment date."
                )
        
        return attrs
    
    def update(self, instance, validated_data):
        action = validated_data['action']
        
        if action == 'done':
            instance.status = 1  # Done
        elif action == 'cancel':
            instance.status = 2  # Cancelled
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            instance.updated_by = request.user.username
        
        instance.save()
        
        # Update related bill status
        try:
            from bill.models import Bill
            bill = Bill.objects.get(appointment=instance)
            bill.update_status()
        except:
            pass
        
        return instance