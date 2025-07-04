from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from .models import Room, Facility, Reservation, ReservationFacility
from profiles.models import Patient, Nurse, EndUser

class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ['id', 'name', 'fee', 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ReservationFacilitySerializer(serializers.ModelSerializer):
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    facility_fee = serializers.DecimalField(source='facility.fee', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ReservationFacility
        fields = ['id', 'facility', 'facility_name', 'facility_fee']

class RoomSerializer(serializers.ModelSerializer):
    available_capacity = serializers.SerializerMethodField()
    
    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'max_capacity', 'price_per_day', 'available_capacity',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_available_capacity(self, obj):
        # Get date range from context if available
        request = self.context.get('request')
        if request:
            date_in = request.query_params.get('date_in')
            date_out = request.query_params.get('date_out')
            
            if date_in and date_out:
                try:
                    date_in = datetime.strptime(date_in, '%Y-%m-%d').date()
                    date_out = datetime.strptime(date_out, '%Y-%m-%d').date()
                    return obj.get_available_capacity(date_in, date_out)
                except ValueError:
                    pass
        
        # Return max capacity if no date range specified
        return obj.max_capacity
    
    def create(self, validated_data):
        # Generate room ID
        room_count = Room.objects.count()
        room_id = f"RM{str(room_count + 1).zfill(4)}"
        validated_data['id'] = room_id
        
        # Set user fields
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user.username
            validated_data['updated_by'] = request.user.username
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user.username
        
        return super().update(instance, validated_data)

class ReservationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    patient_nik = serializers.CharField(source='patient.nik', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    assigned_nurse_name = serializers.CharField(source='assigned_nurse.user.name', read_only=True)
    facilities = ReservationFacilitySerializer(source='reservationfacility_set', many=True, read_only=True)
    days_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Reservation
        fields = ['id', 'patient', 'patient_name', 'patient_nik', 'room', 'room_name',
                 'appointment', 'assigned_nurse', 'assigned_nurse_name', 'date_in', 'date_out',
                 'total_fee', 'facilities', 'days_count',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'total_fee', 'created_at', 'updated_at']
    
    def get_days_count(self, obj):
        return (obj.date_out - obj.date_in).days + 1

class CreateReservationSerializer(serializers.Serializer):
    # Existing patient
    patient_nik = serializers.CharField(max_length=16, required=False)
    
    # New patient data
    patient_name = serializers.CharField(required=False)
    patient_email = serializers.EmailField(required=False)
    patient_gender = serializers.BooleanField(required=False)
    patient_birth_place = serializers.CharField(required=False)
    patient_birth_date = serializers.DateField(required=False)
    patient_class = serializers.IntegerField(required=False)
    
    # Reservation data
    room = serializers.CharField()
    date_in = serializers.DateField()
    date_out = serializers.DateField()
    appointment = serializers.CharField(required=False)
    facilities = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    
    def validate_room(self, value):
        try:
            room = Room.objects.get(id=value, deleted_at__isnull=True)
            return room
        except Room.DoesNotExist:
            raise serializers.ValidationError("Room not found.")
    
    def validate_appointment(self, value):
        if value:
            try:
                from appointment.models import Appointment
                appointment = Appointment.objects.get(id=value, deleted_at__isnull=True)
                return appointment
            except:
                raise serializers.ValidationError("Appointment not found.")
        return None
    
    def validate_facilities(self, value):
        facilities = []
        for facility_id in value:
            try:
                facility = Facility.objects.get(id=facility_id, deleted_at__isnull=True)
                facilities.append(facility)
            except Facility.DoesNotExist:
                raise serializers.ValidationError(f"Facility with ID {facility_id} not found.")
        
        # Check for duplicates
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate facilities are not allowed.")
        
        return facilities
    
    def validate(self, attrs):
        room = attrs.get('room')
        date_in = attrs.get('date_in')
        date_out = attrs.get('date_out')
        patient_nik = attrs.get('patient_nik')
        appointment = attrs.get('appointment')
        
        # Date validation
        if date_out <= date_in:
            raise serializers.ValidationError("Date out must be after date in.")
        
        if date_in < timezone.now().date():
            raise serializers.ValidationError("Date in cannot be in the past.")
        
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
        
        # Check room availability
        if room and room.get_available_capacity(date_in, date_out) <= 0:
            raise serializers.ValidationError("Room is not available for the selected dates.")
        
        # Validate appointment if provided
        if appointment:
            # Check if appointment belongs to the patient
            if patient_nik:
                try:
                    patient = Patient.objects.get(nik=patient_nik, user__deleted_at__isnull=True)
                    if appointment.patient != patient:
                        raise serializers.ValidationError("Appointment does not belong to this patient.")
                    attrs['patient'] = patient
                except Patient.DoesNotExist:
                    raise serializers.ValidationError("Patient with this NIK not found.")
        elif patient_nik:
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
            
            # Generate reservation ID
            room = validated_data['room']
            date_in = validated_data['date_in']
            date_out = validated_data['date_out']
            
            # Calculate date difference (last 2 digits)
            date_diff = (date_out - date_in).days + 1
            date_diff_str = str(date_diff)[-2:].zfill(2)
            
            # Get day of week code
            day_names = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
            day_code = day_names[date_in.weekday()]
            
            # Get last 4 digits of NIK
            nik_last_4 = patient.nik[-4:]
            
            # Get total reservations count
            total_reservations = Reservation.objects.count()
            sequence = str(total_reservations + 1).zfill(4)
            
            reservation_id = f"RES{date_diff_str}{day_code}{nik_last_4}{sequence}"
            
            # Get assigned nurse (current user if nurse, or first available nurse)
            assigned_nurse = None
            request = self.context.get('request')
            if request and request.user and request.user.role == 'NURSE':
                assigned_nurse = request.user.nurse
            else:
                # Get first available nurse
                assigned_nurse = Nurse.objects.filter(user__deleted_at__isnull=True).first()
            
            # Create reservation
            reservation_data = {
                'id': reservation_id,
                'patient': patient,
                'room': room,
                'date_in': date_in,
                'date_out': date_out,
                'assigned_nurse': assigned_nurse,
            }
            
            if validated_data.get('appointment'):
                reservation_data['appointment'] = validated_data['appointment']
            
            # Set user fields
            if request and request.user:
                reservation_data['created_by'] = request.user.username
                reservation_data['updated_by'] = request.user.username
            
            reservation = Reservation.objects.create(**reservation_data)
            
            # Add facilities
            for facility in validated_data.get('facilities', []):
                ReservationFacility.objects.create(
                    reservation=reservation,
                    facility=facility
                )
            
            # Calculate and set total fee
            reservation.total_fee = reservation.calculate_total_fee()
            reservation.save()
            
            # Create bill if appointment ID is null (PBI-BE-H3)
            if not validated_data.get('appointment'):
                from bill.models import Bill
                Bill.objects.create(
                    patient=patient,
                    reservation=reservation,
                    status='TREATMENT_IN_PROGRESS',
                    created_by=reservation_data.get('created_by'),
                    updated_by=reservation_data.get('updated_by')
                )
            
            return reservation

class UpdateReservationRoomSerializer(serializers.Serializer):
    room = serializers.CharField()
    date_in = serializers.DateField()
    date_out = serializers.DateField()
    assigned_nurse = serializers.UUIDField(required=False)
    
    def validate_room(self, value):
        try:
            room = Room.objects.get(id=value, deleted_at__isnull=True)
            return room
        except Room.DoesNotExist:
            raise serializers.ValidationError("Room not found.")
    
    def validate_assigned_nurse(self, value):
        if value:
            try:
                nurse = Nurse.objects.get(user__id=value, user__deleted_at__isnull=True)
                return nurse
            except Nurse.DoesNotExist:
                raise serializers.ValidationError("Nurse not found.")
        return None
    
    def validate(self, attrs):
        room = attrs.get('room')
        date_in = attrs.get('date_in')
        date_out = attrs.get('date_out')
        
        # Date validation
        if date_out <= date_in:
            raise serializers.ValidationError("Date out must be after date in.")
        
        # Check if reservation can be updated (before date_in)
        if date_in <= timezone.now().date():
            raise serializers.ValidationError("Cannot update reservation on or after date in.")
        
        # Check room availability (excluding current reservation)
        if room and room.get_available_capacity(date_in, date_out) <= 0:
            # Check if the current reservation is the only one
            current_reservations = Reservation.objects.filter(
                room=room,
                date_in__lte=date_out,
                date_out__gte=date_in,
                deleted_at__isnull=True
            ).exclude(pk=self.instance.pk).count()
            
            if current_reservations >= room.max_capacity:
                raise serializers.ValidationError("Room is not available for the selected dates.")
        
        return attrs
    
    def update(self, instance, validated_data):
        instance.room = validated_data['room']
        instance.date_in = validated_data['date_in']
        instance.date_out = validated_data['date_out']
        
        if validated_data.get('assigned_nurse'):
            instance.assigned_nurse = validated_data['assigned_nurse']
        
        # Recalculate total fee
        instance.total_fee = instance.calculate_total_fee()
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            instance.updated_by = request.user.username
        
        instance.save()
        return instance

class UpdateReservationFacilitiesSerializer(serializers.Serializer):
    facilities = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    
    def validate_facilities(self, value):
        facilities = []
        for facility_id in value:
            try:
                facility = Facility.objects.get(id=facility_id, deleted_at__isnull=True)
                facilities.append(facility)
            except Facility.DoesNotExist:
                raise serializers.ValidationError(f"Facility with ID {facility_id} not found.")
        
        # Check for duplicates
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Duplicate facilities are not allowed.")
        
        return facilities
    
    def validate(self, attrs):
        # Check if reservation can be updated (before date_out)
        if self.instance.date_out <= timezone.now().date():
            raise serializers.ValidationError("Cannot update facilities on or after date out.")
        
        return attrs
    
    def update(self, instance, validated_data):
        # Remove existing facilities
        instance.reservationfacility_set.all().delete()
        
        # Add new facilities
        for facility in validated_data.get('facilities', []):
            ReservationFacility.objects.create(
                reservation=instance,
                facility=facility
            )
        
        # Recalculate total fee
        instance.total_fee = instance.calculate_total_fee()
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            instance.updated_by = request.user.username
        
        instance.save()
        return instance