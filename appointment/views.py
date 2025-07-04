from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from datetime import datetime, date

from .models import Treatment, Appointment, AppointmentTreatment
from .serializers import (
    TreatmentSerializer, AppointmentSerializer, CreateAppointmentSerializer,
    UpdateAppointmentSerializer, UpdateDiagnosisTreatmentSerializer,
    UpdateAppointmentStatusSerializer
)
from common.permissions import (
    IsAdminUser, IsAdminOrDoctorUser, IsAdminOrNurseUser, IsPatientUser, IsAdminOrDoctorOrNurseUser, IsAdminOrPatientUser
)
from common.utils import soft_delete_object

# ==================== TREATMENT VIEWS ====================

class TreatmentListView(generics.ListAPIView):
    """
    List all treatments
    """
    queryset = Treatment.objects.all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated]

# ==================== APPOINTMENT VIEWS ====================

class AppointmentListView(generics.ListCreateAPIView):
    """
    List all appointments or create new appointment
    PBI-BE-A1: GET All Appointment (Admin, Nurse)
    PBI-BE-A6: POST Create Appointment (Admin, Patient)
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'doctor']
    search_fields = ['id', 'patient__user__name', 'doctor__user__name']
    ordering_fields = ['id', 'date', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateAppointmentSerializer
        return AppointmentSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            # Admin and Patient can create appointments
            return [IsAdminOrPatientUser()]
        # Admin and Nurse can view all appointments
        return [IsAdminOrNurseUser()]
    
    def get_queryset(self):
        queryset = Appointment.objects.filter(deleted_at__isnull=True)
        
        # Date range filtering (PBI-BE-A5)
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            try:
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__date__gte=from_date)
            except ValueError:
                pass
        
        if to_date:
            try:
                to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__date__lte=to_date)
            except ValueError:
                pass
        
        return queryset

class AppointmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete appointment details
    PBI-BE-A2: GET Appointment by ID (Admin, Doctor, Nurse, Patient)
    PBI-BE-A7: PUT Update Appointment Status (Admin, Patient)
    PBI-BE-A19: DELETE Appointment (Admin)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdateAppointmentSerializer
        return AppointmentSerializer
    
    def get_queryset(self):
        queryset = Appointment.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering
        if self.request.user.role == 'DOCTOR':
            queryset = queryset.filter(doctor=self.request.user.doctor)
        elif self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        return queryset
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdminUser()]
        elif self.request.method in ['PUT', 'PATCH']:
            return [IsAdminOrPatientUser()]
        return [permissions.IsAuthenticated()]
    
    def perform_destroy(self, instance):
        # Soft delete
        soft_delete_object(instance, self.request.user)

class AppointmentsByDoctorView(generics.ListAPIView):
    """
    List appointments for a specific doctor
    PBI-BE-A3: GET Appointment List by Doctor ID (Doctor)
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdminOrDoctorUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'patient__user__name']
    ordering = ['-date']
    
    def get_queryset(self):
        doctor_id = self.kwargs['doctor_id']
        
        # If user is doctor, ensure they can only see their own appointments
        if self.request.user.role == 'DOCTOR' and self.request.user.doctor.id != doctor_id:
            return Appointment.objects.none()
        
        return Appointment.objects.filter(
            doctor__id=doctor_id,
            deleted_at__isnull=True
        )

class AppointmentsByPatientView(generics.ListAPIView):
    """
    List appointments for a specific patient
    PBI-BE-A4: GET Appointment List by Patient ID (Patient)
    """
    serializer_class = AppointmentSerializer
    permission_classes = [IsPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'doctor__user__name']
    ordering = ['-date']
    
    def get_queryset(self):
        patient_id = self.kwargs['patient_id']
        
        # Patients can only view their own appointments
        if str(self.request.user.patient.user.id) != str(patient_id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only view your own appointments.")
        
        return Appointment.objects.filter(
            patient__user__id=patient_id,
            deleted_at__isnull=True
        )

class AppointmentsByDateRangeView(APIView):
    """
    Get appointment count by date range
    PBI-BE-A5: GET Appointment List by Date Range (Admin, Doctor, Nurse)
    """
    permission_classes = [IsAdminOrDoctorOrNurseUser]
    
    def get(self, request):
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if not from_date or not to_date:
            return Response(
                {'error': 'Both from_date and to_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = Appointment.objects.filter(
            date__date__gte=from_date,
            date__date__lte=to_date,
            deleted_at__isnull=True
        )
        
        # If doctor, filter by their appointments
        if request.user.role == 'DOCTOR':
            queryset = queryset.filter(doctor=request.user.doctor)
        
        appointments = AppointmentSerializer(queryset, many=True).data
        
        return Response({
            'from_date': from_date,
            'to_date': to_date,
            'count': queryset.count(),
            'appointments': appointments
        }, status=status.HTTP_200_OK)

class UpdateAppointmentStatusView(APIView):
    """
    Update appointment status (done/cancel)
    PBI-BE-A7: PUT Update Appointment Status (Admin, Patient)
    """
    permission_classes = [IsAdminOrPatientUser]
    
    def put(self, request, pk, action):
        try:
            appointment = Appointment.objects.get(pk=pk, deleted_at__isnull=True)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if request.user.role == 'PATIENT' and appointment.patient != request.user.patient:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        if action not in ['done', 'cancel']:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = UpdateAppointmentStatusSerializer(
            appointment,
            data={'action': action},
            context={'request': request}
        )
        
        if serializer.is_valid():
            appointment = serializer.save()
            
            # Determine status message
            if action == 'done':
                message = f"Appointment {appointment.id} marked as done"
            else:
                message = f"Appointment {appointment.id} cancelled"
            
            return Response({
                'message': message,
                'appointment': AppointmentSerializer(appointment).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateDiagnosisTreatmentView(APIView):
    """
    Update appointment diagnosis and treatments
    PBI-BE-A8: PUT Update Appointment Diagnosis & Treatment (Doctor)
    """
    permission_classes = [IsAdminOrDoctorUser]
    
    def get(self, request, pk):
        """
        Get appointment details for diagnosis update
        """
        try:
            appointment = Appointment.objects.get(pk=pk, deleted_at__isnull=True)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if request.user.role == 'DOCTOR' and appointment.doctor != request.user.doctor:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'appointment': AppointmentSerializer(appointment).data,
            'treatments': TreatmentSerializer(Treatment.objects.all(), many=True).data
        }, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        """
        Update diagnosis and treatments
        """
        try:
            appointment = Appointment.objects.get(pk=pk, deleted_at__isnull=True)
        except Appointment.DoesNotExist:
            return Response({'error': 'Appointment not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if request.user.role == 'DOCTOR' and appointment.doctor != request.user.doctor:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = UpdateDiagnosisTreatmentSerializer(
            appointment, 
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            appointment = serializer.save()
            return Response({
                'message': 'Diagnosis and treatments updated successfully',
                'appointment': AppointmentSerializer(appointment).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AppointmentStatisticsView(APIView):
    """
    Get appointment statistics
    """
    permission_classes = [IsAdminOrDoctorUser]
    
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
                count = Appointment.objects.filter(
                    date__year=year,
                    date__month=month,
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
                count = Appointment.objects.filter(
                    date__year=year,
                    date__month__in=months,
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

class AppointmentChartDataView(APIView):
    """
    Get appointment chart data for frontend
    """
    permission_classes = [IsAdminOrDoctorUser]
    
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
                count = Appointment.objects.filter(
                    date__year=year,
                    date__month=month,
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
                count = Appointment.objects.filter(
                    date__year=year,
                    date__month__in=months,
                    deleted_at__isnull=True
                ).count()
                labels.append(quarters[i])
                data.append(count)
        
        return Response({
            'labels': labels,
            'datasets': [{
                'label': f'Appointments {year}',
                'data': data,
                'backgroundColor': 'rgba(59, 130, 246, 0.5)',
                'borderColor': 'rgba(59, 130, 246, 1)',
                'borderWidth': 1
            }]
        }, status=status.HTTP_200_OK)

class TodayAppointmentsView(APIView):
    """
    Get today's appointments count
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        today = date.today()
        count = Appointment.objects.filter(
            date__date=today,
            deleted_at__isnull=True
        ).count()
        
        return Response({'count': count}, status=status.HTTP_200_OK)