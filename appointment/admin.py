from django.contrib import admin
from .models import Treatment, Appointment, AppointmentTreatment

@admin.register(Treatment)
class TreatmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price']
    search_fields = ['name']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'doctor', 'date', 'status', 'total_fee']
    list_filter = ['status', 'date', 'doctor__specialization']
    search_fields = ['id', 'patient__user__name', 'doctor__user__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(AppointmentTreatment)
class AppointmentTreatmentAdmin(admin.ModelAdmin):
    list_display = ['appointment', 'treatment']
    list_filter = ['treatment']
    search_fields = ['appointment__id', 'treatment__name']