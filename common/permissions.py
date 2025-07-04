from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'ADMIN')

class IsDoctorUser(permissions.BasePermission):
    """
    Custom permission to only allow doctor users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'DOCTOR')

class IsNurseUser(permissions.BasePermission):
    """
    Custom permission to only allow nurse users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'NURSE')

class IsPharmacistUser(permissions.BasePermission):
    """
    Custom permission to only allow pharmacist users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'PHARMACIST')

class IsPatientUser(permissions.BasePermission):
    """
    Custom permission to only allow patient users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'PATIENT')

class IsAdminOrNurseUser(permissions.BasePermission):
    """
    Custom permission to only allow admin or nurse users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'NURSE'])

class IsAdminOrDoctorUser(permissions.BasePermission):
    """
    Custom permission to only allow admin or doctor users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'DOCTOR'])

class IsAdminOrDoctorOrNurseUser(permissions.BasePermission):
    """
    Custom permission to only allow admin, doctor, or nurse users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'DOCTOR', 'NURSE'])

class IsAdminOrPharmacistUser(permissions.BasePermission):
    """
    Custom permission to only allow admin or pharmacist users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'PHARMACIST'])

class IsOwnerOrAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admin users.
    """
    def has_object_permission(self, request, view, obj):
        # Admin can access anything
        if request.user.role == 'ADMIN':
            return True
        
        # Check if user is the owner
        if hasattr(obj, 'patient') and hasattr(request.user, 'patient'):
            return obj.patient == request.user.patient
        elif hasattr(obj, 'doctor') and hasattr(request.user, 'doctor'):
            return obj.doctor == request.user.doctor
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False

class IsAdminOrPatientUser(permissions.BasePermission):
    """
    Custom permission to only allow admin or patient users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'PATIENT'])

class IsAdminOrNurseOrPatientUser(permissions.BasePermission):
    """
    Custom permission to only allow admin, nurse, or patient users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'NURSE', 'PATIENT'])

class IsAdminOrPharmacistOrDoctorOrNurseUser(permissions.BasePermission):
    """
    Custom permission to only allow admin, pharmacist, doctor, or nurse users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'PHARMACIST', 'DOCTOR', 'NURSE'])

class IsAdminOrPharmacistOrDoctorUser(permissions.BasePermission):
    """
    Custom permission to only allow admin, pharmacist, or doctor users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.role in ['ADMIN', 'PHARMACIST', 'DOCTOR'])