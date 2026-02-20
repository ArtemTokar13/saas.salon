"""Webhook handlers for Stripe Connect events"""
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from companies.models import Company
from bookings.models import Booking
import stripe
import logging
import json

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_http_methods(["POST"])
def stripe_connect_webhook(request):
    """
    Handle Stripe Connect webhook events.
    
    Main events to handle:
    - checkout.session.completed: Payment succeeded
    - payment_intent.succeeded: Payment completed
    - payment_intent.payment_failed: Payment failed
    - charge.refunded: Payment refunded
    - account.updated: Connect account status changed
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    # Get webhook secret - you'll need to configure this
    webhook_secret = getattr(settings, 'STRIPE_CONNECT_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        logger.error("STRIPE_CONNECT_WEBHOOK_SECRET not configured")
        return HttpResponse(status=500)
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    
    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']
    
    logger.info(f"Received webhook event: {event_type}")
    
    # Route to appropriate handler
    if event_type == 'checkout.session.completed':
        handle_checkout_session_completed(event_data)
    elif event_type == 'payment_intent.succeeded':
        handle_payment_intent_succeeded(event_data)
    elif event_type == 'payment_intent.payment_failed':
        handle_payment_intent_failed(event_data)
    elif event_type == 'charge.refunded':
        handle_charge_refunded(event_data)
    elif event_type == 'account.updated':
        handle_account_updated(event_data)
    elif event_type == 'charge.succeeded':
        handle_charge_succeeded(event_data)
    else:
        logger.info(f"Unhandled event type: {event_type}")
    
    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """
    Handle successful checkout session completion.
    Update booking status and mark as paid.
    """
    try:
        # Get booking ID from metadata
        booking_id = session.get('metadata', {}).get('booking_id')
        
        if not booking_id:
            logger.error(f"No booking_id in session metadata: {session.id}")
            return
        
        # Get the booking
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            logger.error(f"Booking {booking_id} not found for session {session.id}")
            return
        
        # Get payment intent ID
        payment_intent_id = session.get('payment_intent')
        
        # Update booking
        booking.payment_status = 'paid'
        booking.stripe_payment_intent_id = payment_intent_id
        booking.paid_amount = session.get('amount_total', 0) / 100  # Convert from cents
        booking.paid_at = timezone.now()
        
        # Confirm the booking if it was pending payment
        if booking.status == 0:  # Pending
            booking.status = 1  # Confirmed
            booking.confirmed_at = timezone.now()
        
        booking.save()
        
        logger.info(f"Successfully processed payment for booking {booking_id}")
        
        # TODO: Send confirmation email to customer
        # TODO: Send notification to salon
        
    except Exception as e:
        logger.error(f"Error handling checkout.session.completed: {str(e)}")


def handle_payment_intent_succeeded(payment_intent):
    """
    Handle successful payment intent.
    This is a backup in case checkout.session.completed doesn't fire.
    """
    try:
        # Get booking by payment intent ID
        try:
            booking = Booking.objects.get(stripe_payment_intent_id=payment_intent['id'])
        except Booking.DoesNotExist:
            # This is okay - checkout.session.completed will handle it
            logger.info(f"No booking found for payment intent {payment_intent['id']}")
            return
        
        # Update if not already marked as paid
        if booking.payment_status != 'paid':
            booking.payment_status = 'paid'
            booking.paid_at = timezone.now()
            booking.paid_amount = payment_intent.get('amount', 0) / 100
            
            if booking.status == 0:  # Pending
                booking.status = 1  # Confirmed
                booking.confirmed_at = timezone.now()
            
            booking.save()
            logger.info(f"Updated booking {booking.id} from payment_intent.succeeded")
        
    except Exception as e:
        logger.error(f"Error handling payment_intent.succeeded: {str(e)}")


def handle_payment_intent_failed(payment_intent):
    """
    Handle failed payment intent.
    """
    try:
        # Try to find booking by session or payment intent
        booking = None
        
        # First try by payment intent ID
        try:
            booking = Booking.objects.get(stripe_payment_intent_id=payment_intent['id'])
        except Booking.DoesNotExist:
            pass
        
        if booking:
            booking.payment_status = 'failed'
            booking.save()
            logger.info(f"Marked booking {booking.id} payment as failed")
            
            # TODO: Send notification to customer about failed payment
        else:
            logger.info(f"No booking found for failed payment intent {payment_intent['id']}")
        
    except Exception as e:
        logger.error(f"Error handling payment_intent.payment_failed: {str(e)}")


def handle_charge_refunded(charge):
    """
    Handle refunded charge.
    """
    try:
        payment_intent_id = charge.get('payment_intent')
        
        if not payment_intent_id:
            logger.warning(f"No payment_intent in charge {charge['id']}")
            return
        
        # Find booking
        try:
            booking = Booking.objects.get(stripe_payment_intent_id=payment_intent_id)
        except Booking.DoesNotExist:
            logger.warning(f"No booking found for refunded charge {charge['id']}")
            return
        
        # Update booking
        booking.payment_status = 'refunded'
        booking.save()
        
        logger.info(f"Marked booking {booking.id} as refunded")
        
        # TODO: Send notification to customer about refund
        
    except Exception as e:
        logger.error(f"Error handling charge.refunded: {str(e)}")


def handle_charge_succeeded(charge):
    """
    Handle successful charge.
    Additional verification that payment went through.
    """
    try:
        payment_intent_id = charge.get('payment_intent')
        
        if not payment_intent_id:
            return
        
        # Try to find booking
        try:
            booking = Booking.objects.get(stripe_payment_intent_id=payment_intent_id)
        except Booking.DoesNotExist:
            return
        
        # Ensure marked as paid
        if booking.payment_status != 'paid':
            booking.payment_status = 'paid'
            booking.paid_at = timezone.now()
            booking.paid_amount = charge.get('amount', 0) / 100
            booking.save()
            logger.info(f"Updated booking {booking.id} from charge.succeeded")
        
    except Exception as e:
        logger.error(f"Error handling charge.succeeded: {str(e)}")


def handle_account_updated(account):
    """
    Handle Connect account updates.
    Update company's Stripe Connect status.
    """
    try:
        account_id = account['id']
        
        # Find company with this account
        try:
            company = Company.objects.get(stripe_account_id=account_id)
        except Company.DoesNotExist:
            logger.warning(f"No company found for account {account_id}")
            return
        
        # Update company status
        company.stripe_charges_enabled = account.get('charges_enabled', False)
        company.stripe_payouts_enabled = account.get('payouts_enabled', False)
        company.stripe_details_submitted = account.get('details_submitted', False)
        
        # Update onboarding status
        if company.stripe_charges_enabled and company.stripe_details_submitted:
            company.stripe_onboarding_completed = True
        else:
            company.stripe_onboarding_completed = False
        
        company.save()
        
        logger.info(f"Updated Stripe status for company {company.id}")
        
    except Exception as e:
        logger.error(f"Error handling account.updated: {str(e)}")


# Alternative webhook for standard platform subscriptions (existing functionality)
@csrf_exempt
@require_http_methods(["POST"])
def stripe_subscription_webhook(request):
    """
    Handle Stripe webhook events for platform subscriptions (not Connect).
    This is for your existing billing functionality.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)
    
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return HttpResponse(status=500)
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)
    
    # Handle subscription-specific events
    event_type = event['type']
    
    logger.info(f"Received subscription webhook: {event_type}")
    
    # Add your existing subscription webhook handlers here
    # invoice.paid, invoice.payment_failed, customer.subscription.deleted, etc.
    
    return HttpResponse(status=200)
