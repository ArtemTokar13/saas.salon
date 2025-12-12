from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import uuid
from .models import Plan, Subscription, Transaction
from .forms import ChangePlanForm
from users.models import UserProfile


@login_required
def subscription_details(request):
    """View current subscription and billing history"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        
        # Get current subscription
        current_subscription = Subscription.objects.filter(
            company=company,
            is_active=True
        ).first()
        
        # Get all subscriptions history
        subscription_history = Subscription.objects.filter(
            company=company
        ).order_by('-start_date')
        
        # Get transaction history
        transactions = Transaction.objects.filter(
            subscription__company=company
        ).order_by('-transaction_date')
        
        context = {
            'company': company,
            'current_subscription': current_subscription,
            'subscription_history': subscription_history,
            'transactions': transactions,
        }
        
        return render(request, 'billing/subscription_details.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def view_plans(request):
    """View all available plans"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        
        # Get current subscription
        current_subscription = Subscription.objects.filter(
            company=company,
            is_active=True
        ).first()
        
        # Get all available plans
        plans = Plan.objects.all()
        
        context = {
            'company': company,
            'current_subscription': current_subscription,
            'plans': plans,
        }
        
        return render(request, 'billing/view_plans.html', context)
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def change_plan(request, plan_id):
    """Change subscription plan"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        new_plan = get_object_or_404(Plan, id=plan_id)
        
        # Deactivate current subscription
        Subscription.objects.filter(
            company=company,
            is_active=True
        ).update(is_active=False)
        
        # Create new subscription
        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)  # 30-day subscription
        
        new_subscription = Subscription.objects.create(
            company=company,
            plan=new_plan,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )
        
        # Create transaction record
        Transaction.objects.create(
            subscription=new_subscription,
            amount=new_plan.price,
            transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}"
        )
        
        messages.success(request, f'Successfully switched to {new_plan.name} plan!')
        return redirect('subscription_details')
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def cancel_subscription(request):
    """Cancel active subscription"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        
        if request.method == 'POST':
            # Deactivate current subscription
            updated = Subscription.objects.filter(
                company=company,
                is_active=True
            ).update(is_active=False)
            
            if updated:
                messages.success(request, 'Subscription cancelled successfully.')
            else:
                messages.warning(request, 'No active subscription found.')
            
            return redirect('subscription_details')
        
        return render(request, 'billing/cancel_subscription.html', {'company': company})
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')
