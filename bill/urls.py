from django.urls import path
from . import views

urlpatterns = [
    # Bills - Main endpoints
    path('bills/', views.BillListView.as_view(), name='bill-list'),
    path('bills/<uuid:pk>/', views.BillDetailView.as_view(), name='bill-detail'),
    path('bills/create/', views.CreateBillView.as_view(), name='create-bill'),  # PBI-BE-B2
    path('bills/<uuid:pk>/update/', views.UpdateBillView.as_view(), name='update-bill'),  # PBI-BE-B3
    
    # Bills by patient
    path('bills/patient/<uuid:patient_id>/', views.BillsByPatientView.as_view(), name='bills-by-patient'),  # PBI-BE-B1
    
    # Bill actions
    path('bills/pay/', views.PayBillView.as_view(), name='pay-bill'),
    path('bills/update-components/', views.UpdateBillComponentsView.as_view(), name='update-bill-components'),
    path('bills/summary/', views.BillSummaryView.as_view(), name='bill-summary'),
    path('bills/unpaid/', views.UnpaidBillsView.as_view(), name='unpaid-bills'),
    
    # Statistics
    path('bills/statistics/', views.BillStatisticsView.as_view(), name='bill-statistics'),
    
    # Patient-specific views
    path('patient/bills/', views.PatientBillListView.as_view(), name='patient-bill-list'),
    path('patient/bills/<uuid:pk>/', views.PatientBillDetailView.as_view(), name='patient-bill-detail'),
]