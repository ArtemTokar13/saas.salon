#!/usr/bin/env python
"""
Verify Stripe webhook configuration for production
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

def check_webhook_config():
    print("=" * 60)
    print("STRIPE WEBHOOK CONFIGURATION CHECK")
    print("=" * 60)
    
    # Check if using live or test keys
    if settings.STRIPE_SECRET_KEY.startswith('sk_live_'):
        print("✓ Using LIVE Stripe keys")
        mode = 'live'
    elif settings.STRIPE_SECRET_KEY.startswith('sk_test_'):
        print("✓ Using TEST Stripe keys")
        mode = 'test'
    else:
        print("✗ Unknown Stripe key format")
        return
    
    print(f"✓ Webhook secret configured: {settings.STRIPE_WEBHOOK_SECRET[:15]}...")
    
    # Check if webhook secret matches the mode
    if settings.STRIPE_WEBHOOK_SECRET.startswith('whsec_'):
        print("✓ Webhook secret format is correct")
        
        # Warning if this looks like a CLI secret (they're typically shorter/test only)
        if mode == 'live':
            print("\n⚠️  IMPORTANT: Make sure this webhook secret is from:")
            print("   Stripe Dashboard → Webhooks (in LIVE mode)")
            print("   NOT from 'stripe listen' command!")
    else:
        print("✗ Webhook secret format is incorrect")
        return
    
    print("\n" + "=" * 60)
    print("FETCHING WEBHOOK ENDPOINTS FROM STRIPE")
    print("=" * 60)
    
    try:
        # List webhook endpoints
        endpoints = stripe.WebhookEndpoint.list(limit=10)
        
        if not endpoints.data:
            print("✗ No webhook endpoints configured in Stripe Dashboard!")
            print("\nYou need to:")
            print("1. Go to https://dashboard.stripe.com")
            print("2. Switch to LIVE mode")
            print("3. Navigate to: Developers → Webhooks")
            print("4. Click 'Add endpoint'")
            print("5. Add: https://reserva-ya.es/billing/webhook/")
            print("6. Select events: checkout.session.completed,")
            print("                  invoice.payment_succeeded,")
            print("                  invoice.payment_failed")
            print("7. Copy the signing secret and update STRIPE_WEBHOOK_SECRET")
        else:
            print(f"✓ Found {len(endpoints.data)} webhook endpoint(s):\n")
            
            target_url = "https://reserva-ya.es/billing/webhook/"
            found_match = False
            
            for endpoint in endpoints.data:
                is_match = endpoint.url == target_url
                marker = "→" if is_match else " "
                print(f"{marker} URL: {endpoint.url}")
                print(f"  Status: {endpoint.status}")
                print(f"  Events: {', '.join(endpoint.enabled_events) if endpoint.enabled_events else 'ALL'}")
                # Note: Secret is not exposed via API for security
                print(f"  Secret: [Hidden - view in Dashboard]")
                print()
                
                if is_match:
                    found_match = True
                    required_events = {
                        'checkout.session.completed',
                        'invoice.payment_succeeded',
                        'invoice.payment_failed'
                    }
                    
                    if endpoint.enabled_events:
                        has_all_events = required_events.issubset(set(endpoint.enabled_events))
                        if has_all_events:
                            print("  ✓ All required events are configured!")
                        else:
                            missing = required_events - set(endpoint.enabled_events)
                            print(f"  ⚠️  Missing events: {', '.join(missing)}")
                    
                    # Note: Cannot verify secret match via API (not exposed for security)
                    print("\n  ⚠️  To get the signing secret:")
                    print("     1. Go to Stripe Dashboard → Developers → Webhooks")
                    print("     2. Click on this endpoint")
                    print("     3. Click 'Reveal' on the Signing Secret")
                    print("     4. Update STRIPE_WEBHOOK_SECRET in your .env file")
                    print("     5. Restart your server with ./deploy.sh")
            
            if not found_match:
                print(f"⚠️  No webhook endpoint found for: {target_url}")
                print("   Please create one in the Stripe Dashboard")
    
    except stripe.error.StripeError as e:
        print(f"✗ Error connecting to Stripe: {e}")
        print("\nCheck your STRIPE_SECRET_KEY is valid")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    check_webhook_config()
