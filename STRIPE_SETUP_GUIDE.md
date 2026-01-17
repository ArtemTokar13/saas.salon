# Stripe Billing Integration - Setup Guide

## Overview
Your SaaS Salon application now has a complete Stripe payment integration with subscription management, recurring billing, and webhook support.

## Features Implemented

### 1. Subscription Plans
- Multiple billing periods (Monthly, 3 Months, 6 Months, Yearly)
- Automatic discounts for longer periods (10%, 20%, 40%)
- Flexible plan configuration with staff limits and features

### 2. Stripe Integration
- Secure checkout sessions via Stripe Checkout
- Recurring subscription billing
- Customer portal for payment method updates
- Webhook handlers for payment events

### 3. Payment Processing
- Automatic subscription activation on successful payment
- Transaction history tracking
- Payment status monitoring (succeeded, pending, failed)
- Invoice management

### 4. Subscription Management
- Change plans with secure Stripe checkout
- Cancel subscriptions (with end-of-period cancellation)
- Automatic renewal handling
- Subscription status tracking (active, cancelled, past_due, unpaid)

## Setup Instructions

### 1. Get Your Stripe Keys

1. Sign up at https://stripe.com or log in
2. Navigate to Developers → API keys
3. Copy your **Publishable key** and **Secret key**
4. For webhooks: Developers → Webhooks → Add endpoint

### 2. Configure Environment Variables

Create or update your `.env` file or set these environment variables:

```bash
STRIPE_PUBLIC_KEY=pk_test_51xxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_51xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

Or add them to your `app/local_settings.py`:

```python
STRIPE_PUBLIC_KEY = 'pk_test_51xxxxxxxxxxxxx'
STRIPE_SECRET_KEY = 'sk_test_51xxxxxxxxxxxxx'
STRIPE_WEBHOOK_SECRET = 'whsec_xxxxxxxxxxxxx'
```

### 3. Create Products and Prices in Stripe

For each plan, you need to create Products and Prices in Stripe:

**Option A: Via Stripe Dashboard**
1. Go to Products in your Stripe Dashboard
2. Create a new Product (e.g., "Basic Plan", "Pro Plan")
3. For each billing period, create a Price:
   - Monthly: $29/month recurring
   - 3 Months: $78.30 every 3 months (10% discount)
   - 6 Months: $139.20 every 6 months (20% discount)
   - Yearly: $208.80 every year (40% discount)
4. Copy the Price IDs (they start with `price_`)

**Option B: Via Python Script** (recommended)

Create a management command to sync plans:

```python
# Create: billing/management/commands/sync_stripe_plans.py
from django.core.management.base import BaseCommand
import stripe
from django.conf import settings
from billing.models import Plan

stripe.api_key = settings.STRIPE_SECRET_KEY

class Command(BaseCommand):
    help = 'Sync plans with Stripe'

    def handle(self, *args, **options):
        for plan in Plan.objects.all():
            # Create Stripe Product
            product = stripe.Product.create(
                name=plan.name,
                description=plan.description,
            )
            plan.stripe_product_id = product.id
            
            # Create prices for each billing period
            periods = {
                'monthly': 1,
                'three_months': 3,
                'six_months': 6,
                'yearly': 12,
            }
            
            for period, months in periods.items():
                price = plan.get_price_for_period(period)
                stripe_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(price * 100),  # Convert to cents
                    currency='usd',
                    recurring={
                        'interval': 'month' if period == 'monthly' else 'month',
                        'interval_count': months,
                    }
                )
                
                setattr(plan, f'stripe_price_id_{period}', stripe_price.id)
            
            plan.save()
            self.stdout.write(f"Synced {plan.name}")
```

Run it with:
```bash
python manage.py sync_stripe_plans
```

### 4. Update Your Plans in Django Admin

1. Go to Django Admin → Billing → Plans
2. For each plan, add the Stripe Price IDs you created:
   - `stripe_product_id`: prod_xxxxx
   - `stripe_price_id_monthly`: price_xxxxx
   - `stripe_price_id_three_months`: price_xxxxx
   - `stripe_price_id_six_months`: price_xxxxx
   - `stripe_price_id_yearly`: price_xxxxx

### 5. Configure Stripe Webhooks

1. In Stripe Dashboard: Developers → Webhooks → Add endpoint
2. Endpoint URL: `https://yourdomain.com/billing/webhook/`
3. Select these events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the **Signing secret** (starts with `whsec_`)
5. Add it to your environment as `STRIPE_WEBHOOK_SECRET`

### 6. Test the Integration

**Test Mode (Recommended for Development)**
1. Use Stripe test keys (start with `pk_test_` and `sk_test_`)
2. Use test card: `4242 4242 4242 4242`, any future date, any CVC
3. Test webhook locally using Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:8000/billing/webhook/
   ```

**Production**
1. Switch to live keys (start with `pk_live_` and `sk_live_`)
2. Configure production webhook endpoint
3. Ensure SSL/HTTPS is enabled

## Usage

### For Customers

1. **View Plans**: Navigate to `/billing/plans/`
2. **Select Plan**: Choose a plan and billing period
3. **Checkout**: Redirected to Stripe Checkout (secure payment)
4. **Success**: Subscription activated automatically
5. **Manage**: View subscription at `/billing/subscription/`
6. **Update Payment**: Click "Manage Billing" for Stripe Customer Portal
7. **Cancel**: Cancel subscription (continues until period end)

### For Admins

1. **Django Admin**: Manage plans, view subscriptions and transactions
2. **Stripe Dashboard**: View detailed payment info, refunds, disputes
3. **Webhooks**: Monitor webhook delivery in Stripe Dashboard

## Webhook Event Handlers

The following webhook events are handled:

- **checkout.session.completed**: Creates new subscription after successful checkout
- **customer.subscription.updated**: Syncs subscription status changes
- **customer.subscription.deleted**: Marks subscription as cancelled
- **invoice.payment_succeeded**: Records successful payment transaction
- **invoice.payment_failed**: Marks subscription as past due

## Database Models

### Plan
- Basic plan information (name, price, features)
- Stripe Product and Price IDs
- Multi-period pricing support

### Subscription
- Links company to plan
- Tracks billing period and dates
- Stripe customer and subscription IDs
- Status tracking (active, cancelled, past_due, unpaid)

### Transaction
- Payment history
- Stripe Payment Intent, Invoice, and Charge IDs
- Payment status tracking

## URLs

- `/billing/subscription/` - View current subscription
- `/billing/plans/` - Browse available plans
- `/billing/change-plan/<id>/` - Select plan and billing period
- `/billing/cancel/` - Cancel subscription
- `/billing/customer-portal/` - Stripe Customer Portal
- `/billing/webhook/` - Stripe webhook endpoint (POST only)

## Security Considerations

1. **Webhook Verification**: All webhooks are verified using Stripe signature
2. **CSRF Exemption**: Webhook endpoint is CSRF-exempt (required for Stripe)
3. **HTTPS Required**: Use HTTPS in production for secure payment processing
4. **Secret Keys**: Never commit secret keys to version control
5. **Test Mode**: Use test keys for development and testing

## Testing Checklist

- [ ] Plans created in Stripe with correct pricing
- [ ] Stripe keys configured in settings
- [ ] User can view plans
- [ ] Checkout session redirects to Stripe
- [ ] Test payment completes successfully
- [ ] Subscription created in database
- [ ] Transaction recorded
- [ ] Webhook events received and processed
- [ ] Subscription cancellation works
- [ ] Customer portal accessible
- [ ] Billing history displays correctly

## Troubleshooting

### Webhooks Not Receiving
- Check webhook signing secret is correct
- Verify webhook endpoint URL is accessible
- Use Stripe CLI for local testing: `stripe listen --forward-to localhost:8000/billing/webhook/`
- Check webhook logs in Stripe Dashboard

### Payment Fails
- Verify Stripe Price IDs are correctly set in Plan model
- Check Stripe keys are valid and not expired
- Ensure test cards are used in test mode
- Review Stripe Dashboard logs

### Subscription Not Activating
- Check webhook events are being received
- Review Django logs for errors in webhook handlers
- Verify checkout.session.completed event contains correct metadata
- Check that company_id and plan_id are valid

## Next Steps

1. **Email Notifications**: Add email notifications for payment success/failure
2. **Trial Periods**: Implement free trial periods in Stripe
3. **Proration**: Handle plan upgrades/downgrades with proration
4. **Usage-Based Billing**: Add metered billing for additional features
5. **Tax Handling**: Configure Stripe Tax for automatic tax calculation
6. **Dunning Management**: Set up automatic retry logic for failed payments
7. **Analytics**: Track MRR, churn rate, and other subscription metrics

## Support

For Stripe-specific issues:
- Stripe Documentation: https://stripe.com/docs
- Stripe Support: https://support.stripe.com

For application issues, review Django logs and Stripe webhook logs.
