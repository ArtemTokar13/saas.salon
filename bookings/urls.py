from django.urls import path
from . import views

urlpatterns = [
    path('book/<int:company_id>/', views.create_booking, name='create_booking'),
    path('booking-list/', views.bookings_list, name='bookings_list'),
    path('confirmation/<int:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('confirm-prebooked/<int:booking_id>/', views.confirm_prebooked_booking, name='confirm_prebooked_booking'),
    path('cancel/<int:booking_id>/<str:delete_code>/', views.cancel_booking, name='cancel_booking'),
    path('calendar/', views.booking_calendar, name='booking_calendar'),
    path('calendar-api/', views.calendar_api, name='calendar_api'),
    path('edit/<int:booking_id>/', views.edit_booking, name='edit_booking'),
    path('update-status/<int:booking_id>/', views.update_booking_status, name='update_booking_status'),
    path('api/update-booking/<int:booking_id>/', views.update_booking_ajax, name='update_booking_ajax'),
    path('api/update-notes/<int:booking_id>/', views.update_booking_notes, name='update_booking_notes'),
    path('api/delete-booking/<int:booking_id>/', views.delete_booking_ajax, name='delete_booking_ajax'),
    path('api/staff/<int:company_id>/<int:service_id>/', views.get_available_staff, name='get_available_staff'),
    path('api/dates/<int:company_id>/<int:staff_id>/', views.get_available_dates, name='get_available_dates'),
    path('api/times/<int:company_id>/<int:staff_id>/<int:service_id>/<str:date_str>/', views.get_available_times, name='get_available_times'),
    path('api/dates-any/<int:company_id>/<int:service_id>/', views.get_available_dates_any_staff, name='get_available_dates_any_staff'),
    path('api/times-any/<int:company_id>/<int:service_id>/<str:date_str>/', views.get_available_times_any_staff, name='get_available_times_any_staff'),
]
