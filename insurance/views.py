from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from datetime import date
from django.db.models import Sum

from .models import Coverage, Company, Policy, PolicyCoverage
from .serializers import (
    CoverageSerializer, CompanySerializer, CreateCompanySerializer,
    UpdateCompanySerializer, PolicySerializer, CreatePolicySerializer,
    UpdatePolicySerializer, PolicyForTreatmentsSerializer
)
from common.permissions import IsAdminUser, IsPatientUser, IsAdminOrPatientUser
from common.utils import soft_delete_object

# ==================== COVERAGE VIEWS ====================

class CoverageListView(generics.ListAPIView):
    """
    List all coverages
    """
    queryset = Coverage.objects.all()
    serializer_class = CoverageSerializer
    permission_classes = [permissions.IsAuthenticated]

# ==================== COMPANY VIEWS ====================

class CompanyListView(generics.ListCreateAPIView):
    """
    List all companies or create new company
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateCompanySerializer
        return CompanySerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        return Company.objects.filter(deleted_at__isnull=True)

class CompanyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete company details
    """
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdateCompanySerializer
        return CompanySerializer
    
    def get_queryset(self):
        return Company.objects.filter(deleted_at__isnull=True)
    
    def perform_destroy(self, instance):
        # Check if company has active policies
        active_policies = Policy.objects.filter(
            company=instance,
            status__in=[0, 1, 2],  # Created, Partially Claimed, Fully Claimed
            deleted_at__isnull=True
        ).exists()
        
        if active_policies:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot delete company with active policies.")
        
        # Soft delete
        soft_delete_object(instance, self.request.user)

# ==================== POLICY VIEWS ====================

class PolicyListView(generics.ListCreateAPIView):
    """
    GET All Policy (PBI-BE-I1)
    Displays all policies registered in the system (Admin)
    Displays all policies owned by patients registered in the system (Patient)
    Policy data displayed includes policies with the status "Expired" or "Cancelled", 
    but does not include policies that have been deleted (Admin, Patient)
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['id', 'patient__user__name', 'company__name']
    ordering_fields = ['id', 'created_at', 'expiry_date', 'total_coverage']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreatePolicySerializer
        return PolicySerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]  # PBI-BE-I5: POST Create Policy (Admin)
        return [IsAdminOrPatientUser()]  # PBI-BE-I1: GET All Policy (Admin, Patient)
    
    def get_queryset(self):
        # PBI-BE-I1: Policy data displayed includes policies with the status "Expired" or "Cancelled", 
        # but does not include policies that have been deleted
        queryset = Policy.objects.filter(deleted_at__isnull=True)
        
        # Update expired policies first (PBI-BE-I7)
        self.update_expired_policies()
        
        # Role-based filtering
        if self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        # Status filtering (PBI-BE-I2)
        status_filter = self.request.query_params.get('status')
        if status_filter is not None:
            try:
                status_int = int(status_filter)
                queryset = queryset.filter(status=status_int)
            except ValueError:
                pass
        
        # Coverage range filtering (PBI-BE-I3)
        min_coverage = self.request.query_params.get('minCoverage')
        max_coverage = self.request.query_params.get('maxCoverage')
        
        if min_coverage:
            try:
                min_coverage = float(min_coverage)
                queryset = queryset.filter(total_coverage__gte=min_coverage)
            except ValueError:
                pass
        
        if max_coverage:
            try:
                max_coverage = float(max_coverage)
                queryset = queryset.filter(total_coverage__lte=max_coverage)
            except ValueError:
                pass
        
        return queryset
    
    def update_expired_policies(self):
        """
        Update expired policies (PBI-BE-I7)
        """
        expired_policies = Policy.objects.filter(
            expiry_date__lt=date.today(),
            status__in=[0, 1],  # Only update Created or Partially Claimed
            deleted_at__isnull=True
        )
        for policy in expired_policies:
            policy.status = 3  # Expired
            policy.save()

class PolicyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET Detail Policy by Policy ID (PBI-BE-I4)
    Displays policy details with a specific ID (Admin)
    Displays policy details with a specific patient ID (Patient)
    
    PUT Update Policy Expiry Date (PBI-BE-I6)
    Expiry date of policy with specific ID successfully updated
    
    DELETE Delete Policy (PBI-BE-I9)
    Policy with specified ID successfully deleted using soft delete mechanism
    """
    permission_classes = [IsAdminOrPatientUser]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdatePolicySerializer
        return PolicySerializer
    
    def get_queryset(self):
        queryset = Policy.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering
        if self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        return queryset
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]  # Only admin can update/delete
        return [IsAdminOrPatientUser()]  # Both admin and patient can view
    
    def perform_destroy(self, instance):
        # PBI-BE-I9: Delete policy (soft delete)
        if instance.status != 0:  # Only created policies can be deleted
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Only policies with 'Created' status can be deleted.")
        
        # Increase patient's available limit
        if hasattr(instance.patient, 'increase_available_limit'):
            instance.patient.increase_available_limit(instance.total_coverage)
        
        # Soft delete
        soft_delete_object(instance, self.request.user)

class PolicyListByStatusView(generics.ListAPIView):
    """
    GET Policy List by Policy Status (PBI-BE-I2)
    Displays all policies registered in the system based on a certain status (Admin)
    Displays all policies owned by patients registered in the system based on a certain status (Patient)
    Policy data displayed does not include policies that have been deleted (Admin, Patient)
    """
    serializer_class = PolicySerializer
    permission_classes = [IsAdminOrPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'patient__user__name', 'company__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        status_param = self.kwargs.get('status')
        
        # Policy data displayed does not include policies that have been deleted
        queryset = Policy.objects.filter(deleted_at__isnull=True)
        
        # Update expired policies first
        self.update_expired_policies()
        
        # Role-based filtering
        if self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        # Status filtering
        if status_param is not None:
            try:
                status_int = int(status_param)
                queryset = queryset.filter(status=status_int)
            except ValueError:
                pass
        
        return queryset
    
    def update_expired_policies(self):
        """Update expired policies"""
        expired_policies = Policy.objects.filter(
            expiry_date__lt=date.today(),
            status__in=[0, 1],
            deleted_at__isnull=True
        )
        for policy in expired_policies:
            policy.status = 3
            policy.save()

class PolicyListByCoverageRangeView(generics.ListAPIView):
    """
    GET Policy List by Policy Total Coverage Range (PBI-BE-I3)
    Displays all policies that have total coverage with a certain range from 'minCoverage' to 'maxCoverage' inclusively (Admin)
    Displays all policies owned by patients that have total coverage with a certain range from 'minCoverage' to 'maxCoverage' inclusively (Patient)
    Policy data displayed does not include policies that have been deleted (Admin, Patient)
    """
    serializer_class = PolicySerializer
    permission_classes = [IsAdminOrPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'patient__user__name', 'company__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        min_coverage = self.request.query_params.get('minCoverage')
        max_coverage = self.request.query_params.get('maxCoverage')
        
        # Policy data displayed does not include policies that have been deleted
        queryset = Policy.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering
        if self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        # Coverage range filtering
        if min_coverage:
            try:
                min_coverage = float(min_coverage)
                queryset = queryset.filter(total_coverage__gte=min_coverage)
            except ValueError:
                pass
        
        if max_coverage:
            try:
                max_coverage = float(max_coverage)
                queryset = queryset.filter(total_coverage__lte=max_coverage)
            except ValueError:
                pass
        
        return queryset

class UpdatePolicyStatusView(APIView):
    """
    PUT Update Policy Status (PBI-BE-I7)
    Status of policy whose total covered > Rp0 automatically updated to status = 1 (Partially Claimed)
    Status of policy whose total covered == total coverage automatically updated to status = 2 (Fully Claimed)
    Status of policy whose expiry date is less than today's date automatically updated to status = 3 (Expired)
    """
    permission_classes = [IsAdminUser]
    
    def put(self, request, pk):
        try:
            policy = Policy.objects.get(pk=pk, deleted_at__isnull=True)
        except Policy.DoesNotExist:
            return Response({'error': 'Policy not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Update policy status based on business logic
        old_status = policy.status
        
        # Check if expired
        if policy.expiry_date < date.today() and policy.status not in [2, 4]:
            policy.status = 3  # Expired
        # Check if fully claimed
        elif policy.total_covered >= policy.total_coverage and policy.status != 4:
            policy.status = 2  # Fully Claimed
        # Check if partially claimed
        elif policy.total_covered > 0 and policy.status not in [2, 3, 4]:
            policy.status = 1  # Partially Claimed
        
        policy.updated_by = request.user.username
        policy.save()
        
        return Response({
            'message': f'Policy {policy.id} status updated from {old_status} to {policy.status}',
            'old_status': old_status,
            'new_status': policy.status,
            'policy': PolicySerializer(policy).data
        }, status=status.HTTP_200_OK)

class CancelPolicyView(APIView):
    """
    PUT Cancel Policy (PBI-BE-I8)
    Policy with specified ID successfully canceled and its status changed to status = 4 (Cancelled)
    Policy whose status is not "Created" (status = 0) cannot be canceled
    Patient's available limit increased by the total coverage of the canceled policy
    """
    permission_classes = [IsAdminUser]
    
    def put(self, request, pk):
        try:
            policy = Policy.objects.get(pk=pk, deleted_at__isnull=True)
        except Policy.DoesNotExist:
            return Response({'error': 'Policy not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if policy.status != 0:  # Only created policies can be cancelled
            return Response(
                {'error': 'Only policies with "Created" status can be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status to cancelled
        policy.status = 4
        policy.updated_by = request.user.username
        policy.save()
        
        # Increase patient's available limit
        if hasattr(policy.patient, 'increase_available_limit'):
            policy.patient.increase_available_limit(policy.total_coverage)
        
        return Response({
            'message': f'Policy {policy.id} has been cancelled',
            'policy': PolicySerializer(policy).data
        }, status=status.HTTP_200_OK)

class PolicyForTreatmentsView(APIView):
    """
    GET/POST Policy List by Appointment Treatments (PBI-BE-I10)
    Receives request in the form of list of treatments
    Returns response in the form of list of policies with coverage that matches the request
    Policies with coverage that has been used are not displayed
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """GET endpoint for policy list by treatments"""
        treatments = request.query_params.getlist('treatments')
        
        if not treatments:
            return Response(
                {'error': 'treatments parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get policies that have coverages for these treatments and are not used
        policies = Policy.objects.filter(
            policycoverage__coverage__name__in=treatments,
            policycoverage__used=False,
            status__in=[0, 1],  # Created or Partially Claimed
            expiry_date__gt=date.today(),
            deleted_at__isnull=True
        ).distinct()
        
        return Response({
            'treatments': treatments,
            'policies': PolicySerializer(policies, many=True).data
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """POST endpoint for policy list by treatments"""
        serializer = PolicyForTreatmentsSerializer(data=request.data)
        
        if serializer.is_valid():
            treatments = serializer.validated_data['treatments']
            
            # Get policies that have coverages for these treatments and are not used
            policies = Policy.objects.filter(
                policycoverage__coverage__name__in=treatments,
                policycoverage__used=False,
                status__in=[0, 1],  # Created or Partially Claimed
                expiry_date__gt=date.today(),
                deleted_at__isnull=True
            ).distinct()
            
            return Response({
                'treatments': treatments,
                'policies': PolicySerializer(policies, many=True).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== STATISTICS VIEWS ====================

class PolicyStatisticsView(APIView):
    """
    Get policy statistics
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Update expired policies first
        expired_policies = Policy.objects.filter(
            expiry_date__lt=date.today(),
            status__in=[0, 1],
            deleted_at__isnull=True
        )
        for policy in expired_policies:
            policy.status = 3
            policy.save()
        
        # Get statistics
        total_policies = Policy.objects.filter(deleted_at__isnull=True).count()
        active_policies = Policy.objects.filter(status__in=[0, 1], deleted_at__isnull=True).count()
        expired_policies = Policy.objects.filter(status=3, deleted_at__isnull=True).count()
        cancelled_policies = Policy.objects.filter(status=4, deleted_at__isnull=True).count()
        fully_claimed_policies = Policy.objects.filter(status=2, deleted_at__isnull=True).count()
        
        total_coverage = Policy.objects.filter(deleted_at__isnull=True).aggregate(
            total=Sum('total_coverage')
        )['total'] or 0
        
        total_covered = Policy.objects.filter(deleted_at__isnull=True).aggregate(
            total=Sum('total_covered')
        )['total'] or 0
        
        return Response({
            'total_policies': total_policies,
            'active_policies': active_policies,
            'expired_policies': expired_policies,
            'cancelled_policies': cancelled_policies,
            'fully_claimed_policies': fully_claimed_policies,
            'total_coverage': total_coverage,
            'total_covered': total_covered,
            'coverage_utilization': (total_covered / total_coverage * 100) if total_coverage > 0 else 0
        }, status=status.HTTP_200_OK)

# ==================== PATIENT-SPECIFIC VIEWS ====================

class PatientPolicyListView(generics.ListAPIView):
    """
    List policies for patient
    """
    serializer_class = PolicySerializer
    permission_classes = [IsPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'company__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Policy.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )

class PatientPolicyDetailView(generics.RetrieveAPIView):
    """
    Get policy details for patient
    """
    serializer_class = PolicySerializer
    permission_classes = [IsPatientUser]
    
    def get_queryset(self):
        return Policy.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )