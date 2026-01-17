# Stripe Billing Setup Checklist

Use this checklist to ensure everything is properly configured.

## ✅ Installation & Setup

- [ ] Stripe package installed (`pip install stripe==11.2.0`)
- [ ] Database migrations applied (`python manage.py migrate`)
- [ ] Django server can start without errors

## ✅ Stripe Account

- [ ] Stripe account created at https://stripe.com
- [ ] Test API keys obtained (Developers → API keys)
- [ ] Test keys added to configuration (.env or local_settings.py)

## ✅ Plans Configuration

- [ ] At least one plan created in Django admin
- [ ] Plan has monthly_price set
- [ ] Plan has max_number_of_staff set
- [ ] Plan description added
- [ ] Plan is marked as active

## ✅ Stripe Sync

- [ ] Ran `python manage.py sync_stripe_plans`
- [ ] No errors in sync output
- [ ] Stripe Product IDs populated in admin
- [ ] Stripe Price IDs populated for all billing periods
- [ ] Verified products exist in Stripe Dashboard

## ✅ Testing

- [ ] Can access `/billing/plans/`
- [ ] Plans display correctly
- [ ] Can click "Select Plan"
- [ ] Billing period selection page loads
- [ ] Redirects to Stripe Checkout
- [ ] Test card payment succeeds (4242 4242 4242 4242)
- [ ] Subscription appears in Django admin
- [ ] Transaction recorded in admin
- [ ] Can view subscription at `/billing/subscription/`
- [ ] Billing history shows payment

## ✅ Webhooks (Local Development)

- [ ] Stripe CLI installed
- [ ] Can run `stripe listen --forward-to localhost:8000/billing/webhook/`
- [ ] Webhooks received during test payment
- [ ] No errors in webhook handler logs

## ✅ Webhooks (Production)

- [ ] Webhook endpoint added in Stripe Dashboard
- [ ] Webhook URL: `https://yourdomain.com/billing/webhook/`
- [ ] Selected events:
  - [ ] checkout.session.completed
  - [ ] customer.subscription.updated
  - [ ] customer.subscription.deleted
  - [ ] invoice.payment_succeeded
  - [ ] invoice.payment_failed
- [ ] Webhook signing secret added to configuration
- [ ] Test webhook delivery successful

## ✅ Production Readiness

- [ ] Switched to live Stripe keys
- [ ] HTTPS enabled on production server
- [ ] Production webhook endpoint configured
- [ ] Tested real payment (small amount)
- [ ] Subscription activated correctly
- [ ] Email notifications configured (optional)
- [ ] Error monitoring set up (optional)
- [ ] Backup strategy for database

## ✅ Security

- [ ] API keys stored in environment variables
- [ ] API keys not in git repository
- [ ] Webhook signature verification working
- [ ] HTTPS enforced in production
- [ ] CSRF protection enabled (except webhook endpoint)

## ✅ User Experience

- [ ] Clear pricing displayed
- [ ] Billing periods show discounts
- [ ] Checkout flow is smooth
- [ ] Success message displays after payment
- [ ] Subscription details are clear
- [ ] Cancellation process works
- [ ] Customer portal accessible

## ✅ Admin Experience

- [ ] Can create/edit plans
- [ ] Can view all subscriptions
- [ ] Can see transaction history
- [ ] Stripe IDs visible in admin
- [ ] Payment status clearly indicated

## ✅ Documentation

- [ ] Team knows how to create plans
- [ ] Team knows how to sync with Stripe
- [ ] Support process documented
- [ ] Troubleshooting guide available

## 🧪 Test Scenarios

Test these scenarios before going live:

### Happy Path
- [ ] New user selects plan
- [ ] User completes payment
- [ ] Subscription activates immediately
- [ ] User can view subscription
- [ ] Billing history shows payment

### Plan Changes
- [ ] User can switch to higher plan
- [ ] User can switch to lower plan
- [ ] Old subscription deactivates
- [ ] New subscription activates

### Cancellation
- [ ] User can cancel subscription
- [ ] Subscription continues until period end
- [ ] Status shows "Cancelled"
- [ ] Access maintained until end date

### Payment Failures
- [ ] Test with declining card (4000 0000 0000 9995)
- [ ] Payment failure handled gracefully
- [ ] Subscription marked as past_due
- [ ] User receives appropriate message

### Webhooks
- [ ] Webhook receives checkout.session.completed
- [ ] Subscription created in database
- [ ] Transaction recorded
- [ ] Invoice payment success processed
- [ ] Invoice payment failure processed
- [ ] Subscription updates synced

## 📊 Metrics to Monitor

After launch, track these metrics:

- [ ] Number of active subscriptions
- [ ] Monthly recurring revenue (MRR)
- [ ] Churn rate
- [ ] Failed payments
- [ ] Webhook delivery success rate
- [ ] Average subscription duration
- [ ] Popular plans
- [ ] Cancellation reasons (if collected)

## 🚨 Emergency Procedures

Document these before launch:

- [ ] How to manually activate a subscription
- [ ] How to issue refunds
- [ ] How to handle payment disputes
- [ ] How to pause a subscription
- [ ] Support contact for Stripe issues
- [ ] Backup database restoration process

## 💡 Recommended Next Steps

After basic setup works:

- [ ] Add email notifications
- [ ] Implement free trial period
- [ ] Add usage-based billing
- [ ] Configure tax calculation
- [ ] Set up dunning management
- [ ] Create analytics dashboard
- [ ] Add invoice generation
- [ ] Support multiple currencies
- [ ] Add promotional codes
- [ ] Implement referral system

---

**Status**: Use this checklist to track your progress

**Last Updated**: Check off items as you complete them

**Need Help?**: See GETTING_STARTED.md for detailed instructions
