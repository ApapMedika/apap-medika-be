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
    # Prescription data
    appointment_id = serializers.CharField()  # Required for PBI-BE-P6
    medicines = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        min_length=1  # Required for PBI-BE-P6
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
            
            # PBI-BE-P6: Create Prescription fails if >=1 quantity of medicine requested <=0
            if quantity <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")
            
            try:
                Medicine.objects.get(id=medicine_id)
            except Medicine.DoesNotExist:
                raise serializers.ValidationError(f"Medicine with ID {medicine_id} does not exist.")
            
            # PBI-BE-P6: If there are two or more drugs that are the same, then the requested quantity is added up
            medicine_totals[medicine_id] += quantity
        
        return medicine_totals
    
    def create(self, validated_data):
        from appointment.models import Appointment
        
        # Get appointment and patient
        try:
            appointment = Appointment.objects.get(id=validated_data['appointment_id'])
            patient = appointment.patient
        except Appointment.DoesNotExist:
            raise serializers.ValidationError("Appointment not found.")
        
        # Generate prescription ID
        medicine_count = len(validated_data['medicines'])
        now = timezone.now()
        prescription_id = get_prescription_code(medicine_count, now.weekday(), now.strftime('%H%M%S'))
        
        # Create prescription
        prescription_data = {
            'id': prescription_id,
            'patient': patient,
            'appointment': appointment,
            'status': 0,  # Created
        }
        
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