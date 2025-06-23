from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import EndUser, Admin, Nurse, Patient, Doctor, Pharmacist

@admin.register(EndUser)
class EndUserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'name', 'role', 'gender', 'is_active', 'created_at']
    list_filter = ['role', 'gender', 'is_active', 'created_at']
    search_fields = ['username', 'email', 'name']
    ordering = ['created_at']
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('name', 'email', 'gender')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at', 'deleted_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'name', 'gender', 'role', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Admin)
class AdminAdmin(admin.ModelAdmin):
    list_display = ['user']

@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = ['user']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['user', 'nik', 'birth_date', 'p_class']
    list_filter = ['p_class']
    search_fields = ['user__name', 'nik']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'specialization', 'years_of_experience', 'fee']
    list_filter = ['specialization']
    search_fields = ['user__name', 'id']

@admin.register(Pharmacist)
class PharmacistAdmin(admin.ModelAdmin):
    list_display = ['user']