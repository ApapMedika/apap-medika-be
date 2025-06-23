from rest_framework import serializers
from django.utils import timezone
from collections import defaultdict
from .models import Medicine, Prescription, MedicineQuantity
from profiles.models import Patient, Pharmacist, EndUser
from common.utils import get_medicine_code, get_prescription_code, update_user_fields

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ['id', 'name', 'price', 'stock', 'description', 
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Generate medicine ID
        medicine_count = Medicine.objects.count()
        medicine_id = get_medicine_code(medicine_count + 1)
        validated_data['id'] = medicine_id
        
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

class MedicineQuantitySerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_price = serializers.DecimalField(source='medicine.price', max_digits=10, decimal_places=2, read_only=True)
    remaining_quantity = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    
    class Meta:
        model = MedicineQuantity
        fields = ['id', 'medicine', 'medicine_name', 'medicine_price', 'quantity', 
                 'fulfilled_quantity', 'remaining_quantity', 'total_price']

class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display_custom', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.user.name', read_only=True)
    medicines = MedicineQuantitySerializer(source='medicinequantity_set', many=True, read_only=True)
    
    class Meta:
        model = Prescription
        fields = ['id', 'patient', 'patient_name', 'appointment', 'status', 'status_display',
                 'total_price', 'processed_by', 'processed_by_name', 'medicines',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'total_price', 'created_at', 'updated_at']

class CreatePrescriptionSerializer(serializers.Serializer):
    # Patient data (for new patient creation)
    patient_id = serializers.UUIDField(required=False)
    patient_name = serializers.CharField(required=False)
    patient_nik = serializers.CharField(max_length=16, required=False)
    patient_email = serializers.EmailField(required=False)
    patient_gender = serializers.BooleanField(required=False)
    patient_birth_place = serializers.CharField(required=False)
    patient_birth_date = serializers.DateField(required=False)
    patient_class = serializers.IntegerField(required=False)
    
    # Prescription data
    appointment_id = serializers.CharField(required=False)
    medicines = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        min_length=1
    )
    
    def validate_medicines(self, value):
        """
        Validate medicines list
        """
        medicine_ids = []
        
        for med_data in value:
            medicine_id = med_data.get('medicine_id')
            quantity = med_data.get('quantity')
            
            if not medicine_id:
                raise serializers.ValidationError("Medicine ID is required.")
            
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Quantity must be a valid integer.")
            
            if quantity <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")
            
            try:
                Medicine.objects.get(id=medicine_id)
            except Medicine.DoesNotExist:
                raise serializers.ValidationError(f"Medicine with ID {medicine_id} does not exist.")
            
            medicine_ids.append(medicine_id)
        
        # Check for duplicate medicines and sum quantities
        medicine_totals = defaultdict(int)
        for med_data in value:
            medicine_totals[med_data['medicine_id']] += int(med_data['quantity'])
        
        return medicine_totals
    
    def create(self, validated_data):
        from profiles.models import EndUser, Patient
        from django.contrib.auth.hashers import make_password
        
        # Get or create patient
        patient = None
        if validated_data.get('patient_id'):
            try:
                patient = Patient.objects.get(user__id=validated_data['patient_id'])
            except Patient.DoesNotExist:
                raise serializers.ValidationError("Patient not found.")
        elif validated_data.get('appointment_id'):
            try:
                from appointment.models import Appointment
                appointment = Appointment.objects.get(id=validated_data['appointment_id'])
                patient = appointment.patient
            except:
                raise serializers.ValidationError("Appointment not found.")
        else:
            # Create new patient
            user_data = {
                'name': validated_data['patient_name'],
                'username': validated_data['patient_nik'],
                'email': validated_data['patient_email'],
                'gender': validated_data['patient_gender'],
                'role': 'PATIENT',
                'password': make_password('defaultpassword123')  # Default password
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
        
        # Generate prescription ID
        medicine_count = len(validated_data['medicines'])
        now = timezone.now()
        prescription_id = get_prescription_code(medicine_count, now.weekday(), now.strftime('%H:%M:%S'))
        
        # Create prescription
        prescription_data = {
            'id': prescription_id,
            'patient': patient,
            'status': 0,  # Created
        }
        
        if validated_data.get('appointment_id'):
            try:
                from appointment.models import Appointment
                appointment = Appointment.objects.get(id=validated_data['appointment_id'])
                prescription_data['appointment'] = appointment
            except:
                pass
        
        # Set user fields
        request = self.context.get('request')
        if request and request.user:
            prescription_data['created_by'] = request.user.username
            prescription_data['updated_by'] = request.user.username
        
        prescription = Prescription.objects.create(**prescription_data)
        
        # Create medicine quantities
        total_price = 0
        for medicine_id, quantity in validated_data['medicines'].items():
            medicine = Medicine.objects.get(id=medicine_id)
            MedicineQuantity.objects.create(
                medicine=medicine,
                prescription=prescription,
                quantity=quantity
            )
            total_price += medicine.price * quantity
        
        prescription.total_price = total_price
        prescription.save()
        
        return prescription

class UpdatePrescriptionSerializer(serializers.Serializer):
    medicines = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        min_length=1
    )
    
    def validate_medicines(self, value):
        """
        Validate medicines list
        """
        medicine_totals = defaultdict(int)
        
        for med_data in value:
            medicine_id = med_data.get('medicine_id')
            quantity = med_data.get('quantity')
            
            if not medicine_id:
                raise serializers.ValidationError("Medicine ID is required.")
            
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Quantity must be a valid integer.")
            
            if quantity <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")
            
            try:
                Medicine.objects.get(id=medicine_id)
            except Medicine.DoesNotExist:
                raise serializers.ValidationError(f"Medicine with ID {medicine_id} does not exist.")
            
            medicine_totals[medicine_id] += quantity
        
        return medicine_totals
    
    def update(self, instance, validated_data):
        # Check if prescription can be updated
        if instance.status != 0:  # Only created prescriptions can be updated
            raise serializers.ValidationError("Prescription can only be updated if status is Created.")
        
        # Delete existing medicine quantities
        instance.medicinequantity_set.all().delete()
        
        # Create new medicine quantities
        total_price = 0
        for medicine_id, quantity in validated_data['medicines'].items():
            medicine = Medicine.objects.get(id=medicine_id)
            MedicineQuantity.objects.create(
                medicine=medicine,
                prescription=instance,
                quantity=quantity
            )
            total_price += medicine.price * quantity
        
        instance.total_price = total_price
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            instance.updated_by = request.user.username
        
        instance.save()
        return instance

class ProcessPrescriptionSerializer(serializers.Serializer):
    processed_by = serializers.CharField()
    
    def validate_processed_by(self, value):
        try:
            pharmacist = Pharmacist.objects.get(user__username=value)
            return pharmacist
        except Pharmacist.DoesNotExist:
            raise serializers.ValidationError("Pharmacist not found.")
    
    def update(self, instance, validated_data):
        # Process prescription
        instance.processed_by = validated_data['processed_by']
        
        # Check stock and fulfill quantities
        all_fulfilled = True
        
        for medicine_quantity in instance.medicinequantity_set.all():
            medicine = medicine_quantity.medicine
            remaining_quantity = medicine_quantity.remaining_quantity
            
            if medicine.stock >= remaining_quantity:
                # Fulfill completely
                medicine.stock -= remaining_quantity
                medicine_quantity.fulfilled_quantity += remaining_quantity
            else:
                # Fulfill partially
                medicine_quantity.fulfilled_quantity += medicine.stock
                medicine.stock = 0
                all_fulfilled = False
            
            medicine.save()
            medicine_quantity.save()
        
        # Update prescription status
        if all_fulfilled:
            instance.status = 2  # Done
        else:
            instance.status = 1  # Waiting for stock
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            instance.updated_by = request.user.username
        
        instance.save()
        return instance

class MedicineRestockSerializer(serializers.Serializer):
    medicines = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        min_length=1
    )
    
    def validate_medicines(self, value):
        """
        Validate medicine restock data
        """
        medicine_totals = defaultdict(int)
        
        for med_data in value:
            medicine_id = med_data.get('medicine_id')
            quantity = med_data.get('quantity')
            
            if not medicine_id:
                raise serializers.ValidationError("Medicine ID is required.")
            
            try:
                quantity = int(quantity)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Quantity must be a valid integer.")
            
            if quantity <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")
            
            try:
                Medicine.objects.get(id=medicine_id)
            except Medicine.DoesNotExist:
                raise serializers.ValidationError(f"Medicine with ID {medicine_id} does not exist.")
            
            medicine_totals[medicine_id] += quantity
        
        return medicine_totals
    
    def create(self, validated_data):
        """
        Restock medicines
        """
        restocked_medicines = []
        
        for medicine_id, quantity in validated_data['medicines'].items():
            medicine = Medicine.objects.get(id=medicine_id)
            medicine.stock += quantity
            
            # Set updated_by field
            request = self.context.get('request')
            if request and request.user:
                medicine.updated_by = request.user.username
            
            medicine.save()
            restocked_medicines.append({
                'medicine_id': medicine_id,
                'medicine_name': medicine.name,
                'added_quantity': quantity,
                'new_stock': medicine.stock
            })
        
        return {'restocked_medicines': restocked_medicines}