from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('jwt/', views.get_jwt_token, name='get_jwt_token'),
    
    # PBI-BE-U1: Get All EndUser (Admin)
    path('users/', views.UserListView.as_view(), name='user-list'),
    
    # PBI-BE-U9: GET Detail User (All)
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('users/me/', views.UserDetailView.as_view(), name='user-profile'),
    
    # PBI-BE-U2: GET All Patient (Admin, Doctor, Nurse)
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    
    # PBI-BE-U3: GET Patient by NIK (Admin, Doctor, Nurse)
    path('patients/<str:nik>/', views.PatientDetailView.as_view(), name='patient-detail'),
    path('patients/search/', views.PatientSearchView.as_view(), name='patient-search'),
    
    # PBI-BE-U4: GET All Doctor (Admin, Patient)
    path('doctors/', views.DoctorListView.as_view(), name='doctor-list'),
    path('doctors/<str:pk>/', views.DoctorDetailView.as_view(), name='doctor-detail'),
    
    # PBI-BE-U5: Get Available Doctor's Schedule by Doctor ID (Admin, Patient)
    path('doctors/<str:doctor_id>/schedule/', views.DoctorScheduleView.as_view(), name='doctor-schedule'),
    
    # PBI-BE-U6: PUT Upgrade Patient Class (Admin)
    path('patients/upgrade-class/', views.UpgradePatientClassView.as_view(), name='upgrade-patient-class'),
]