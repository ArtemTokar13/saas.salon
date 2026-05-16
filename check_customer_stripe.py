#!/usr/bin/env python
"""
Script to check Stripe customer and subscription details
Usage: python check_customer_stripe.py <customer_email>
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

import stripe
from django.conf import settings
from billing.models import Subscription
from users.models import Company

stripe.api_key = settings.STRIPE_SECRET_KEY


def check_customer(email):
    """Check customer details in Stripe"""
    print(f"🔍 Searching for customer: {email}")
    print("=" * 60)
    
    # Find company by email
    try:
        company = Company.objects.get(email=email)
        print(f"✅ Company found: {company.name} (ID: {company.id})")
    except Company.DoesNotExist:
        print(f"❌ No company found with email: {email}")
        return
    
    # Find subscription
    subscription = Subscription.objects.filter(company=company, is_active=True).first()
    if not subscription:
        print("❌ No active subscription found")
        all_subs = Subscription.objects.filter(company=company).order_by('-created_at')
        if all_subs:
            print(f"\n📋 Found {all_subs.count()} inactive subscriptions:")
            for sub in all_subs[:3]:
                print(f"  - Status: {sub.status}, Stripe ID: {sub.stripe_subscription_id}")
        return
    
    print(f"✅ Active subscription found:")
    print(f"   - Status: {subscription.status}")
    print(f"   - Plan: {subscription.plan.name}")
    print(f"   - Period: {subscription.billing_period}")
    print(f"   - End date: {subscription.end_date}")
    print(f"   - Stripe Sub ID: {subscription.stripe_subscription_id}")
    print(f"   - Stripe Customer ID: {subscription.stripe_customer_id}")
    
    if not subscription.stripe_customer_id:
        print("❌ No Stripe customer ID found")
        return
    
    print("\n" + "=" * 60)
    print("🔍 Fetching Stripe customer details...")
    print("=" * 60)
    
    # Fetch Stripe customer
    try:
        customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
        print(f"✅ Customer: {customer.email}")
        print(f"   - ID: {customer.id}")
        print(f"   - Created: {customer.created}")
        
        # Check payment methods
        payment_methods = stripe.PaymentMethod.list(
            customer=customer.id,
            type='card'
        )
        
        print(f"\n💳 Payment Methods ({len(payment_methods.data)}):")
        for pm in payment_methods.data:
            card = pm.card
            print(f"   - {card.brand.upper()} •••• {card.last4}")
            print(f"     Expires: {card.exp_month}/{card.exp_year}")
            print(f"     Country: {card.country}")
            print(f"     Funding: {card.funding}")  # debit/credit
            if hasattr(card, 'cvc_check') and card.cvc_check:
                print(f"     CVC check: {card.cvc_check}")
            if hasattr(card, 'three_d_secure_usage') and card.three_d_secure_usage:
                print(f"     3D Secure: {card.three_d_secure_usage.supported}")
            print(f"     ID: {pm.id}")
        
        # Check default payment method
        if customer.invoice_settings.default_payment_method:
            print(f"\n✅ Default payment method: {customer.invoice_settings.default_payment_method}")
        else:
            print(f"\n⚠️  No default payment method set")
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")
        return
    
    # Fetch Stripe subscription
    print("\n" + "=" * 60)
    print("🔍 Fetching Stripe subscription details...")
    print("=" * 60)
    
    try:
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        print(f"✅ Subscription: {stripe_sub.id}")
        print(f"   - Status: {stripe_sub.status}")
        print(f"   - Current period: {stripe_sub.current_period_start} - {stripe_sub.current_period_end}")
        print(f"   - Cancel at period end: {stripe_sub.cancel_at_period_end}")
        
        # Check latest invoice
        if stripe_sub.latest_invoice:
            invoice = stripe.Invoice.retrieve(stripe_sub.latest_invoice)
            print(f"\n📄 Latest Invoice:")
            print(f"   - Status: {invoice.status}")
            print(f"   - Amount: €{invoice.amount_due / 100:.2f}")
            print(f"   - Paid: {invoice.paid}")
            print(f"   - Attempt count: {invoice.attempt_count}")
            
            if invoice.payment_intent:
                payment_intent = stripe.PaymentIntent.retrieve(invoice.payment_intent)
                print(f"\n💰 Payment Intent: {payment_intent.id}")
                print(f"   - Status: {payment_intent.status}")
                print(f"   - Amount: €{payment_intent.amount / 100:.2f}")
                
                if payment_intent.last_payment_error:
                    error = payment_intent.last_payment_error
                    print(f"\n❌ Last Payment Error:")
                    print(f"   - Code: {error.code}")
                    print(f"   - Decline code: {error.decline_code}")
                    print(f"   - Message: {error.message}")
                    print(f"   - Payment method: {error.payment_method.id if error.payment_method else 'N/A'}")
        
        # Check payment settings
        print(f"\n⚙️  Subscription payment settings:")
        print(f"   - Default payment method: {stripe_sub.default_payment_method}")
        print(f"   - Collection method: {stripe_sub.collection_method}")
        print(f"   - Days until due: {stripe_sub.days_until_due}")
        
    except stripe.error.StripeError as e:
        print(f"❌ Stripe error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_customer_stripe.py <customer_email>")
        print("Example: python check_customer_stripe.py herasimovahanna@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    check_customer(email)
