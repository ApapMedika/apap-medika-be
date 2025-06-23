from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Medicine, Prescription, MedicineQuantity
from .serializers import (
    MedicineSerializer, PrescriptionSerializer, CreatePrescriptionSerializer,
    UpdatePrescriptionSerializer, ProcessPrescriptionSerializer, MedicineRestockSerializer
)
from common.permissions import (
    IsAdminUser, IsPharmacistUser, IsDoctorUser, IsAdminOrPharmacistUser,
    IsAdminOrDoctorUser, IsPatientUser
)
from common.utils import soft_delete_object

# ==================== MEDICINE VIEWS ====================

class MedicineListView(generics.ListCreateAPIView):
    """
    List all medicines or create new medicine
    """
    serializer_class = MedicineSerializer
    permission_classes = [IsAdminOrPharmacistUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'id']
    ordering_fields = ['id', 'name', 'price', 'stock', 'created_at']
    ordering = ['id']
    
    def get_queryset(self):
        return Medicine.objects.filter(deleted_at__isnull=True)

class MedicineDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete medicine details
    """
    serializer_class = MedicineSerializer
    permission_classes = [IsAdminOrPharmacistUser]
    
    def get_queryset(self):
        return Medicine.objects.filter(deleted_at__isnull=True)
    
    def perform_destroy(self, instance):
        # Check if medicine is used in any active prescriptions
        active_prescriptions = Prescription.objects.filter(
            medicinequantity__medicine=instance,
            status__in=[0, 1],  # Created or Waiting for stock
            deleted_at__isnull=True
        ).exists()
        
        if active_prescriptions:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot delete medicine that is used in active prescriptions.")
        
        # Soft delete
        soft_delete_object(instance, self.request.user)

class MedicineStockUpdateView(APIView):
    """
    Update medicine stock (add to existing stock)
    """
    permission_classes = [IsAdminOrPharmacistUser]
    
    def put(self, request, pk):
        try:
            medicine = Medicine.objects.get(pk=pk, deleted_at__isnull=True)
        except Medicine.DoesNotExist:
            return Response({'error': 'Medicine not found'}, status=status.HTTP_404_NOT_FOUND)
        
        stock = request.data.get('stock')
        
        if not stock:
            return Response({'error': 'Stock amount is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            stock = int(stock)
        except ValueError:
            return Response({'error': 'Stock must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        if stock <= 0:
            return Response({'error': 'Stock must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add to existing stock
        medicine.stock += stock
        medicine.updated_by = request.user.username
        medicine.save()
        
        return Response({
            'message': f'Successfully added {stock} units to {medicine.name}',
            'medicine': MedicineSerializer(medicine).data
        }, status=status.HTTP_200_OK)

class RestockMedicinesView(APIView):
    """
    Restock multiple medicines at once
    """
    permission_classes = [IsAdminOrPharmacistUser]
    
    def post(self, request):
        serializer = MedicineRestockSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': 'Medicines restocked successfully',
                'result': result
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== PRESCRIPTION VIEWS ====================

class PrescriptionListView(generics.ListCreateAPIView):
    """
    List all prescriptions or create new prescription
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['id', 'patient__user__name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreatePrescriptionSerializer
        return PrescriptionSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminOrDoctorUser()]
        return [IsAdminOrPharmacistUser()]
    
    def get_queryset(self):
        queryset = Prescription.objects.filter(deleted_at__isnull=True)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter is not None:
            try:
                status_int = int(status_filter)
                queryset = queryset.filter(status=status_int)
            except ValueError:
                pass
        
        return queryset

class PrescriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete prescription details
    """
    permission_classes = [IsAdminOrPharmacistUser]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdatePrescriptionSerializer
        return PrescriptionSerializer
    
    def get_queryset(self):
        return Prescription.objects.filter(deleted_at__isnull=True)
    
    def perform_destroy(self, instance):
        # Check if prescription can be cancelled
        if instance.status not in [0, 1]:  # Created or Waiting for stock
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Prescription can only be cancelled if status is Created or Waiting for Stock.")
        
        # Return stock if prescription was waiting for stock
        if instance.status == 1:
            for medicine_quantity in instance.medicinequantity_set.all():
                medicine = medicine_quantity.medicine
                medicine.stock += medicine_quantity.fulfilled_quantity
                medicine.save()
        
        # Update status to cancelled
        instance.status = 3
        instance.updated_by = self.request.user.username
        instance.save()

class ProcessPrescriptionView(APIView):
    """
    Process prescription (mark as done)
    """
    permission_classes = [IsAdminOrPharmacistUser]
    
    def post(self, request, pk):
        try:
            prescription = Prescription.objects.get(pk=pk, deleted_at__isnull=True)
        except Prescription.DoesNotExist:
            return Response({'error': 'Prescription not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if prescription.status not in [0, 1]:  # Can only process Created or Waiting for stock
            return Response(
                {'error': 'Prescription can only be processed if status is Created or Waiting for Stock'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ProcessPrescriptionSerializer(
            prescription, 
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            prescription = serializer.save()
            
            # Determine status message
            if prescription.status == 2:
                status_message = "Prescription completed successfully"
            else:
                status_message = "Prescription processed, waiting for stock"
            
            return Response({
                'message': status_message,
                'prescription': PrescriptionSerializer(prescription).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PrescriptionStatisticsView(APIView):
    """
    Get prescription statistics for medicine usage
    """
    permission_classes = [IsAdminOrPharmacistUser]
    
    def get(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        
        if not month or not year:
            return Response(
                {'error': 'Month and year parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            month = int(month)
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'Month and year must be integers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get medicine usage statistics for the specified month/year
        medicine_stats = MedicineQuantity.objects.filter(
            prescription__created_at__month=month,
            prescription__created_at__year=year,
            prescription__status=2,  # Only done prescriptions
            prescription__deleted_at__isnull=True
        ).values(
            'medicine__id',
            'medicine__name'
        ).annotate(
            total_quantity=Sum('fulfilled_quantity')
        ).order_by('-total_quantity')[:10]  # Top 10 most used medicines
        
        return Response({
            'month': month,
            'year': year,
            'statistics': list(medicine_stats)
        }, status=status.HTTP_200_OK)

# ==================== DOCTOR-SPECIFIC VIEWS ====================

class DoctorPrescriptionListView(generics.ListAPIView):
    """
    List prescriptions for doctor (from their appointments)
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAdminOrDoctorUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'patient__user__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Prescription.objects.filter(deleted_at__isnull=True)
        
        # If doctor, filter by their appointments
        if self.request.user.role == 'DOCTOR':
            queryset = queryset.filter(appointment__doctor=self.request.user.doctor)
        
        return queryset

class DoctorPrescriptionDetailView(generics.RetrieveAPIView):
    """
    Get prescription details for doctor
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAdminOrDoctorUser]
    
    def get_queryset(self):
        queryset = Prescription.objects.filter(deleted_at__isnull=True)
        
        # If doctor, filter by their appointments
        if self.request.user.role == 'DOCTOR':
            queryset = queryset.filter(appointment__doctor=self.request.user.doctor)
        
        return queryset

# ==================== PATIENT-SPECIFIC VIEWS ====================

class PatientPrescriptionListView(generics.ListAPIView):
    """
    List prescriptions for patient
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [IsPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Prescription.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )

class PatientPrescriptionDetailView(generics.RetrieveAPIView):
    """
    Get prescription details for patient
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [IsPatientUser]
    
    def get_queryset(self):
        return Prescription.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )