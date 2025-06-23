from django.contrib import admin
from .models import Medicine, Prescription, MedicineQuantity

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'stock', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['id', 'name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'status', 'total_price', 'processed_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'patient__user__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(MedicineQuantity)
class MedicineQuantityAdmin(admin.ModelAdmin):
    list_display = ['prescription', 'medicine', 'quantity', 'fulfilled_quantity']
    list_filter = ['prescription__status']
    search_fields = ['prescription__id', 'medicine__name']