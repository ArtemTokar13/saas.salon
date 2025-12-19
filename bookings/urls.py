from django.urls import path
from . import views

urlpatterns = [
    path('book/<int:company_id>/', views.create_booking, name='create_booking'),
    path('confirmation/<int:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('calendar/', views.booking_calendar, name='booking_calendar'),
    path('update-status/<int:booking_id>/', views.update_booking_status, name='update_booking_status'),
    path('api/update-booking/<int:booking_id>/', views.update_booking_ajax, name='update_booking_ajax'),
    path('api/delete-booking/<int:booking_id>/', views.delete_booking_ajax, name='delete_booking_ajax'),
    path('api/staff/<int:company_id>/<int:service_id>/', views.get_available_staff, name='get_available_staff'),
    path('api/times/<int:company_id>/<int:staff_id>/<str:date_str>/', views.get_available_times, name='get_available_times'),
]
