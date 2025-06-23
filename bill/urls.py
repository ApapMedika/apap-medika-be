from django.urls import path
from . import views

urlpatterns = [
    # Bills
    path('bills/', views.BillListView.as_view(), name='bill-list'),
    path('bills/<uuid:pk>/', views.BillDetailView.as_view(), name='bill-detail'),
    path('bills/pay/', views.PayBillView.as_view(), name='pay-bill'),
    path('bills/update-components/', views.UpdateBillComponentsView.as_view(), name='update-bill-components'),
    path('bills/summary/', views.BillSummaryView.as_view(), name='bill-summary'),
    path('bills/unpaid/', views.UnpaidBillsView.as_view(), name='unpaid-bills'),
    
    # Bills by patient
    path('bills/patient/<uuid:patient_id>/', views.BillsByPatientView.as_view(), name='bills-by-patient'),
    
    # Statistics
    path('bills/statistics/', views.BillStatisticsView.as_view(), name='bill-statistics'),
    path('bills/statistics/chart/', views.BillChartDataView.as_view(), name='bill-chart-data'),
    
    # Patient-specific views
    path('patient/bills/', views.PatientBillListView.as_view(), name='patient-bill-list'),
    path('patient/bills/<uuid:pk>/', views.PatientBillDetailView.as_view(), name='patient-bill-detail'),
]