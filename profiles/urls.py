from django.urls import path
from . import views

urlpatterns = [    
    # PBI-BE-U1: Get All EndUser (Admin)
    path('users/', views.UserListView.as_view(), name='user-list'),
    
    # PBI-BE-U9: GET Detail User (All)
    path('users/me/', views.UserDetailView.as_view(), name='user-profile'),
    path('users/<str:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # PBI-BE-U2: GET All Patient (Admin, Doctor, Nurse)
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    
    # PBI-BE-U3: GET Patient by NIK (Admin, Doctor, Nurse)
    path('patients/search/', views.PatientSearchView.as_view(), name='patient-search'),
    path('patients/<str:nik>/', views.PatientDetailView.as_view(), name='patient-detail'),
    
    # PBI-BE-U4: GET All Doctor (Admin, Patient)
    path('doctors/', views.DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<str:pk>/', views.DoctorDetailView.as_view(), name='doctor-detail'),
    
    # PBI-BE-U5: Get Available Doctor's Schedule by Doctor ID (Admin, Patient)
    path('doctors/<str:doctor_id>/schedule/', views.DoctorScheduleView.as_view(), name='doctor-schedule'),
    
    # PBI-BE-U6: PUT Upgrade Patient Class (Admin)
    path('patients/upgrade-class/', views.UpgradePatientClassView.as_view(), name='upgrade-patient-class'),
]