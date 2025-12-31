from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_company, name='register_company'),
    path('activate/<uidb64>/<token>/', views.activate_company, name='activate_company'),
    path('dashboard/', views.company_dashboard, name='company_dashboard'),
    path('edit/', views.edit_company_profile, name='edit_company_profile'),
    path('delete-image/<int:image_id>/', views.delete_company_image, name='delete_company_image'),
    path('<int:company_id>/', views.company_public_page, name='company_public_page'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('services/', views.service_list, name='service_list'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/edit/<int:service_id>/', views.edit_service, name='edit_service'),
    path('services/delete/<int:service_id>/', views.delete_service, name='delete_service'),
    path('working-hours/', views.working_hours, name='working_hours'),
]
