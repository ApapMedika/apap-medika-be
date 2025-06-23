from django.urls import path
from . import views

urlpatterns = [
    # Rooms
    path('rooms/', views.RoomListView.as_view(), name='room-list'),
    path('rooms/<str:pk>/', views.RoomDetailView.as_view(), name='room-detail'),
    
    # Facilities
    path('facilities/', views.FacilityListView.as_view(), name='facility-list'),
    path('facilities/<uuid:pk>/', views.FacilityDetailView.as_view(), name='facility-detail'),
    
    # Reservations
    path('reservations/', views.ReservationListView.as_view(), name='reservation-list'),
    path('reservations/<str:pk>/', views.ReservationDetailView.as_view(), name='reservation-detail'),
    path('reservations/<str:pk>/update-room/', views.UpdateReservationRoomView.as_view(), name='update-reservation-room'),
    path('reservations/<str:pk>/update-facilities/', views.UpdateReservationFacilitiesView.as_view(), name='update-reservation-facilities'),
    
    # Statistics
    path('reservations/statistics/', views.ReservationStatisticsView.as_view(), name='reservation-statistics'),
    path('reservations/statistics/chart/', views.ReservationChartDataView.as_view(), name='reservation-chart-data'),
    
    # Patient-specific views
    path('patient/reservations/', views.PatientReservationListView.as_view(), name='patient-reservation-list'),
    path('patient/reservations/<str:pk>/', views.PatientReservationDetailView.as_view(), name='patient-reservation-detail'),
]