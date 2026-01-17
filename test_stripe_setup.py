#!/usr/bin/env python
"""
Test script to verify Stripe billing integration setup
Run: python test_stripe_setup.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.conf import settings
from billing.models import Plan, Subscription, Transaction
import stripe

def test_configuration():
    """Test Stripe configuration"""
    print("\n🔍 Testing Stripe Configuration...")
    
    checks = {
        'STRIPE_PUBLIC_KEY': bool(settings.STRIPE_PUBLIC_KEY),
        'STRIPE_SECRET_KEY': bool(settings.STRIPE_SECRET_KEY),
        'STRIPE_WEBHOOK_SECRET': bool(settings.STRIPE_WEBHOOK_SECRET),
    }
    
    all_ok = True
    for key, value in checks.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {'Configured' if value else 'NOT CONFIGURED'}")
        if not value:
            all_ok = False
    
    return all_ok


def test_stripe_connection():
    """Test connection to Stripe API"""
    print("\n🔍 Testing Stripe API Connection...")
    
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        # Test API connection
        balance = stripe.Balance.retrieve()
        print(f"  ✅ Connected to Stripe successfully")
        print(f"  💰 Account currency: {balance.available[0].currency.upper()}")
        print(f"  🏦 Available balance: {balance.available[0].amount / 100}")
        return True
    except stripe.error.AuthenticationError:
        print("  ❌ Authentication failed - check your STRIPE_SECRET_KEY")
        return False
    except Exception as e:
        print(f"  ❌ Connection failed: {str(e)}")
        return False


def test_database_models():
    """Test database models"""
    print("\n🔍 Testing Database Models...")
    
    try:
        plan_count = Plan.objects.count()
        subscription_count = Subscription.objects.count()
        transaction_count = Transaction.objects.count()
        
        print(f"  ✅ Plans: {plan_count}")
        print(f"  ✅ Subscriptions: {subscription_count}")
        print(f"  ✅ Transactions: {transaction_count}")
        
        if plan_count == 0:
            print("  ⚠️  No plans found. Create plans in Django admin.")
        
        return True
    except Exception as e:
        print(f"  ❌ Database error: {str(e)}")
        return False


def test_plan_stripe_configuration():
    """Test if plans are configured with Stripe"""
    print("\n🔍 Testing Plan Stripe Configuration...")
    
    plans = Plan.objects.filter(is_active=True)
    
    if not plans.exists():
        print("  ⚠️  No active plans found")
        return False
    
    all_configured = True
    for plan in plans:
        has_product = bool(plan.stripe_product_id)
        has_monthly = bool(plan.stripe_price_id_monthly)
        has_all_prices = all([
            plan.stripe_price_id_monthly,
            plan.stripe_price_id_three_months,
            plan.stripe_price_id_six_months,
            plan.stripe_price_id_yearly,
        ])
        
        status = "✅" if has_all_prices else "⚠️" if has_product else "❌"
        print(f"  {status} {plan.name}")
        
        if not has_product:
            print(f"      ❌ Missing Stripe Product ID")
            all_configured = False
        elif not has_all_prices:
            print(f"      ⚠️  Missing some Price IDs")
            all_configured = False
        else:
            print(f"      ✅ Fully configured")
    
    if not all_configured:
        print("\n  💡 Run: python manage.py sync_stripe_plans")
    
    return all_configured


def test_stripe_products():
    """Test if Stripe products exist"""
    print("\n🔍 Testing Stripe Products...")
    
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        
        plans = Plan.objects.filter(is_active=True, stripe_product_id__isnull=False)
        
        if not plans.exists():
            print("  ⚠️  No plans with Stripe Product IDs")
            return False
        
        all_ok = True
        for plan in plans:
            try:
                product = stripe.Product.retrieve(plan.stripe_product_id)
                status = "✅" if product.active else "⚠️"
                print(f"  {status} {plan.name} - {product.name}")
            except stripe.error.InvalidRequestError:
                print(f"  ❌ {plan.name} - Product not found in Stripe")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def print_next_steps():
    """Print next steps for setup"""
    print("\n📝 Next Steps:")
    print("\n1. Configure Stripe Keys:")
    print("   - Get keys from https://dashboard.stripe.com/test/apikeys")
    print("   - Add to .env file or app/local_settings.py")
    print("\n2. Create Plans in Django Admin:")
    print("   - Visit http://localhost:8000/admin/billing/plan/")
    print("   - Create your subscription plans")
    print("\n3. Sync Plans with Stripe:")
    print("   - Run: python manage.py sync_stripe_plans")
    print("\n4. Configure Webhooks:")
    print("   - Add endpoint: https://yourdomain.com/billing/webhook/")
    print("   - Select events: checkout.session.completed, customer.subscription.*,")
    print("     invoice.payment_succeeded, invoice.payment_failed")
    print("\n5. Test Locally:")
    print("   - Install Stripe CLI: https://stripe.com/docs/stripe-cli")
    print("   - Run: stripe listen --forward-to localhost:8000/billing/webhook/")
    print("   - Test payment with card: 4242 4242 4242 4242")


def main():
    """Run all tests"""
    print("=" * 60)
    print("🔧 Stripe Billing Setup Verification")
    print("=" * 60)
    
    results = {
        'Configuration': test_configuration(),
        'Stripe Connection': test_stripe_connection() if settings.STRIPE_SECRET_KEY else False,
        'Database Models': test_database_models(),
        'Plan Configuration': test_plan_stripe_configuration(),
        'Stripe Products': test_stripe_products() if settings.STRIPE_SECRET_KEY else False,
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ All tests passed! Your Stripe integration is ready.")
        print("\n🎉 You can now:")
        print("   - Visit /billing/plans/ to view plans")
        print("   - Test the payment flow")
        print("   - Configure production webhooks")
    else:
        print("\n⚠️  Some tests failed. Please review the issues above.")
        print_next_steps()
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
