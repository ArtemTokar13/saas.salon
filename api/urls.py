from django.urls import path
from . import views

urlpatterns = [
    # Existing endpoints
    path('get_plan_price/', views.get_plan_price, name='get_plan_price'),
    
    # Auth endpoints
    path('auth/login/', views.auth_login, name='api_login'),
    path('auth/register/', views.auth_register, name='api_register'),
    path('auth/logout/', views.auth_logout, name='api_logout'),
    path('auth/user/', views.get_user, name='api_user'),
    
    # Booking endpoints
    path('bookings/', views.bookings_list, name='api_bookings_list'),
    path('bookings/<int:id>/', views.booking_detail, name='api_booking_detail'),
    
    # Company endpoints
    path('companies/', views.companies_list, name='api_companies_list'),
    path('companies/<int:id>/', views.company_detail, name='api_company_detail'),
    path('companies/<int:id>/services/', views.company_services, name='api_company_services'),
    path('companies/<int:id>/staff/', views.company_staff, name='api_company_staff'),
    path('companies/<int:id>/bookings/', views.company_bookings, name='api_company_bookings'),
    
    # Service endpoints
    path('services/', views.services_list, name='api_services_list'),
]