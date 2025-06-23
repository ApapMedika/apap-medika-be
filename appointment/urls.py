from django.urls import path
from . import views

urlpatterns = [
    # Treatments
    path('treatments/', views.TreatmentListView.as_view(), name='treatment-list'),
    
    # Appointments
    path('appointments/', views.AppointmentListView.as_view(), name='appointment-list'),
    path('appointments/<str:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    path('appointments/doctor/<str:doctor_id>/', views.AppointmentsByDoctorView.as_view(), name='appointments-by-doctor'),
    path('appointments/patient/<uuid:patient_id>/', views.AppointmentsByPatientView.as_view(), name='appointments-by-patient'),
    path('appointments/date-range/count/', views.AppointmentsByDateRangeView.as_view(), name='appointments-by-date-range'),
    path('appointments/today/count/', views.TodayAppointmentsView.as_view(), name='today-appointments'),
    
    # Appointment actions
    path('appointments/<str:pk>/status/<str:action>/', views.UpdateAppointmentStatusView.as_view(), name='update-appointment-status'),
    path('appointments/<str:pk>/diagnosis/', views.UpdateDiagnosisTreatmentView.as_view(), name='update-diagnosis-treatment'),
    
    # Statistics
    path('appointments/statistics/', views.AppointmentStatisticsView.as_view(), name='appointment-statistics'),
    path('appointments/statistics/chart/', views.AppointmentChartDataView.as_view(), name='appointment-chart-data'),
]