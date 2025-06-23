from rest_framework import serializers
from .models import Bill, BillCoveredTreatment
from profiles.models import Patient
from appointment.models import Appointment
from pharmacy.models import Prescription
from hospitalization.models import Reservation
from insurance.models import Policy

class BillCoveredTreatmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillCoveredTreatment
        fields = ['id', 'treatment_name', 'treatment_price', 'coverage_amount']

class BillSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    patient_nik = serializers.CharField(source='patient.nik', read_only=True)
    appointment_id = serializers.CharField(source='appointment.id', read_only=True)
    prescription_id = serializers.CharField(source='prescription.id', read_only=True)
    reservation_id = serializers.CharField(source='reservation.id', read_only=True)
    policy_id = serializers.CharField(source='policy.id', read_only=True)
    policy_name = serializers.CharField(source='policy.company.name', read_only=True)
    
    # Coverage details if policy is applied
    coverage_discount = serializers.SerializerMethodField()
    covered_treatments = BillCoveredTreatmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Bill
        fields = ['id', 'patient', 'patient_name', 'patient_nik', 'appointment', 'appointment_id',
                 'prescription', 'prescription_id', 'reservation', 'reservation_id', 'policy', 'policy_id', 'policy_name',
                 'appointment_total_fee', 'prescription_total_price', 'reservation_total_fee', 
                 'subtotal', 'coverage_discount', 'total_amount_due', 'status', 'covered_treatments',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'subtotal', 'total_amount_due', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_coverage_discount(self, obj):
        return obj.calculate_coverage_discount()

class CreateBillSerializer(serializers.Serializer):
    appointment_id = serializers.CharField(required=False)
    reservation_id = serializers.CharField(required=False)
    
    def validate(self, attrs):
        # Either appointment_id or reservation_id must be provided
        if not attrs.get('appointment_id') and not attrs.get('reservation_id'):
            raise serializers.ValidationError("Either appointment_id or reservation_id must be provided.")
        
        # Both cannot be provided at the same time
        if attrs.get('appointment_id') and attrs.get('reservation_id'):
            raise serializers.ValidationError("Cannot provide both appointment_id and reservation_id.")
        
        # Validate appointment exists
        if attrs.get('appointment_id'):
            try:
                appointment = Appointment.objects.get(id=attrs['appointment_id'], deleted_at__isnull=True)
                attrs['appointment'] = appointment
                attrs['patient'] = appointment.patient
            except Appointment.DoesNotExist:
                raise serializers.ValidationError("Appointment not found.")
        
        # Validate reservation exists
        if attrs.get('reservation_id'):
            try:
                reservation = Reservation.objects.get(id=attrs['reservation_id'], deleted_at__isnull=True)
                attrs['reservation'] = reservation
                attrs['patient'] = reservation.patient
            except Reservation.DoesNotExist:
                raise serializers.ValidationError("Reservation not found.")
        
        return attrs
    
    def create(self, validated_data):
        patient = validated_data['patient']
        
        # Create bill data
        bill_data = {
            'patient': patient,
            'status': 'TREATMENT_IN_PROGRESS'
        }
        
        if validated_data.get('appointment'):
            bill_data['appointment'] = validated_data['appointment']
        
        if validated_data.get('reservation'):
            bill_data['reservation'] = validated_data['reservation']
        
        # Set user fields
        request = self.context.get('request')
        if request and request.user:
            bill_data['created_by'] = request.user.username
            bill_data['updated_by'] = request.user.username
        
        bill = Bill.objects.create(**bill_data)
        return bill

class UpdateBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ['policy']
    
    def validate_policy(self, value):
        if value:
            # Check if policy belongs to the same patient
            if value.patient != self.instance.patient:
                raise serializers.ValidationError("Policy does not belong to this patient.")
            
            # Check if policy is active
            if value.status not in [0, 1]:  # Created or Partially Claimed
                raise serializers.ValidationError("Policy is not active.")
            
            # Check if policy covers any treatments in the appointment
            if self.instance.appointment:
                covered_treatments = []
                for app_treatment in self.instance.appointment.appointmenttreatment_set.all():
                    treatment_name = app_treatment.treatment.name
                    
                    policy_coverage = value.policycoverage_set.filter(
                        coverage__name=treatment_name,
                        used=False
                    ).first()
                    
                    if policy_coverage:
                        covered_treatments.append(treatment_name)
                
                if not covered_treatments:
                    raise serializers.ValidationError(
                        "Selected policy does not cover any treatments in this appointment."
                    )
        
        return value
    
    def update(self, instance, validated_data):
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            validated_data['updated_by'] = request.user.username
        
        # Update policy and recalculate amounts
        instance = super().update(instance, validated_data)
        
        # Update bill status and amounts
        instance.update_status()
        
        # If policy is applied, create covered treatment records
        if instance.policy and instance.appointment:
            # Clear existing covered treatments
            instance.covered_treatments.all().delete()
            
            # Create new covered treatment records
            for app_treatment in instance.appointment.appointmenttreatment_set.all():
                treatment_name = app_treatment.treatment.name
                
                policy_coverage = instance.policy.policycoverage_set.filter(
                    coverage__name=treatment_name,
                    used=False
                ).first()
                
                if policy_coverage:
                    coverage_amount = min(app_treatment.treatment.price, policy_coverage.coverage_amount)
                    BillCoveredTreatment.objects.create(
                        bill=instance,
                        treatment_name=treatment_name,
                        treatment_price=app_treatment.treatment.price,
                        coverage_amount=coverage_amount
                    )
        
        return instance

class PayBillSerializer(serializers.Serializer):
    bill_id = serializers.UUIDField()
    payment_method = serializers.CharField(max_length=50)
    
    def validate_bill_id(self, value):
        try:
            bill = Bill.objects.get(id=value, deleted_at__isnull=True)
            if bill.status != 'UNPAID':
                raise serializers.ValidationError("Bill is not in unpaid status.")
            return bill
        except Bill.DoesNotExist:
            raise serializers.ValidationError("Bill not found.")
    
    def validate_payment_method(self, value):
        valid_methods = ['CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'INSURANCE']
        if value.upper() not in valid_methods:
            raise serializers.ValidationError(f"Invalid payment method. Valid options: {', '.join(valid_methods)}")
        return value.upper()
    
    def create(self, validated_data):
        bill = validated_data['bill_id']
        payment_method = validated_data['payment_method']
        
        # Process payment
        bill.pay()
        
        # Set updated_by field
        request = self.context.get('request')
        if request and request.user:
            bill.updated_by = request.user.username
            bill.save()
        
        return {
            'bill': bill,
            'payment_method': payment_method,
            'message': f'Payment processed successfully via {payment_method}'
        }

class BillSummarySerializer(serializers.Serializer):
    """
    Serializer for bill summary/dashboard data
    """
    total_bills = serializers.IntegerField()
    unpaid_bills = serializers.IntegerField()
    paid_bills = serializers.IntegerField()
    total_amount_unpaid = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount_paid = serializers.DecimalField(max_digits=15, decimal_places=2)

class UpdateBillComponentsSerializer(serializers.Serializer):
    """
    Serializer for updating all bill components and statuses
    """
    updated_bills = serializers.IntegerField()
    
    def create(self, validated_data):
        """
        Update all bill components and statuses
        """
        updated_count = 0
        
        # Get all bills that might need updates
        bills = Bill.objects.filter(
            status__in=['TREATMENT_IN_PROGRESS', 'UNPAID'],
            deleted_at__isnull=True
        )
        
        for bill in bills:
            old_status = bill.status
            
            # Update appointment total fee
            if bill.appointment and bill.appointment.status == 1:  # Done
                bill.appointment_total_fee = bill.appointment.total_fee
            
            # Update prescription total price
            if bill.prescription and bill.prescription.status == 2:  # Done
                bill.prescription_total_price = bill.prescription.total_price
            
            # Update reservation total fee
            if bill.reservation:
                bill.reservation_total_fee = bill.reservation.total_fee
            
            # Update bill status
            bill.update_status()
            
            if bill.status != old_status or bill.subtotal != bill.calculate_subtotal():
                bill.save()
                updated_count += 1
        
        return {'updated_bills': updated_count}

class BillDetailSerializer(serializers.ModelSerializer):
    """
    Detailed bill serializer with all related information
    """
    patient_name = serializers.CharField(source='patient.user.name', read_only=True)
    patient_nik = serializers.CharField(source='patient.nik', read_only=True)
    
    # Related object details
    appointment_details = serializers.SerializerMethodField()
    prescription_details = serializers.SerializerMethodField()
    reservation_details = serializers.SerializerMethodField()
    policy_details = serializers.SerializerMethodField()
    
    # Coverage details
    coverage_discount = serializers.SerializerMethodField()
    covered_treatments = BillCoveredTreatmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Bill
        fields = ['id', 'patient', 'patient_name', 'patient_nik', 
                 'appointment', 'appointment_details', 'appointment_total_fee',
                 'prescription', 'prescription_details', 'prescription_total_price',
                 'reservation', 'reservation_details', 'reservation_total_fee',
                 'policy', 'policy_details', 'subtotal', 'coverage_discount', 'total_amount_due',
                 'status', 'covered_treatments',
                 'created_at', 'updated_at', 'created_by', 'updated_by']
        read_only_fields = ['id', 'subtotal', 'total_amount_due', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_appointment_details(self, obj):
        if obj.appointment:
            from appointment.serializers import AppointmentSerializer
            return AppointmentSerializer(obj.appointment).data
        return None
    
    def get_prescription_details(self, obj):
        if obj.prescription:
            from pharmacy.serializers import PrescriptionSerializer
            return PrescriptionSerializer(obj.prescription).data
        return None
    
    def get_reservation_details(self, obj):
        if obj.reservation:
            from hospitalization.serializers import ReservationSerializer
            return ReservationSerializer(obj.reservation).data
        return None
    
    def get_policy_details(self, obj):
        if obj.policy:
            from insurance.serializers import PolicySerializer
            return PolicySerializer(obj.policy).data
        return None
    
    def get_coverage_discount(self, obj):
        return obj.calculate_coverage_discount()