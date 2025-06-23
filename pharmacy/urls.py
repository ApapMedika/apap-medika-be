from django.urls import path
from . import views

urlpatterns = [
    # Medicines
    path('medicines/', views.MedicineListView.as_view(), name='medicine-list'),
    path('medicines/<str:pk>/', views.MedicineDetailView.as_view(), name='medicine-detail'),
    path('medicines/<str:pk>/update-stock/', views.MedicineStockUpdateView.as_view(), name='medicine-update-stock'),
    path('medicines/restock/', views.RestockMedicinesView.as_view(), name='restock-medicines'),
    
    # Prescriptions
    path('prescriptions/', views.PrescriptionListView.as_view(), name='prescription-list'),
    path('prescriptions/<str:pk>/', views.PrescriptionDetailView.as_view(), name='prescription-detail'),
    path('prescriptions/<str:pk>/process/', views.ProcessPrescriptionView.as_view(), name='process-prescription'),
    path('prescriptions/statistics/', views.PrescriptionStatisticsView.as_view(), name='prescription-statistics'),
    
    # Doctor prescription views
    path('doctor/prescriptions/', views.DoctorPrescriptionListView.as_view(), name='doctor-prescription-list'),
    path('doctor/prescriptions/<str:pk>/', views.DoctorPrescriptionDetailView.as_view(), name='doctor-prescription-detail'),
    
    # Patient prescription views
    path('patient/prescriptions/', views.PatientPrescriptionListView.as_view(), name='patient-prescription-list'),
    path('patient/prescriptions/<str:pk>/', views.PatientPrescriptionDetailView.as_view(), name='patient-prescription-detail'),
]