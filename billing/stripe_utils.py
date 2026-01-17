"""Stripe utility functions for billing"""
import stripe
from django.conf import settings
from decimal import Decimal
from .models import Plan, Subscription, Transaction

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_customer(company):
    """Create a Stripe customer for a company"""
    try:
        customer = stripe.Customer.create(
            email=company.email if hasattr(company, 'email') else '',
            name=company.name,
            metadata={
                'company_id': company.id,
            }
        )
        return customer
    except stripe.error.StripeError as e:
        raise Exception(f"Error creating Stripe customer: {str(e)}")


def create_stripe_checkout_session(company, plan, billing_period, success_url, cancel_url, num_workers=None):
    """Create a Stripe Checkout session for subscription"""
    try:
        if num_workers is None:
            num_workers = plan.base_workers
            
        # Get or create Stripe customer
        subscription = Subscription.objects.filter(company=company, is_active=True).first()
        
        if subscription and subscription.stripe_customer_id:
            customer_id = subscription.stripe_customer_id
        else:
            customer = create_stripe_customer(company)
            customer_id = customer.id
        
        # Get the Stripe Price ID for the billing period
        stripe_price_id = plan.get_stripe_price_id(billing_period)
        
        if not stripe_price_id:
            raise Exception(f"No Stripe Price ID configured for {plan.name} - {billing_period}")
        
        # Calculate line items
        line_items = [{
            'price': stripe_price_id,
            'quantity': 1,
        }]
        
        # Add additional workers if needed
        additional_workers = max(0, num_workers - plan.base_workers)
        if additional_workers > 0 and plan.stripe_additional_worker_price_id:
            line_items.append({
                'price': plan.stripe_additional_worker_price_id,
                'quantity': additional_workers,
            })
        
        # Prepare subscription data with trial period
        subscription_data = {}
        if plan.trial_days > 0:
            subscription_data['trial_period_days'] = plan.trial_days
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=line_items,
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data=subscription_data if subscription_data else None,
            metadata={
                'company_id': company.id,
                'plan_id': plan.id,
                'billing_period': billing_period,
                'num_workers': num_workers,
            }
        )
        
        return session
    except stripe.error.StripeError as e:
        raise Exception(f"Error creating Stripe checkout session: {str(e)}")


def cancel_stripe_subscription(subscription):
    """Cancel a Stripe subscription"""
    try:
        if subscription.stripe_subscription_id:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            return True
        return False
    except stripe.error.StripeError as e:
        raise Exception(f"Error cancelling Stripe subscription: {str(e)}")


def reactivate_stripe_subscription(subscription):
    """Reactivate a cancelled Stripe subscription"""
    try:
        if subscription.stripe_subscription_id:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            return True
        return False
    except stripe.error.StripeError as e:
        raise Exception(f"Error reactivating Stripe subscription: {str(e)}")


def create_customer_portal_session(customer_id, return_url):
    """Create a Stripe Customer Portal session"""
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session
    except stripe.error.StripeError as e:
        raise Exception(f"Error creating customer portal session: {str(e)}")


def sync_subscription_from_stripe(stripe_subscription_id):
    """Sync subscription data from Stripe"""
    try:
        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
        
        # Find the subscription in our database
        subscription = Subscription.objects.filter(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if subscription:
            # Map Stripe status to our status
            status_map = {
                'active': Subscription.STATUS_ACTIVE,
                'canceled': Subscription.STATUS_CANCELLED,
                'past_due': Subscription.STATUS_PAST_DUE,
                'unpaid': Subscription.STATUS_UNPAID,
            }
            
            subscription.status = status_map.get(stripe_sub.status, Subscription.STATUS_ACTIVE)
            subscription.is_active = stripe_sub.status == 'active'
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
            subscription.save()
            
        return subscription
    except stripe.error.StripeError as e:
        raise Exception(f"Error syncing subscription from Stripe: {str(e)}")
