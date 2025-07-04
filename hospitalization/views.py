from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from datetime import datetime, date

from .models import Room, Facility, Reservation, ReservationFacility
from .serializers import (
    RoomSerializer, FacilitySerializer, ReservationSerializer,
    CreateReservationSerializer, UpdateReservationRoomSerializer,
    UpdateReservationFacilitiesSerializer
)
from common.permissions import (
    IsAdminUser, IsAdminOrNurseUser, IsPatientUser, IsNurseUser,
    IsAdminOrNurseOrPatientUser
)
from common.utils import soft_delete_object

# ==================== ROOM VIEWS ====================

class RoomListView(generics.ListCreateAPIView):
    """
    List all rooms or create new room
    PBI-BE-H7: GET All Room (Nurse) - Date filter support
    """
    serializer_class = RoomSerializer
    permission_classes = [IsNurseUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['id', 'name']
    ordering_fields = ['id', 'name', 'max_capacity', 'price_per_day', 'created_at']
    ordering = ['id']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsNurseUser()]
    
    def get_queryset(self):
        queryset = Room.objects.filter(deleted_at__isnull=True)
        
        # Date-based filtering for availability (PBI-BE-H7)
        date_in = self.request.query_params.get('date_in')
        date_out = self.request.query_params.get('date_out')
        
        if date_in and date_out:
            try:
                date_in = datetime.strptime(date_in, '%Y-%m-%d').date()
                date_out = datetime.strptime(date_out, '%Y-%m-%d').date()
                
                # Filter rooms that have availability
                available_rooms = []
                for room in queryset:
                    if room.get_available_capacity(date_in, date_out) > 0:
                        available_rooms.append(room.id)
                
                queryset = queryset.filter(id__in=available_rooms)
            except ValueError:
                pass
        
        return queryset

class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete room details
    """
    serializer_class = RoomSerializer
    permission_classes = [IsNurseUser]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminUser()]
        return [IsNurseUser()]
    
    def get_queryset(self):
        return Room.objects.filter(deleted_at__isnull=True)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get room details with reservation info for date range
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        data = serializer.data
        
        # Add reservation details if date range provided
        date_in = request.query_params.get('date_in')
        date_out = request.query_params.get('date_out')
        
        if date_in and date_out:
            try:
                date_in = datetime.strptime(date_in, '%Y-%m-%d').date()
                date_out = datetime.strptime(date_out, '%Y-%m-%d').date()
                
                # Get reservations in date range
                reservations = Reservation.objects.filter(
                    room=instance,
                    date_in__lte=date_out,
                    date_out__gte=date_in,
                    deleted_at__isnull=True
                ).select_related('patient__user')
                
                reservation_data = []
                for reservation in reservations:
                    reservation_data.append({
                        'id': reservation.id,
                        'patient_name': reservation.patient.user.name,
                        'date_in': reservation.date_in,
                        'date_out': reservation.date_out
                    })
                
                data['reservations'] = reservation_data
                data['available_capacity'] = instance.get_available_capacity(date_in, date_out)
                
            except ValueError:
                pass
        
        return Response(data)
    
    def perform_destroy(self, instance):
        # Check if room has active reservations
        active_reservations = Reservation.objects.filter(
            room=instance,
            date_out__gte=date.today(),
            deleted_at__isnull=True
        ).exists()
        
        if active_reservations:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot delete room with active reservations.")
        
        # Soft delete
        soft_delete_object(instance, self.request.user)

# ==================== FACILITY VIEWS ====================

class FacilityListView(generics.ListCreateAPIView):
    """
    List all facilities or create new facility
    """
    serializer_class = FacilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'fee', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        return Facility.objects.filter(deleted_at__isnull=True)

class FacilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Get, update, or delete facility details
    """
    serializer_class = FacilitySerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        return Facility.objects.filter(deleted_at__isnull=True)
    
    def perform_destroy(self, instance):
        # Soft delete
        soft_delete_object(instance, self.request.user)

# ==================== RESERVATION VIEWS ====================

class ReservationListView(generics.ListCreateAPIView):
    """
    List all reservations or create new reservation
    PBI-BE-H1: GET All Reservations (Nurse, Patient, Admin)
    PBI-BE-H3: POST Create Reservation (Nurse)
    """
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['id', 'patient__user__name', 'room__name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateReservationSerializer
        return ReservationSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsNurseUser()]
        return [IsAdminOrNurseOrPatientUser()]
    
    def get_queryset(self):
        queryset = Reservation.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering (PBI-BE-H1)
        if self.request.user.role == 'NURSE':
            # Return all reservations made by this nurse
            queryset = queryset.filter(assigned_nurse=self.request.user.nurse)
        elif self.request.user.role == 'PATIENT':
            # Return all reservations for this patient
            queryset = queryset.filter(patient=self.request.user.patient)
        # Admin can see all reservations
        
        return queryset

class ReservationDetailView(generics.RetrieveDestroyAPIView):
    """
    Get or delete reservation details
    PBI-BE-H2: GET Detail Reservation by ID (Nurse, Patient, Admin)
    PBI-BE-H6: DELETE Reservation By ID (Nurse, Admin)
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsAdminOrNurseOrPatientUser]
    
    def get_queryset(self):
        queryset = Reservation.objects.filter(deleted_at__isnull=True)
        
        # Role-based filtering (PBI-BE-H2)
        if self.request.user.role == 'NURSE':
            queryset = queryset.filter(assigned_nurse=self.request.user.nurse)
        elif self.request.user.role == 'PATIENT':
            queryset = queryset.filter(patient=self.request.user.patient)
        
        return queryset
    
    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdminOrNurseUser()]
        return [IsAdminOrNurseOrPatientUser()]
    
    def retrieve(self, request, *args, **kwargs):
        """
        Get reservation details with proper error handling (PBI-BE-H2)
        """
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except Reservation.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def perform_destroy(self, instance):
        # Check if reservation can be deleted (not ongoing) - PBI-BE-H6
        if instance.date_in <= date.today():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Cannot delete ongoing or past reservations.")
        
        # Soft delete
        soft_delete_object(instance, self.request.user)

class UpdateReservationRoomView(APIView):
    """
    Update reservation room and dates
    PBI-BE-H4: PUT Update Reservation date & room By ID (Nurse)
    """
    permission_classes = [IsNurseUser]
    
    def get(self, request, pk):
        """
        Get reservation details for room update
        """
        try:
            reservation = Reservation.objects.get(pk=pk, deleted_at__isnull=True)
        except Reservation.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if (request.user.role == 'NURSE' and 
            reservation.assigned_nurse != request.user.nurse):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'reservation': ReservationSerializer(reservation).data,
            'rooms': RoomSerializer(Room.objects.filter(deleted_at__isnull=True), many=True).data
        }, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        """
        Update reservation room and dates
        """
        try:
            reservation = Reservation.objects.get(pk=pk, deleted_at__isnull=True)
        except Reservation.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user can update this reservation
        if (request.user.role == 'NURSE' and 
            reservation.assigned_nurse != request.user.nurse):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if reservation can be updated (before date_in)
        if reservation.date_in <= date.today():
            return Response(
                {'error': 'Cannot update reservation that has already started'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = UpdateReservationRoomSerializer(
            reservation,
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            reservation = serializer.save()
            return Response({
                'message': 'Reservation updated successfully',
                'reservation': ReservationSerializer(reservation).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateReservationFacilitiesView(APIView):
    """
    Update reservation facilities
    PBI-BE-H5: PUT Update Reservation Facilities By ID (Nurse)
    """
    permission_classes = [IsNurseUser]
    
    def get(self, request, pk):
        """
        Get reservation details for facility update
        """
        try:
            reservation = Reservation.objects.get(pk=pk, deleted_at__isnull=True)
        except Reservation.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check permissions
        if (request.user.role == 'NURSE' and 
            reservation.assigned_nurse != request.user.nurse):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        return Response({
            'reservation': ReservationSerializer(reservation).data,
            'facilities': FacilitySerializer(Facility.objects.filter(deleted_at__isnull=True), many=True).data
        }, status=status.HTTP_200_OK)
    
    def put(self, request, pk):
        """
        Update reservation facilities
        """
        try:
            reservation = Reservation.objects.get(pk=pk, deleted_at__isnull=True)
        except Reservation.DoesNotExist:
            return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user can update this reservation
        if (request.user.role == 'NURSE' and 
            reservation.assigned_nurse != request.user.nurse):
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if reservation can be updated (before date_out)
        if reservation.date_out <= date.today():
            return Response(
                {'error': 'Cannot update facilities after checkout date'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = UpdateReservationFacilitiesSerializer(
            reservation,
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            reservation = serializer.save()
            return Response({
                'message': 'Reservation facilities updated successfully',
                'reservation': ReservationSerializer(reservation).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== STATISTICS VIEWS ====================

class ReservationStatisticsView(APIView):
    """
    Get reservation statistics
    """
    permission_classes = [IsAdminOrNurseUser]
    
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
                count = Reservation.objects.filter(
                    date_in__year=year,
                    date_in__month=month,
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
                count = Reservation.objects.filter(
                    date_in__year=year,
                    date_in__month__in=months,
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

class ReservationChartDataView(APIView):
    """
    Get reservation chart data for frontend
    """
    permission_classes = [IsAdminOrNurseUser]
    
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
                count = Reservation.objects.filter(
                    date_in__year=year,
                    date_in__month=month,
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
                count = Reservation.objects.filter(
                    date_in__year=year,
                    date_in__month__in=months,
                    deleted_at__isnull=True
                ).count()
                labels.append(quarters[i])
                data.append(count)
        
        return Response({
            'labels': labels,
            'datasets': [{
                'label': f'Reservations {year}',
                'data': data,
                'backgroundColor': 'rgba(99, 255, 132, 0.5)',
                'borderColor': 'rgba(99, 255, 132, 1)',
                'borderWidth': 1
            }]
        }, status=status.HTTP_200_OK)

class PatientReservationListView(generics.ListAPIView):
    """
    List reservations for patient
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsPatientUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['id', 'room__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Reservation.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )

class PatientReservationDetailView(generics.RetrieveAPIView):
    """
    Get reservation details for patient
    """
    serializer_class = ReservationSerializer
    permission_classes = [IsPatientUser]
    
    def get_queryset(self):
        return Reservation.objects.filter(
            patient=self.request.user.patient,
            deleted_at__isnull=True
        )