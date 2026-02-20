# Migration Guide for Stripe Connect

## Quick Migration Steps

After implementing the Stripe Connect code, run these commands:

```bash
# Generate migrations for both apps
python manage.py makemigrations companies bookings

# Review the migrations (optional but recommended)
python manage.py sqlmigrate companies XXXX  # Replace XXXX with migration number
python manage.py sqlmigrate bookings YYYY   # Replace YYYY with migration number

# Apply migrations
python manage.py migrate
```

---

## Expected Migration Changes

### Companies App Migration

The migration will add these fields to the `Company` model:

```python
# Migration: companies/migrations/000X_add_stripe_connect_fields.py

operations = [
    migrations.AddField(
        model_name='company',
        name='stripe_account_id',
        field=models.CharField(blank=True, max_length=255, null=True, help_text='Stripe Connect Account ID'),
    ),
    migrations.AddField(
        model_name='company',
        name='stripe_onboarding_completed',
        field=models.BooleanField(default=False, help_text='Whether Stripe onboarding is complete'),
    ),
    migrations.AddField(
        model_name='company',
        name='stripe_charges_enabled',
        field=models.BooleanField(default=False, help_text='Whether the account can receive payments'),
    ),
    migrations.AddField(
        model_name='company',
        name='stripe_payouts_enabled',
        field=models.BooleanField(default=False, help_text='Whether the account can receive payouts'),
    ),
    migrations.AddField(
        model_name='company',
        name='stripe_details_submitted',
        field=models.BooleanField(default=False, help_text='Whether account details have been submitted'),
    ),
    migrations.AddField(
        model_name='company',
        name='accepts_online_payments',
        field=models.BooleanField(default=False, help_text='Whether salon accepts online payments for bookings'),
    ),
]
```

### Bookings App Migration

The migration will add these fields to the `Booking` model:

```python
# Migration: bookings/migrations/000Y_add_payment_fields.py

operations = [
    migrations.AddField(
        model_name='booking',
        name='payment_required',
        field=models.BooleanField(default=False, help_text='Whether this booking requires online payment'),
    ),
    migrations.AddField(
        model_name='booking',
        name='payment_status',
        field=models.CharField(
            choices=[
                ('pending', 'Pending'),
                ('paid', 'Paid'),
                ('failed', 'Failed'),
                ('refunded', 'Refunded')
            ],
            default='pending',
            help_text='Payment status',
            max_length=20,
        ),
    ),
    migrations.AddField(
        model_name='booking',
        name='stripe_checkout_session_id',
        field=models.CharField(blank=True, max_length=255, null=True, help_text='Stripe Checkout Session ID'),
    ),
    migrations.AddField(
        model_name='booking',
        name='stripe_payment_intent_id',
        field=models.CharField(blank=True, max_length=255, null=True, help_text='Stripe Payment Intent ID'),
    ),
    migrations.AddField(
        model_name='booking',
        name='paid_amount',
        field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, help_text='Amount paid by customer'),
    ),
    migrations.AddField(
        model_name='booking',
        name='paid_at',
        field=models.DateTimeField(blank=True, null=True, help_text='When payment was completed'),
    ),
]
```

---

## Rollback (If Needed)

If you need to rollback the migrations:

```bash
# Rollback companies migration
python manage.py migrate companies 000X_previous_migration

# Rollback bookings migration  
python manage.py migrate bookings 000Y_previous_migration
```

Where `000X` and `000Y` are the migration numbers *before* the Stripe Connect changes.

---

## Data Migration

If you have existing companies or bookings, you may want to set default values:

### Optional: Set All Existing Companies to NOT Accept Online Payments

```python
# Python manage.py shell

from companies.models import Company

# Ensure all existing companies have online payments disabled by default
Company.objects.filter(accepts_online_payments__isnull=True).update(
    accepts_online_payments=False
)
```

### Optional: Set All Existing Bookings to 'pending' Payment Status

```python
# Python manage.py shell

from bookings.models import Booking

# Set all existing bookings to not require payment
Booking.objects.filter(payment_required__isnull=True).update(
    payment_required=False,
    payment_status='pending'
)
```

---

## Verification

After migration, verify the fields exist:

```bash
python manage.py shell
```

```python
from companies.models import Company
from bookings.models import Booking

# Check Company fields
company = Company.objects.first()
print(hasattr(company, 'stripe_account_id'))  # Should print: True
print(hasattr(company, 'accepts_online_payments'))  # Should print: True

# Check Booking fields
booking = Booking.objects.first()
print(hasattr(booking, 'payment_status'))  # Should print: True
print(hasattr(booking, 'stripe_checkout_session_id'))  # Should print: True
```

---

## Database Impact

- **6 new fields** added to `companies_company` table
- **6 new fields** added to `bookings_booking` table
- All fields are nullable or have defaults, so **no data loss**
- **Zero downtime** migration (no data changes, only schema additions)

---

## Next Steps After Migration

1. Configure Stripe keys in settings
2. Set up webhooks in Stripe Dashboard
3. Test onboarding flow
4. Test payment flow

See `STRIPE_CONNECT_IMPLEMENTATION.md` for full setup guide.
