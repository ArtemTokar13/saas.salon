from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Company, Staff, Service, WorkingHours, CompanyImage
from .forms import CompanyRegistrationForm, CompanyProfileForm
from billing.models import Subscription
from users.models import UserProfile


def register_company(request):
    """Company registration with user creation and subscription"""
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )
            
            company = Company.objects.create(
                administrator=user,
                name=form.cleaned_data['company_name'],
                description=form.cleaned_data.get('company_description', ''),
                address=form.cleaned_data['company_address'],
                city=form.cleaned_data['company_city'],
                phone=form.cleaned_data.get('company_phone', ''),
                email=form.cleaned_data.get('company_email', ''),
                logo=form.cleaned_data.get('company_logo')
            )
            
            UserProfile.objects.create(
                user=user,
                company=company,
                is_admin=True
            )
            
            login(request, user)
            messages.success(request, 'Company registered successfully!')
            return redirect('company_dashboard')
    else:
        form = CompanyRegistrationForm()
    
    return render(request, 'companies/register.html', {'form': form})


@login_required
def company_dashboard(request):
    """Dashboard for company administrators"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        staff_count = Staff.objects.filter(company=company).count()
        service_count = Service.objects.filter(company=company).count()
        
        # Get active subscription
        subscription = Subscription.objects.filter(
            company=company, 
            is_active=True
        ).first()
        
        context = {
            'company': company,
            'staff_count': staff_count,
            'service_count': service_count,
            'subscription': subscription,
        }
        
        return render(request, 'companies/dashboard.html', context)
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def edit_company_profile(request):
    """Edit company profile"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        
        if request.method == 'POST':
            form = CompanyProfileForm(request.POST, request.FILES, instance=company)
            if form.is_valid():
                form.save()
                messages.success(request, 'Company profile updated successfully!')
                return redirect('company_dashboard')
        else:
            form = CompanyProfileForm(instance=company)
        
        return render(request, 'companies/edit_profile.html', {'form': form, 'company': company})
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


def company_public_page(request, company_id):
    """Public-facing company page for customers"""
    company = get_object_or_404(Company, id=company_id)
    staff = Staff.objects.filter(company=company, is_active=True)
    services = Service.objects.filter(company=company, active=True)
    working_hours = WorkingHours.objects.filter(company=company).order_by('day_of_week')
    images = CompanyImage.objects.filter(company=company)
    
    context = {
        'company': company,
        'staff': staff,
        'services': services,
        'working_hours': working_hours,
        'images': images,
    }
    
    return render(request, 'companies/public_page.html', context)
