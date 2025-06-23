from django.urls import path
from . import views

urlpatterns = [
    # Coverages
    path('coverages/', views.CoverageListView.as_view(), name='coverage-list'),
    
    # Companies
    path('companies/', views.CompanyListView.as_view(), name='company-list'),
    path('companies/<uuid:pk>/', views.CompanyDetailView.as_view(), name='company-detail'),
    
    # Policies
    path('policies/', views.PolicyListView.as_view(), name='policy-list'),
    path('policies/<str:pk>/', views.PolicyDetailView.as_view(), name='policy-detail'),
    path('policies/<str:pk>/cancel/', views.CancelPolicyView.as_view(), name='cancel-policy'),
    path('policies/for-treatments/', views.PolicyForTreatmentsView.as_view(), name='policies-for-treatments'),
    
    # Statistics
    path('policies/statistics/', views.PolicyStatisticsView.as_view(), name='policy-statistics'),
    path('policies/statistics/chart/', views.PolicyChartDataView.as_view(), name='policy-chart-data'),
    
    # Patient management
    path('patients/<uuid:patient_id>/upgrade-class/', views.UpgradePatientClassView.as_view(), name='upgrade-patient-class'),
    
    # Patient-specific views
    path('patient/policies/', views.PatientPolicyListView.as_view(), name='patient-policy-list'),
    path('patient/policies/<str:pk>/', views.PatientPolicyDetailView.as_view(), name='patient-policy-detail'),
]