"""Stripe utility functions for billing"""
import stripe
from django.conf import settings
from decimal import Decimal
from .models import Plan, Subscription, Transaction, StripeErrorLog
from datetime import timedelta, datetime
from django.utils import timezone
import uuid
from django.utils.translation import gettext as _

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_customer(company):
    """Create a Stripe customer for a company"""
    try:
        customer = stripe.Customer.create(
            email=getattr(company, 'email', ''),
            name=company.name,
            metadata={'company_id': company.id}
        )
        return customer
    except Exception as e:
        StripeErrorLog.log_error(
            function_name='create_stripe_customer',
            error=e,
            company=company,
            request_params={'email': getattr(company, 'email', ''), 'name': company.name}
        )
        raise


def create_stripe_checkout_session(company, plan, billing_period, success_url, cancel_url, num_workers=None):
    """Create a Stripe Checkout session for subscription"""
    try:
        if num_workers is None:
            num_workers = plan.base_workers

        total_price = plan.get_price_for_period(billing_period, num_workers)
        amount_cents = int(total_price * 100)

        months = {
            "monthly": 1,
            "three_months": 3,
            "six_months": 6,
            "yearly": 12,
        }[billing_period]

        product = stripe.Product.create(
            name=f"{plan.name} ({months} {_('months')})",
        )

        price_obj = stripe.Price.create(
            unit_amount=amount_cents,
            currency="eur",
            recurring={
                "interval": "month",
                "interval_count": months,
            },
            product=product.id,
        )

        customer = create_stripe_customer(company)

        session = stripe.checkout.Session.create(
            customer=customer.id,
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": price_obj.id,
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "company_id": company.id,
                "plan_id": plan.id,
                "billing_period": billing_period,
                "num_workers": num_workers,
            },
        )

        return session

    except Exception as e:
        StripeErrorLog.log_error(
            function_name='create_stripe_checkout_session',
            error=e,
            company=company,
            request_params={
                'plan_id': plan.id,
                'billing_period': billing_period,
                'num_workers': num_workers
            }
        )
        raise



def cancel_stripe_subscription(stripe_subscription_id):
    """Cancel a Stripe subscription"""
    subscription = None
    try:
        subscription = Subscription.objects.filter(stripe_subscription_id=stripe_subscription_id).first()
        stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
        return True
    except Exception as e:
        StripeErrorLog.log_error(
            function_name='cancel_stripe_subscription',
            error=e,
            company=subscription.company if subscription else None,
            subscription=subscription,
            request_params={'stripe_subscription_id': stripe_subscription_id}
        )
        raise


def reactivate_stripe_subscription(stripe_subscription_id):
    """Reactivate a cancelled Stripe subscription"""
    subscription = None
    try:
        subscription = Subscription.objects.filter(stripe_subscription_id=stripe_subscription_id).first()
        stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=False)
        return True
    except Exception as e:
        StripeErrorLog.log_error(
            function_name='reactivate_stripe_subscription',
            error=e,
            company=subscription.company if subscription else None,
            subscription=subscription,
            request_params={'stripe_subscription_id': stripe_subscription_id}
        )
        raise


def create_customer_portal_session(customer_id, return_url):
    """Create a Stripe Customer Portal session"""
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url
        )
        return session
    except Exception as e:
        StripeErrorLog.log_error(
            function_name='create_customer_portal_session',
            error=e,
            request_params={'customer_id': customer_id, 'return_url': return_url}
        )
        raise


def sync_subscription_from_stripe(stripe_subscription_id):
    """Sync subscription data from Stripe to local Subscription model"""
    subscription = None
    try:
        stripe_sub = stripe.Subscription.retrieve(stripe_subscription_id)
        subscription = Subscription.objects.filter(stripe_subscription_id=stripe_subscription_id).first()
        if subscription:
            status_map = {
                "active": Subscription.STATUS_ACTIVE,
                "canceled": Subscription.STATUS_CANCELLED,
                "past_due": Subscription.STATUS_PAST_DUE,
                "unpaid": Subscription.STATUS_UNPAID,
            }
            subscription.status = status_map.get(stripe_sub.status, Subscription.STATUS_ACTIVE)
            subscription.is_active = stripe_sub.status == "active"
            subscription.cancel_at_period_end = stripe_sub.cancel_at_period_end
            subscription.save()
        return subscription
    except Exception as e:
        StripeErrorLog.log_error(
            function_name='sync_subscription_from_stripe',
            error=e,
            company=subscription.company if subscription else None,
            subscription=subscription,
            request_params={'stripe_subscription_id': stripe_subscription_id}
        )
        raise
