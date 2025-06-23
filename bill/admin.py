from django.contrib import admin
from .models import Bill, BillCoveredTreatment

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'status', 'subtotal', 'total_amount_due', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'patient__user__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(BillCoveredTreatment)
class BillCoveredTreatmentAdmin(admin.ModelAdmin):
    list_display = ['bill', 'treatment_name', 'treatment_price', 'coverage_amount']
    search_fields = ['bill__id', 'treatment_name']