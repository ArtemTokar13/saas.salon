"""Stripe Connect utility functions for salon payments"""
import stripe
from django.conf import settings
from decimal import Decimal
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_connect_account(company):
    """
    Create a Stripe Connect Express account for a salon/company.
    
    Args:
        company: Company model instance
        
    Returns:
        dict: {'account_id': str, 'success': bool, 'error': str or None}
    """
    try:
        account = stripe.Account.create(
            type='express',  # Use 'standard' for Standard accounts
            country='ES',  # Adjust based on your needs or company location
            email=company.email or company.administrator.email,
            capabilities={
                'card_payments': {'requested': True},
                'transfers': {'requested': True},
            },
            business_type='company',
            business_profile={
                'name': company.name,
                'url': company.website if company.website else None,
            },
            metadata={
                'company_id': company.id,
                'company_name': company.name,
            }
        )
        
        # Save the account ID to the company
        company.stripe_account_id = account.id
        company.save(update_fields=['stripe_account_id'])
        
        logger.info(f"Created Stripe Connect account {account.id} for company {company.id}")
        
        return {
            'account_id': account.id,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create Stripe Connect account for company {company.id}: {str(e)}")
        return {
            'account_id': None,
            'success': False,
            'error': str(e)
        }


def create_account_link(account_id, refresh_url, return_url):
    """
    Create an Account Link for onboarding or updating account information.
    
    Args:
        account_id: Stripe Connect account ID
        refresh_url: URL to redirect if link expires
        return_url: URL to redirect after completion
        
    Returns:
        dict: {'url': str, 'success': bool, 'error': str or None}
    """
    try:
        account_link = stripe.AccountLink.create(
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type='account_onboarding',
        )
        
        return {
            'url': account_link.url,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create account link for {account_id}: {str(e)}")
        return {
            'url': None,
            'success': False,
            'error': str(e)
        }


def check_account_status(account_id):
    """
    Check the status of a Stripe Connect account.
    
    Args:
        account_id: Stripe Connect account ID
        
    Returns:
        dict: {
            'charges_enabled': bool,
            'payouts_enabled': bool,
            'details_submitted': bool,
            'success': bool,
            'error': str or None
        }
    """
    try:
        account = stripe.Account.retrieve(account_id)
        
        return {
            'charges_enabled': account.charges_enabled,
            'payouts_enabled': account.payouts_enabled,
            'details_submitted': account.details_submitted,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve account status for {account_id}: {str(e)}")
        return {
            'charges_enabled': False,
            'payouts_enabled': False,
            'details_submitted': False,
            'success': False,
            'error': str(e)
        }


def create_checkout_session_for_booking(booking, success_url, cancel_url):
    """
    Create a Stripe Checkout Session for a booking payment.
    Payment goes directly to the salon's Stripe Connect account.
    
    Args:
        booking: Booking model instance
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect if payment is cancelled
        
    Returns:
        dict: {'session_id': str, 'url': str, 'success': bool, 'error': str or None}
    """
    try:
        company = booking.company
        
        # Check if company has a connected Stripe account
        if not company.stripe_account_id:
            return {
                'session_id': None,
                'url': None,
                'success': False,
                'error': 'Company does not have a Stripe account connected'
            }
        
        if not company.stripe_charges_enabled:
            return {
                'session_id': None,
                'url': None,
                'success': False,
                'error': 'Company Stripe account is not enabled for charges'
            }
        
        # Calculate amount in cents
        amount = booking.price if booking.price else booking.service.price
        amount_cents = int(amount * 100)
        
        # Create checkout session
        # Key point: use stripe_account parameter to charge the Connect account
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',  # Adjust based on your currency
                    'unit_amount': amount_cents,
                    'product_data': {
                        'name': booking.service.name,
                        'description': f"{booking.service.name} - {booking.company.name}",
                    },
                },
                'quantity': 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=booking.customer.email if booking.customer.email else None,
            metadata={
                'booking_id': booking.id,
                'company_id': company.id,
                'customer_name': booking.customer.name,
                'service_name': booking.service.name,
            },
            # CRITICAL: This ensures payment goes to the salon's account
            stripe_account=company.stripe_account_id,
            # Optional: If you want to charge an application fee (platform revenue)
            # payment_intent_data={
            #     'application_fee_amount': 0,  # Amount in cents (e.g., 500 = €5)
            # },
        )
        
        # Save session ID to booking
        booking.stripe_checkout_session_id = session.id
        booking.payment_required = True
        booking.save(update_fields=['stripe_checkout_session_id', 'payment_required'])
        
        logger.info(f"Created checkout session {session.id} for booking {booking.id}")
        
        return {
            'session_id': session.id,
            'url': session.url,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create checkout session for booking {booking.id}: {str(e)}")
        return {
            'session_id': None,
            'url': None,
            'success': False,
            'error': str(e)
        }


def retrieve_checkout_session(session_id, stripe_account_id):
    """
    Retrieve a Stripe Checkout Session.
    
    Args:
        session_id: Stripe Checkout Session ID
        stripe_account_id: Stripe Connect account ID
        
    Returns:
        dict: {'session': object, 'success': bool, 'error': str or None}
    """
    try:
        session = stripe.checkout.Session.retrieve(
            session_id,
            stripe_account=stripe_account_id
        )
        
        return {
            'session': session,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve checkout session {session_id}: {str(e)}")
        return {
            'session': None,
            'success': False,
            'error': str(e)
        }


def create_refund(payment_intent_id, stripe_account_id, amount=None, reason=None):
    """
    Create a refund for a payment.
    
    Args:
        payment_intent_id: Stripe Payment Intent ID
        stripe_account_id: Stripe Connect account ID
        amount: Amount to refund in cents (None = full refund)
        reason: Reason for refund ('duplicate', 'fraudulent', 'requested_by_customer')
        
    Returns:
        dict: {'refund_id': str, 'success': bool, 'error': str or None}
    """
    try:
        refund_params = {
            'payment_intent': payment_intent_id,
        }
        
        if amount:
            refund_params['amount'] = amount
            
        if reason:
            refund_params['reason'] = reason
        
        refund = stripe.Refund.create(
            **refund_params,
            stripe_account=stripe_account_id
        )
        
        logger.info(f"Created refund {refund.id} for payment intent {payment_intent_id}")
        
        return {
            'refund_id': refund.id,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create refund for payment intent {payment_intent_id}: {str(e)}")
        return {
            'refund_id': None,
            'success': False,
            'error': str(e)
        }


def create_login_link(account_id):
    """
    Create a login link for a Connect account to access their Stripe Dashboard.
    
    Args:
        account_id: Stripe Connect account ID
        
    Returns:
        dict: {'url': str, 'success': bool, 'error': str or None}
    """
    try:
        login_link = stripe.Account.create_login_link(account_id)
        
        return {
            'url': login_link.url,
            'success': True,
            'error': None
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create login link for {account_id}: {str(e)}")
        return {
            'url': None,
            'success': False,
            'error': str(e)
        }
