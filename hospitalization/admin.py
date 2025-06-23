from django.contrib import admin
from .models import Room, Facility, Reservation, ReservationFacility

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'max_capacity', 'price_per_day', 'created_at']
    list_filter = ['max_capacity', 'created_at']
    search_fields = ['id', 'name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'fee', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'room', 'date_in', 'date_out', 'total_fee']
    list_filter = ['date_in', 'date_out', 'room']
    search_fields = ['id', 'patient__user__name', 'room__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ReservationFacility)
class ReservationFacilityAdmin(admin.ModelAdmin):
    list_display = ['reservation', 'facility']
    list_filter = ['facility']
    search_fields = ['reservation__id', 'facility__name']