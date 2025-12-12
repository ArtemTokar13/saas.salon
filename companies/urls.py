from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_company, name='register_company'),
    path('dashboard/', views.company_dashboard, name='company_dashboard'),
    path('edit/', views.edit_company_profile, name='edit_company_profile'),
    path('<int:company_id>/', views.company_public_page, name='company_public_page'),
]
