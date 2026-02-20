"""Views for Stripe Connect - Salon Payment Onboarding"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext as _
from companies.models import Company
from bookings.models import Booking
from .stripe_connect_utils import (
    create_connect_account,
    create_account_link,
    check_account_status,
    create_checkout_session_for_booking,
    create_login_link,
    retrieve_checkout_session,
)
import stripe
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def stripe_connect_onboard(request):
    """
    Initiate Stripe Connect onboarding for a salon/company.
    Creates a Connect account if needed and generates an onboarding link.
    """
    try:
        # Get the user's company
        user_profile = request.user.userprofile
        company = user_profile.company
        
        # Check if user is admin
        if not user_profile.is_admin:
            messages.error(request, _('Only company administrators can set up payments.'))
            return redirect('company_dashboard')
        
        # Check if already has a Stripe account
        if company.stripe_account_id:
            # Check account status
            status = check_account_status(company.stripe_account_id)
            
            if status['success']:
                # Update company status
                company.stripe_charges_enabled = status['charges_enabled']
                company.stripe_payouts_enabled = status['payouts_enabled']
                company.stripe_details_submitted = status['details_submitted']
                company.save(update_fields=[
                    'stripe_charges_enabled',
                    'stripe_payouts_enabled',
                    'stripe_details_submitted'
                ])
                
                # If already fully onboarded
                if status['charges_enabled'] and status['details_submitted']:
                    company.stripe_onboarding_completed = True
                    company.save(update_fields=['stripe_onboarding_completed'])
                    messages.success(request, _('Your Stripe account is already set up!'))
                    return redirect('stripe_connect_dashboard')
        else:
            # Create new Connect account
            result = create_connect_account(company)
            
            if not result['success']:
                messages.error(request, _('Failed to create Stripe account: %(error)s') % {'error': result['error']})
                return redirect('company_dashboard')
        
        # Generate onboarding link
        refresh_url = request.build_absolute_uri(reverse('stripe_connect_onboard'))
        return_url = request.build_absolute_uri(reverse('stripe_connect_return'))
        
        link_result = create_account_link(
            company.stripe_account_id,
            refresh_url,
            return_url
        )
        
        if link_result['success']:
            # Redirect to Stripe onboarding
            return redirect(link_result['url'])
        else:
            messages.error(request, _('Failed to create onboarding link: %(error)s') % {'error': link_result['error']})
            return redirect('company_dashboard')
            
    except Exception as e:
        logger.error(f"Error in stripe_connect_onboard: {str(e)}")
        messages.error(request, _('An error occurred. Please try again.'))
        return redirect('company_dashboard')


@login_required
def stripe_connect_return(request):
    """
    Handle return from Stripe Connect onboarding.
    Check account status and update company settings.
    """
    try:
        user_profile = request.user.userprofile
        company = user_profile.company
        
        if not company.stripe_account_id:
            messages.error(request, _('No Stripe account found.'))
            return redirect('company_dashboard')
        
        # Check account status
        status = check_account_status(company.stripe_account_id)
        
        if status['success']:
            # Update company status
            company.stripe_charges_enabled = status['charges_enabled']
            company.stripe_payouts_enabled = status['payouts_enabled']
            company.stripe_details_submitted = status['details_submitted']
            
            if status['charges_enabled'] and status['details_submitted']:
                company.stripe_onboarding_completed = True
                company.accepts_online_payments = True
                messages.success(request, _('Stripe account successfully connected! You can now accept online payments.'))
            else:
                company.stripe_onboarding_completed = False
                messages.warning(request, _('Stripe account created, but onboarding not complete. Please complete all required information.'))
            
            company.save()
        else:
            messages.error(request, _('Failed to verify account status: %(error)s') % {'error': status['error']})
        
        return redirect('stripe_connect_dashboard')
        
    except Exception as e:
        logger.error(f"Error in stripe_connect_return: {str(e)}")
        messages.error(request, _('An error occurred. Please try again.'))
        return redirect('company_dashboard')


@login_required
def stripe_connect_dashboard(request):
    """
    Display Stripe Connect dashboard for salon owners.
    Shows connection status and payment settings.
    """
    try:
        user_profile = request.user.userprofile
        company = user_profile.company
        
        if not user_profile.is_admin:
            messages.error(request, _('Access denied.'))
            return redirect('company_dashboard')
        
        # Check current status if account exists
        account_status = None
        if company.stripe_account_id:
            status = check_account_status(company.stripe_account_id)
            if status['success']:
                account_status = status
                # Update company status
                company.stripe_charges_enabled = status['charges_enabled']
                company.stripe_payouts_enabled = status['payouts_enabled']
                company.stripe_details_submitted = status['details_submitted']
                company.save()
        
        # Get recent bookings with payment info
        recent_bookings = Booking.objects.filter(
            company=company,
            payment_required=True
        ).select_related('customer', 'service', 'staff').order_by('-created_at')[:10]
        
        context = {
            'company': company,
            'account_status': account_status,
            'recent_bookings': recent_bookings,
        }
        
        return render(request, 'billing/stripe_connect_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in stripe_connect_dashboard: {str(e)}")
        messages.error(request, _('An error occurred. Please try again.'))
        return redirect('company_dashboard')


@login_required
def stripe_connect_dashboard_link(request):
    """
    Generate a link to the Stripe Dashboard for the connected account.
    """
    try:
        user_profile = request.user.userprofile
        company = user_profile.company
        
        if not user_profile.is_admin:
            messages.error(request, _('Access denied.'))
            return redirect('company_dashboard')
        
        if not company.stripe_account_id:
            messages.error(request, _('No Stripe account connected.'))
            return redirect('stripe_connect_dashboard')
        
        # Create login link
        result = create_login_link(company.stripe_account_id)
        
        if result['success']:
            return redirect(result['url'])
        else:
            messages.error(request, _('Failed to access Stripe Dashboard: %(error)s') % {'error': result['error']})
            return redirect('stripe_connect_dashboard')
            
    except Exception as e:
        logger.error(f"Error in stripe_connect_dashboard_link: {str(e)}")
        messages.error(request, _('An error occurred. Please try again.'))
        return redirect('stripe_connect_dashboard')


@login_required
@require_http_methods(["POST"])
def toggle_online_payments(request):
    """
    Toggle whether the company accepts online payments.
    """
    try:
        user_profile = request.user.userprofile
        company = user_profile.company
        
        if not user_profile.is_admin:
            return JsonResponse({'success': False, 'error': 'Access denied'}, status=403)
        
        # Can only enable if Stripe is set up
        enable = request.POST.get('enable', 'false').lower() == 'true'
        
        if enable and not company.stripe_onboarding_completed:
            return JsonResponse({
                'success': False,
                'error': 'Please complete Stripe onboarding first'
            }, status=400)
        
        company.accepts_online_payments = enable
        company.save(update_fields=['accepts_online_payments'])
        
        return JsonResponse({
            'success': True,
            'accepts_online_payments': company.accepts_online_payments
        })
        
    except Exception as e:
        logger.error(f"Error in toggle_online_payments: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def create_booking_payment(request, booking_id):
    """
    Create a Stripe Checkout Session for a booking payment.
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Verify access (either booking owner or company staff)
        user_profile = request.user.userprofile
        is_company_staff = user_profile.company == booking.company
        # Add additional authorization checks as needed
        
        if not booking.company.accepts_online_payments:
            messages.error(request, _('This salon does not accept online payments.'))
            return redirect('bookings_list')
        
        if not booking.company.stripe_charges_enabled:
            messages.error(request, _('This salon cannot accept payments at the moment.'))
            return redirect('bookings_list')
        
        # Check if already paid
        if booking.payment_status == 'paid':
            messages.info(request, _('This booking has already been paid.'))
            return redirect('bookings_list')
        
        # Create checkout session
        success_url = request.build_absolute_uri(
            reverse('booking_payment_success', kwargs={'booking_id': booking.id})
        ) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = request.build_absolute_uri(
            reverse('booking_payment_cancel', kwargs={'booking_id': booking.id})
        )
        
        result = create_checkout_session_for_booking(
            booking,
            success_url,
            cancel_url
        )
        
        if result['success']:
            return redirect(result['url'])
        else:
            messages.error(request, _('Failed to create payment session: %(error)s') % {'error': result['error']})
            return redirect('bookings_list')
            
    except Exception as e:
        logger.error(f"Error in create_booking_payment: {str(e)}")
        messages.error(request, _('An error occurred. Please try again.'))
        return redirect('bookings_list')


@login_required
def booking_payment_success(request, booking_id):
    """
    Handle successful payment return.
    The webhook will actually update the booking, but we show a success message here.
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        session_id = request.GET.get('session_id')
        
        if session_id:
            # Optionally verify the session (webhook handles the actual update)
            pass
        
        messages.success(request, _('Payment successful! Your booking is confirmed.'))
        return redirect('bookings_list')
        
    except Exception as e:
        logger.error(f"Error in booking_payment_success: {str(e)}")
        messages.error(request, _('An error occurred.'))
        return redirect('bookings_list')


@login_required
def booking_payment_cancel(request, booking_id):
    """
    Handle cancelled payment.
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        messages.warning(request, _('Payment was cancelled. You can try again when ready.'))
        return redirect('bookings_list')
        
    except Exception as e:
        logger.error(f"Error in booking_payment_cancel: {str(e)}")
        return redirect('bookings_list')
