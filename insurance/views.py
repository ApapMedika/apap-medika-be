from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from datetime import date

from .models import Coverage, Company, Policy, PolicyCoverage
from .serializers import (
    CoverageSerializer, CompanySerializer, CreateCompanySerializer,
    UpdateCompanySerializer, PolicySerializer, CreatePolicySerializer,
    UpdatePolicySerializer, PolicyForTreatmentsSerializer
)
from common.permissions import IsAdminUser, IsPatientUser
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
            return [IsAdminUser]
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
    List all policies or create new policy (PBI-BE-I1)
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
            return [IsAdminUser]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        queryset = Policy.objects.filter(deleted_at__isnull=True)
        
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
        
        # Update expired policies (PBI-BE-I7)
        # This could also be done with a periodic task
        expired_policies = queryset.filter(
            expiry_date__lt=date.today(),
            status__in=[0, 1]  # Only update Created or Partially Claimed
        )
        for policy in expired_policies:
            policy.status = 3  # Expired
            policy.save()
        
        return queryset

class PolicyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete policy details (PBI-BE-I4, PBI-BE-I6)
    """
    permission_classes = [permissions.IsAuthenticated]
    
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
            return [IsAdminUser]
        return [permissions.IsAuthenticated()]
    
    def perform_destroy(self, instance):
        # PBI-BE-I9: Delete policy (soft delete)
        if instance.status != 0:  # Only created policies can be deleted
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Only policies with 'Created' status can be deleted.")
        
        # Increase patient's available limit
        # This would need to be implemented in the patient upgrade class view
        
        # Soft delete
        soft_delete_object(instance, self.request.user)

class CancelPolicyView(APIView):
    """
    Cancel a policy (PBI-BE-I8)
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
        
        return Response({
            'message': f'Policy {policy.id} has been cancelled',
            'policy': PolicySerializer(policy).data
        }, status=status.HTTP_200_OK)

class PolicyForTreatmentsView(APIView):
    """
    Get policies that cover specific treatments (PBI-BE-I10)
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request):
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
            
            # Filter by patient if patient role
            if request.user.role == 'PATIENT':
                policies = policies.filter(patient=request.user.patient)
            
            return Response({
                'treatments': treatments,
                'policies': PolicySerializer(policies, many=True).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PolicyStatisticsView(APIView):
    """
    Get policy statistics
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        period = request.query_params.get('period', 'monthly')
        year = request.query_params.get('year')
        
        if not year:
            return Response(
                {'error': 'Year parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'Year must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if period == 'monthly':
            # Monthly statistics
            stats = []
            for month in range(1, 13):
                count = Policy.objects.filter(
                    created_at__year=year,
                    created_at__month=month,
                    deleted_at__isnull=True
                ).count()
                stats.append({
                    'period': f"{year}-{month:02d}",
                    'count': count
                })
        elif period == 'quarterly':
            # Quarterly statistics
            stats = []
            quarters = [
                (1, [1, 2, 3]),
                (2, [4, 5, 6]),
                (3, [7, 8, 9]),
                (4, [10, 11, 12])
            ]
            
            for quarter, months in quarters:
                count = Policy.objects.filter(
                    created_at__year=year,
                    created_at__month__in=months,
                    deleted_at__isnull=True
                ).count()
                stats.append({
                    'period': f"{year}-Q{quarter}",
                    'count': count
                })
        else:
            return Response(
                {'error': 'Period must be "monthly" or "quarterly"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'period': period,
            'year': year,
            'statistics': stats
        }, status=status.HTTP_200_OK)

class PolicyChartDataView(APIView):
    """
    Get policy chart data for frontend
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        period = request.query_params.get('period', 'monthly')
        year = request.query_params.get('year')
        
        if not year:
            return Response(
                {'error': 'Year parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
        except ValueError:
            return Response(
                {'error': 'Year must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        labels = []
        data = []
        
        if period == 'monthly':
            month_names = [
                'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
            ]
            
            for month in range(1, 13):
                count = Policy.objects.filter(
                    created_at__year=year,
                    created_at__month=month,
                    deleted_at__isnull=True
                ).count()
                labels.append(month_names[month - 1])
                data.append(count)
        
        elif period == 'quarterly':
            quarters = ['Q1', 'Q2', 'Q3', 'Q4']
            quarter_months = [
                [1, 2, 3],
                [4, 5, 6],
                [7, 8, 9],
                [10, 11, 12]
            ]
            
            for i, months in enumerate(quarter_months):
                count = Policy.objects.filter(
                    created_at__year=year,
                    created_at__month__in=months,
                    deleted_at__isnull=True
                ).count()
                labels.append(quarters[i])
                data.append(count)
        
        return Response({
            'labels': labels,
            'datasets': [{
                'label': f'Policies {year}',
                'data': data,
                'backgroundColor': 'rgba(34, 197, 94, 0.5)',
                'borderColor': 'rgba(34, 197, 94, 1)',
                'borderWidth': 1
            }]
        }, status=status.HTTP_200_OK)

class UpgradePatientClassView(APIView):
    """
    Upgrade patient class
    """
    permission_classes = [IsAdminUser]
    
    def put(self, request, patient_id):
        new_class = request.data.get('new_class')
        
        if not new_class:
            return Response(
                {'error': 'new_class is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_class = int(new_class)
        except ValueError:
            return Response(
                {'error': 'new_class must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_class not in [1, 2, 3]:
            return Response(
                {'error': 'new_class must be 1, 2, or 3'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from profiles.models import Patient
            patient = Patient.objects.get(user__id=patient_id, user__deleted_at__isnull=True)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if patient.p_class <= new_class:
            return Response(
                {'error': 'Can only upgrade to higher class'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_class = patient.p_class
        patient.p_class = new_class
        patient.save()
        
        return Response({
            'message': f'Patient class upgraded from Class {old_class} to Class {new_class}',
            'patient': {
                'id': patient.user.id,
                'name': patient.user.name,
                'nik': patient.nik,
                'old_class': old_class,
                'new_class': new_class
            }
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