from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import timedelta
import uuid
import stripe
import json
from .models import Plan, Subscription, Transaction
from .forms import ChangePlanForm
from .stripe_utils import (
    create_stripe_checkout_session, 
    cancel_stripe_subscription,
    reactivate_stripe_subscription,
    create_customer_portal_session,
    sync_subscription_from_stripe
)
from users.models import UserProfile

stripe.api_key = settings.STRIPE_SECRET_KEY


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
    """Change subscription plan with worker selection"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        new_plan = get_object_or_404(Plan, id=plan_id)
        
        if request.method == 'POST':
            billing_period = request.POST.get('billing_period', 'monthly')
            num_workers = int(request.POST.get('num_workers', new_plan.base_workers))
            
            # Validate worker count
            if num_workers < 1:
                messages.error(request, 'Number of workers must be at least 1.')
                return redirect('change_plan', plan_id=plan_id)
            
            # Store worker count in session for webhook handler
            request.session['subscription_workers'] = num_workers
            
            # Create Stripe checkout session
            success_url = request.build_absolute_uri('/billing/payment-success/')
            cancel_url = request.build_absolute_uri('/billing/plans/')
            
            try:
                session = create_stripe_checkout_session(
                    company=company,
                    plan=new_plan,
                    billing_period=billing_period,
                    success_url=success_url,
                    cancel_url=cancel_url,
                    num_workers=num_workers
                )
                
                # Redirect to Stripe Checkout
                return redirect(session.url, code=303)
            except Exception as e:
                messages.error(request, f'Error creating checkout session: {str(e)}')
                return redirect('view_plans')
        
        # GET request - show plan selection form
        context = {
            'plan': new_plan,
            'company': company,
            'billing_periods': Subscription.BILLING_PERIOD_CHOICES,
        }
        return render(request, 'billing/change_plan.html', context)
    
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
            subscription = Subscription.objects.filter(
                company=company,
                is_active=True
            ).first()
            
            if subscription:
                try:
                    # Cancel on Stripe
                    if subscription.stripe_subscription_id:
                        cancel_stripe_subscription(subscription)
                        subscription.cancel_at_period_end = True
                        subscription.save()
                        messages.success(request, 'Subscription will be cancelled at the end of the billing period.')
                    else:
                        # No Stripe subscription, just deactivate
                        subscription.is_active = False
                        subscription.status = Subscription.STATUS_CANCELLED
                        subscription.cancelled_at = timezone.now()
                        subscription.save()
                        messages.success(request, 'Subscription cancelled successfully.')
                except Exception as e:
                    messages.error(request, f'Error cancelling subscription: {str(e)}')
            else:
                messages.warning(request, 'No active subscription found.')
            
            return redirect('subscription_details')
        
        return render(request, 'billing/cancel_subscription.html', {'company': company})
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@login_required
def payment_success(request):
    """Handle successful payment"""
    messages.success(request, 'Payment successful! Your subscription has been activated.')
    return redirect('subscription_details')


@login_required
def payment_cancelled(request):
    """Handle cancelled payment"""
    messages.warning(request, 'Payment was cancelled.')
    return redirect('view_plans')


@login_required
def customer_portal(request):
    """Redirect to Stripe Customer Portal"""
    try:
        profile = request.user.userprofile
        if not profile.is_admin:
            messages.error(request, 'Access denied.')
            return redirect('home')
        
        company = profile.company
        subscription = Subscription.objects.filter(company=company, is_active=True).first()
        
        if not subscription or not subscription.stripe_customer_id:
            messages.error(request, 'No active subscription found.')
            return redirect('subscription_details')
        
        try:
            return_url = request.build_absolute_uri('/billing/subscription/')
            session = create_customer_portal_session(subscription.stripe_customer_id, return_url)
            return redirect(session.url, code=303)
        except Exception as e:
            messages.error(request, f'Error accessing customer portal: {str(e)}')
            return redirect('subscription_details')
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'User profile not found.')
        return redirect('home')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    
    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_invoice_payment_succeeded(invoice)
    
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)
    
    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """Handle completed checkout session"""
    try:
        company_id = session['metadata'].get('company_id')
        plan_id = session['metadata'].get('plan_id')
        billing_period = session['metadata'].get('billing_period', 'monthly')
        num_workers = int(session['metadata'].get('num_workers', 3))
        
        from companies.models import Company
        company = Company.objects.get(id=company_id)
        plan = Plan.objects.get(id=plan_id)
        
        # Retrieve subscription from Stripe
        stripe_subscription_id = session.get('subscription')
        stripe_customer_id = session.get('customer')
        
        # Get trial end date from Stripe subscription if exists
        trial_end_date = None
        if stripe_subscription_id:
            stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
            if stripe_sub.trial_end:
                from datetime import datetime
                trial_end_date = datetime.fromtimestamp(stripe_sub.trial_end).date()
        
        # Deactivate old subscriptions
        Subscription.objects.filter(company=company, is_active=True).update(is_active=False)
        
        # Calculate period dates
        start_date = timezone.now().date()
        period_days = {
            'monthly': 30,
            'three_months': 90,
            'six_months': 180,
            'yearly': 365,
        }
        end_date = start_date + timedelta(days=period_days.get(billing_period, 30))
        
        # Create new subscription
        subscription = Subscription.objects.create(
            company=company,
            plan=plan,
            billing_period=billing_period,
            num_workers=num_workers,
            start_date=start_date,
            end_date=end_date,
            trial_end=trial_end_date,
            is_active=True,
            status=Subscription.STATUS_ACTIVE,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )
        
        # Create transaction record (only if not in trial)
        if not trial_end_date or trial_end_date <= start_date:
            Transaction.objects.create(
                subscription=subscription,
                amount=plan.get_price_for_period(billing_period, num_workers),
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                payment_status=Transaction.PAYMENT_STATUS_SUCCEEDED,
                stripe_payment_intent_id=session.get('payment_intent'),
            )
        
    except Exception as e:
        print(f"Error handling checkout session completed: {str(e)}")


def handle_subscription_updated(stripe_subscription):
    """Handle subscription updated event"""
    try:
        sync_subscription_from_stripe(stripe_subscription['id'])
    except Exception as e:
        print(f"Error handling subscription updated: {str(e)}")


def handle_subscription_deleted(stripe_subscription):
    """Handle subscription deleted event"""
    try:
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_subscription['id']
        ).first()
        
        if subscription:
            subscription.is_active = False
            subscription.status = Subscription.STATUS_CANCELLED
            subscription.cancelled_at = timezone.now()
            subscription.save()
    except Exception as e:
        print(f"Error handling subscription deleted: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment"""
    try:
        stripe_subscription_id = invoice.get('subscription')
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if subscription:
            # Create transaction record
            Transaction.objects.create(
                subscription=subscription,
                amount=invoice['amount_paid'] / 100,  # Convert from cents
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                payment_status=Transaction.PAYMENT_STATUS_SUCCEEDED,
                stripe_invoice_id=invoice['id'],
                stripe_charge_id=invoice.get('charge'),
            )
            
            # Update subscription status
            subscription.status = Subscription.STATUS_ACTIVE
            subscription.is_active = True
            subscription.save()
    except Exception as e:
        print(f"Error handling invoice payment succeeded: {str(e)}")


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment"""
    try:
        stripe_subscription_id = invoice.get('subscription')
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = Subscription.STATUS_PAST_DUE
            subscription.save()
            
            # Create failed transaction record
            Transaction.objects.create(
                subscription=subscription,
                amount=invoice['amount_due'] / 100,  # Convert from cents
                transaction_id=f"TXN-{uuid.uuid4().hex[:12].upper()}",
                payment_status=Transaction.PAYMENT_STATUS_FAILED,
                stripe_invoice_id=invoice['id'],
            )
    except Exception as e:
        print(f"Error handling invoice payment failed: {str(e)}")
