from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Q
from companies.models import Company, Staff, Service
from bookings.models import Booking, Customer
from billing.models import Plan, Subscription, Transaction
from users.models import UserProfile
from users.models import DailyVisit


def is_superuser(user):
    return user.is_superuser or user.is_staff


@login_required
@user_passes_test(is_superuser)
def admin_dashboard(request):
    """Super admin dashboard to manage entire platform"""
    
    # Statistics
    total_users = User.objects.count()
    total_companies = Company.objects.count()
    total_bookings = Booking.objects.count()
    total_revenue = Transaction.objects.aggregate(Sum('amount'))['amount__sum'] or 0

    # Visits
    total_visits = DailyVisit.objects.count()
    today_visits = DailyVisit.objects.filter(date=date.today()).count()
    
    # Recent activity
    recent_companies = Company.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_joined')[:10]
    recent_bookings = Booking.objects.select_related('company', 'customer', 'service').order_by('-created_at')[:10]
    recent_transactions = Transaction.objects.select_related('subscription__company', 'subscription__plan').order_by('-transaction_date')[:10]
    
    # Active subscriptions
    active_subscriptions = Subscription.objects.filter(is_active=True).select_related('company', 'plan')
    
    # Plans statistics
    plans = Plan.objects.annotate(
        subscription_count=Count('subscription', filter=Q(subscription__is_active=True))
    )
    
    context = {
        'total_users': total_users,
        'total_companies': total_companies,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'recent_companies': recent_companies,
        'recent_users': recent_users,
        'recent_bookings': recent_bookings,
        'recent_transactions': recent_transactions,
        'active_subscriptions': active_subscriptions,
        'plans': plans,
        'total_visits': total_visits,
        'today_visits': today_visits,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_users(request):
    """View and manage all users"""
    users = User.objects.select_related('userprofile').order_by('-date_joined')
    
    context = {
        'users': users,
    }
    
    return render(request, 'admin_dashboard/manage_users.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_companies(request):
    """View and manage all companies"""
    companies = Company.objects.select_related('administrator').annotate(
        staff_count=Count('staff'),
        service_count=Count('service'),
        booking_count=Count('booking')
    ).order_by('-created_at')
    
    context = {
        'companies': companies,
    }
    
    return render(request, 'admin_dashboard/manage_companies.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_plans(request):
    """View and manage billing plans"""
    plans = Plan.objects.filter(is_active=True).order_by('base_monthly_price')
    
    context = {
        'plans': plans,
    }
    
    return render(request, 'admin_dashboard/manage_plans.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_subscriptions(request):
    """View all subscriptions"""
    subscriptions = Subscription.objects.select_related('company', 'plan').order_by('-start_date')
    
    # Filter options
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        subscriptions = subscriptions.filter(is_active=True)
    elif status_filter == 'inactive':
        subscriptions = subscriptions.filter(is_active=False)
    
    context = {
        'subscriptions': subscriptions,
        'status_filter': status_filter,
    }
    
    return render(request, 'admin_dashboard/manage_subscriptions.html', context)
