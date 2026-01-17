# Stripe Billing - Quick Start

## 1. Install Dependencies
```bash
pip install stripe==11.2.0
```

## 2. Configure Stripe Keys

Add to your `.env` file or `app/local_settings.py`:
```python
STRIPE_PUBLIC_KEY = 'pk_test_...'
STRIPE_SECRET_KEY = 'sk_test_...'
STRIPE_WEBHOOK_SECRET = 'whsec_...'
```

## 3. Run Migrations
```bash
python manage.py migrate
```

## 4. Create Plans in Django Admin

1. Go to: http://localhost:8000/admin/billing/plan/
2. Create your plans (e.g., Basic, Pro, Enterprise)
3. Set monthly_price, max_number_of_staff, features

## 5. Sync Plans with Stripe

Run the management command to create Stripe products and prices:
```bash
python manage.py sync_stripe_plans
```

This will:
- Create Stripe Products for each plan
- Create Stripe Prices for all billing periods (monthly, 3mo, 6mo, yearly)
- Automatically calculate discounted prices
- Update your Django plans with Stripe IDs

## 6. Test Locally with Stripe CLI

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login

# Forward webhooks to your local server
stripe listen --forward-to localhost:8000/billing/webhook/

# In another terminal, start your Django server
python manage.py runserver
```

## 7. Test Payment Flow

1. Visit: http://localhost:8000/billing/plans/
2. Select a plan
3. Choose billing period
4. Use test card: `4242 4242 4242 4242`
5. Complete checkout

## 8. Production Setup

1. Switch to live Stripe keys in settings
2. Configure production webhook URL in Stripe Dashboard
3. Ensure HTTPS is enabled
4. Test end-to-end payment flow

## Management Commands

### Sync all plans with Stripe
```bash
python manage.py sync_stripe_plans
```

### Sync specific plan
```bash
python manage.py sync_stripe_plans --plan-id 1
```

### Dry run (preview changes)
```bash
python manage.py sync_stripe_plans --dry-run
```

## Test Cards

| Card Number | Scenario |
|------------|----------|
| 4242 4242 4242 4242 | Success |
| 4000 0000 0000 9995 | Declined |
| 4000 0025 0000 3155 | Requires authentication |

Use any future expiry date and any 3-digit CVC.

## Webhook Events

The system handles these Stripe webhook events:
- `checkout.session.completed` - New subscription
- `customer.subscription.updated` - Subscription changes
- `customer.subscription.deleted` - Cancellations
- `invoice.payment_succeeded` - Successful payment
- `invoice.payment_failed` - Failed payment

## URLs

| URL | Description |
|-----|-------------|
| `/billing/plans/` | Browse plans |
| `/billing/subscription/` | Current subscription |
| `/billing/change-plan/<id>/` | Select plan |
| `/billing/customer-portal/` | Stripe portal |
| `/billing/webhook/` | Webhook endpoint |

## Support

See [STRIPE_SETUP_GUIDE.md](STRIPE_SETUP_GUIDE.md) for detailed documentation.
