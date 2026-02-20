# Stripe Connect - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Run Migrations

```bash
python manage.py makemigrations companies bookings
python manage.py migrate
```

### Step 2: Configure Stripe Keys

Add to `app/local_settings.py`:

```python
STRIPE_PUBLIC_KEY = 'pk_test_51xxxxxxxxxxxxx'
STRIPE_SECRET_KEY = 'sk_test_51xxxxxxxxxxxxx'
STRIPE_CONNECT_WEBHOOK_SECRET = 'whsec_xxxxxxxxxxxxx'
```

### Step 3: Set Up Webhook

1. Go to https://dashboard.stripe.com/test/webhooks
2. Click "Add endpoint"
3. URL: `https://yourdomain.com/billing/webhook/connect/`
4. Select events:
   - `checkout.session.completed`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`
   - `account.updated`
5. Copy webhook secret → Add to settings

### Step 4: Test It!

```bash
# 1. Start server
python manage.py runserver

# 2. Login as salon admin
# 3. Go to: http://localhost:8000/billing/connect/dashboard/
# 4. Click "Connect Stripe Account"
# 5. Complete test onboarding
# 6. Create a booking and pay with test card: 4242 4242 4242 4242
```

---

## 📁 Key Files Created

| File | Purpose |
|------|---------|
| `billing/stripe_connect_utils.py` | Stripe API functions |
| `billing/stripe_connect_views.py` | Onboarding & payment views |
| `billing/stripe_connect_webhooks.py` | Event handlers |
| `templates/billing/stripe_connect_dashboard.html` | Dashboard UI |
| `templates/billing/_pay_online_button.html` | Payment button |

---

## 🔗 Key URLs

| URL | Purpose |
|-----|---------|
| `/billing/connect/dashboard/` | Salon payment dashboard |
| `/billing/connect/onboard/` | Start Stripe onboarding |
| `/billing/booking/<id>/pay/` | Customer payment page |
| `/billing/webhook/connect/` | Webhook endpoint |

---

## 💡 Usage Examples

### Add "Connect Stripe" Button to Dashboard

```django
{# In company_dashboard.html #}
{% if not company.stripe_onboarding_completed %}
    <a href="{% url 'stripe_connect_dashboard' %}" class="btn btn-primary">
        <i class="fas fa-link"></i> Set Up Payments
    </a>
{% endif %}
```

### Add "Pay Online" Button to Booking

```django
{# In booking_detail.html #}
{% include 'billing/_pay_online_button.html' with booking=booking %}
```

### Check Payment Status in Template

```django
{% if booking.payment_status == 'paid' %}
    <span class="badge badge-success">Paid</span>
{% elif booking.payment_status == 'pending' %}
    <span class="badge badge-warning">Payment Pending</span>
{% endif %}
```

### Check if Salon Accepts Payments

```python
# In views
if company.accepts_online_payments and company.stripe_charges_enabled:
    # Show payment option
    pass
```

---

## 🧪 Test Cards

| Card Number | Result |
|------------|--------|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 0002` | Decline |
| `4000 0025 0000 3155` | Requires authentication |

---

## 🐛 Common Issues

### Webhook not receiving events

**Fix**: Use Stripe CLI for local testing:

```bash
stripe listen --forward-connect-to localhost:8000/billing/webhook/connect/
```

### "Account not enabled for charges"

**Fix**: Complete Stripe onboarding at `/billing/connect/onboard/`

### Payment succeeds but booking not confirmed

**Fix**: Check webhook logs and Django logs for errors

---

## 📚 Full Documentation

See `STRIPE_CONNECT_IMPLEMENTATION.md` for:
- Complete setup guide
- Architecture details
- Security best practices
- Production deployment
- Troubleshooting

---

## ✅ What's Working

✅ Salon Stripe account creation  
✅ Stripe onboarding flow  
✅ Payment checkout sessions  
✅ Webhook event handling  
✅ Booking status updates  
✅ Payment status tracking  
✅ Dashboard UI  

---

## 🔜 Optional Enhancements

- [ ] Email notifications on payment success
- [ ] SMS notifications (Twilio integration)
- [ ] Refund functionality
- [ ] Payment reports for salons
- [ ] Invoice generation
- [ ] Platform transaction fees (if needed)

---

**Need Help?** Check `STRIPE_CONNECT_IMPLEMENTATION.md` for detailed documentation.
