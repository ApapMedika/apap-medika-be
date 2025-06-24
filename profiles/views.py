from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from oauth2_provider.models import AccessToken
from django.utils import timezone
import calendar
from datetime import date, timedelta

from .models import EndUser, Patient, Doctor
from .serializers import (
    PatientSerializer, DoctorSerializer,
    LoginSerializer, SignUpSerializer, UserDetailSerializer,
    UpgradeClassSerializer
)
from common.permissions import IsAdminUser, IsAdminOrDoctorUser, IsAdminOrNurseUser
from common.utils import generate_jwt_token

class LoginView(APIView):
    """
    Login endpoint (PBI-FE-U1)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT token
            token = generate_jwt_token(user)
            
            # Get user details with profile
            user_serializer = UserDetailSerializer(user)
            
            return Response({
                'message': 'Login successful',
                'token': token,
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SignUpView(APIView):
    """
    Sign up endpoint (PBI-BE-U8, PBI-FE-U2)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT token
            token = generate_jwt_token(user)
            
            # Get user details with profile
            user_serializer = UserDetailSerializer(user)
            
            return Response({
                'message': 'User created successfully',
                'token': token,
                'user': user_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """
    Logout endpoint (PBI-FE-U3)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)

class UserListView(generics.ListAPIView):
    """
    List all users (PBI-BE-U1: Admin only)
    """
    serializer_class = UserDetailSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role']
    search_fields = ['name', 'email', 'username']
    ordering_fields = ['name', 'email', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return EndUser.objects.filter(deleted_at__isnull=True)

class UserDetailView(generics.RetrieveAPIView):
    """
    Get user details (PBI-BE-U9)
    """
    serializer_class = UserDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Handle /users/me/ endpoint
        if self.kwargs.get('pk') == 'me' or not self.kwargs.get('pk'):
            return self.request.user
        
        pk = self.kwargs.get('pk')
        
        # Try to find by UUID first
        try:
            user = EndUser.objects.get(id=pk, deleted_at__isnull=True)
            # Users can view their own profile, admins can view any
            if self.request.user.role == 'ADMIN' or user == self.request.user:
                return user
            else:
                self.permission_denied(self.request)
        except (EndUser.DoesNotExist, ValueError):
            pass
        
        # Try to find by username or email
        user = EndUser.objects.filter(
            Q(username=pk) | Q(email=pk),
            deleted_at__isnull=True
        ).first()
        
        if user:
            # Users can view their own profile, admins can view any
            if self.request.user.role == 'ADMIN' or user == self.request.user:
                return user
            else:
                self.permission_denied(self.request)
        
        from rest_framework.exceptions import NotFound
        raise NotFound("User not found")

class PatientListView(generics.ListAPIView):
    """
    List all patients (PBI-BE-U2: Admin, Doctor, Nurse)
    """
    serializer_class = PatientSerializer
    permission_classes = [IsAdminOrDoctorUser | IsAdminOrNurseUser]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['user__name', 'nik']
    ordering_fields = ['user__name', 'nik', 'user__created_at']
    ordering = ['-user__created_at']
    
    def get_queryset(self):
        return Patient.objects.filter(user__deleted_at__isnull=True)

class PatientDetailView(generics.RetrieveAPIView):
    """
    Get patient details by NIK (PBI-BE-U3: Admin, Doctor, Nurse)
    """
    serializer_class = PatientSerializer
    permission_classes = [IsAdminOrDoctorUser | IsAdminOrNurseUser]
    lookup_field = 'nik'
    
    def get_queryset(self):
        return Patient.objects.filter(user__deleted_at__isnull=True)

class PatientSearchView(APIView):
    """
    Search patient by NIK
    """
    permission_classes = [IsAdminOrDoctorUser | IsAdminOrNurseUser]
    
    def post(self, request):
        nik = request.data.get('nik')
        if not nik:
            return Response({'error': 'NIK is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(nik=nik, user__deleted_at__isnull=True)
            serializer = PatientSerializer(patient)
            return Response({
                'found': True,
                'patient': serializer.data
            }, status=status.HTTP_200_OK)
        except Patient.DoesNotExist:
            return Response({
                'found': False,
                'message': 'Patient not found'
            }, status=status.HTTP_404_NOT_FOUND)

class DoctorListView(generics.ListAPIView):
    """
    List all doctors (PBI-BE-U4: Admin, Patient)
    """
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['specialization']
    search_fields = ['user__name', 'id']
    ordering_fields = ['user__name', 'specialization', 'years_of_experience', 'user__created_at']
    ordering = ['-user__created_at']
    
    def get_queryset(self):
        # Check if user is Admin or Patient
        if self.request.user.role not in ['ADMIN', 'PATIENT']:
            return Doctor.objects.none()
        return Doctor.objects.filter(user__deleted_at__isnull=True)

class DoctorDetailView(generics.RetrieveAPIView):
    """
    Get doctor details
    """
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Doctor.objects.filter(user__deleted_at__isnull=True)

class DoctorScheduleView(APIView):
    """
    Get doctor's available schedule for next 4 weeks (PBI-BE-U5: Admin, Patient)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, doctor_id):
        # Check if user is Admin or Patient
        if request.user.role not in ['ADMIN', 'PATIENT']:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            doctor = Doctor.objects.get(id=doctor_id, user__deleted_at__isnull=True)
        except Doctor.DoesNotExist:
            return Response({'error': 'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get next 4 weeks of available dates based on doctor's schedule
        today = date.today()
        available_dates = []
        
        # Days mapping
        days_mapping = {
            0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
            4: 'Friday', 5: 'Saturday', 6: 'Sunday'
        }
        
        for week in range(4):
            for day in doctor.schedules:
                # Calculate the date for this day in this week
                days_ahead = day - today.weekday()
                if days_ahead < 0:  # Target day already happened this week
                    days_ahead += 7
                days_ahead += week * 7
                
                target_date = today + timedelta(days_ahead)
                
                # Format the date nicely
                day_name = days_mapping[day]
                month_name = calendar.month_name[target_date.month]
                formatted_date = f"{day_name}, {target_date.day} {month_name} {target_date.year}"
                
                available_dates.append({
                    'date': target_date.isoformat(),
                    'formatted': formatted_date
                })
        
        return Response({
            'doctor': DoctorSerializer(doctor).data,
            'available_dates': available_dates
        }, status=status.HTTP_200_OK)

class UpgradePatientClassView(APIView):
    """
    Upgrade patient class (PBI-BE-U6, PBI-FE-U6: Admin only)
    """
    permission_classes = [IsAdminUser]
    
    def put(self, request):
        serializer = UpgradeClassSerializer(data=request.data)
        if serializer.is_valid():
            patient = serializer.validated_data['patient']
            new_class = serializer.validated_data['new_class']
            
            # Update patient class
            old_class = patient.p_class
            patient.p_class = new_class
            patient.save()
            
            return Response({
                'message': f'Patient class upgraded from Class {old_class} to Class {new_class}',
                'patient': PatientSerializer(patient).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def get_jwt_token(request):
    """
    Get JWT token from OAuth token (PBI-BE-U7)
    """
    oauth_token = request.data.get('oauth_token')
    
    if not oauth_token:
        return Response({'error': 'OAuth token is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Verify OAuth token
        access_token = AccessToken.objects.get(
            token=oauth_token,
            expires__gt=timezone.now()
        )
        
        # Check if user exists in our system
        user = access_token.user
        try:
            end_user = EndUser.objects.get(email=user.email, deleted_at__isnull=True)
            # Generate JWT token
            token = generate_jwt_token(end_user)
            return Response({'token': token}, status=status.HTTP_200_OK)
        except EndUser.DoesNotExist:
            return Response({'error': 'User not registered in the system'}, status=status.HTTP_404_NOT_FOUND)
    
    except AccessToken.DoesNotExist:
        return Response({'error': 'Invalid or expired OAuth token'}, status=status.HTTP_401_UNAUTHORIZED)