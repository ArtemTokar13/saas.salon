from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView
from django.urls import reverse

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    
    def get_success_url(self):
        # Redirect superusers to platform admin, others to company dashboard
        if self.request.user.is_superuser or self.request.user.is_staff:
            return reverse('admin_dashboard')
        return reverse('company_dashboard')
