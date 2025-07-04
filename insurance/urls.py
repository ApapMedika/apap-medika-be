from django.urls import path
from . import views

urlpatterns = [
    # Coverages
    path('coverages/', views.CoverageListView.as_view(), name='coverage-list'),
    
    # Companies
    path('companies/', views.CompanyListView.as_view(), name='company-list'),
    path('companies/<uuid:pk>/', views.CompanyDetailView.as_view(), name='company-detail'),
    
    # Policies - Main endpoints
    path('policies/', views.PolicyListView.as_view(), name='policy-list'),  # PBI-BE-I1, PBI-BE-I5
    path('policies/<str:pk>/', views.PolicyDetailView.as_view(), name='policy-detail'),  # PBI-BE-I4, PBI-BE-I6, PBI-BE-I9
    
    # Policies - Filtering endpoints
    path('policies/status/<int:status>/', views.PolicyListByStatusView.as_view(), name='policy-list-by-status'),  # PBI-BE-I2
    path('policies/coverage-range/', views.PolicyListByCoverageRangeView.as_view(), name='policy-list-by-coverage-range'),  # PBI-BE-I3
    
    # Policies - Actions
    path('policies/<str:pk>/update-status/', views.UpdatePolicyStatusView.as_view(), name='update-policy-status'),  # PBI-BE-I7
    path('policies/<str:pk>/cancel/', views.CancelPolicyView.as_view(), name='cancel-policy'),  # PBI-BE-I8
    path('policies/for-treatments/', views.PolicyForTreatmentsView.as_view(), name='policies-for-treatments'),  # PBI-BE-I10
    
    # Statistics
    path('policies/statistics/', views.PolicyStatisticsView.as_view(), name='policy-statistics'),
    
    # Patient-specific views
    path('patient/policies/', views.PatientPolicyListView.as_view(), name='patient-policy-list'),
    path('patient/policies/<str:pk>/', views.PatientPolicyDetailView.as_view(), name='patient-policy-detail'),
]