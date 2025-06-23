from django.contrib import admin
from .models import Coverage, Company, CompanyCoverage, Policy, PolicyCoverage

@admin.register(Coverage)
class CoverageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'coverage_amount']
    search_fields = ['name']

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact', 'email', 'created_at']
    search_fields = ['name', 'email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CompanyCoverage)
class CompanyCoverageAdmin(admin.ModelAdmin):
    list_display = ['company', 'coverage']
    list_filter = ['company', 'coverage']

@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'company', 'status', 'expiry_date', 'total_coverage']
    list_filter = ['status', 'company', 'expiry_date']
    search_fields = ['id', 'patient__user__name', 'company__name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PolicyCoverage)
class PolicyCoverageAdmin(admin.ModelAdmin):
    list_display = ['policy', 'coverage', 'used']
    list_filter = ['used', 'coverage']
    search_fields = ['policy__id', 'coverage__name']