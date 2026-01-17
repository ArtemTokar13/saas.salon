from django.db import models
from django.contrib.auth.models import User
from companies.models import Company
from decimal import Decimal


class Plan(models.Model):
    """Single plan with base workers and per-worker pricing"""
    PERIOD_MULTIPLIERS = {
        'monthly': 1,
        'three_months': 3,
        'six_months': 6,
        'yearly': 12,
    }
    PERIOD_DISCOUNTS = {
        'monthly': Decimal('0.00'),      # 0% discount - full price
        'three_months': Decimal('0.10'),  # 10% discount
        'six_months': Decimal('0.20'),    # 20% discount
        'yearly': Decimal('0.40'),        # 40% discount
    }
    
    name = models.CharField(max_length=255)
    base_workers = models.PositiveIntegerField(default=3, help_text="Number of workers included in base price")
    base_monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Base monthly price for included workers")
    additional_worker_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Price per additional worker per month")
    
    # Legacy fields for backward compatibility
    max_number_of_staff = models.PositiveIntegerField(default=3, help_text="Deprecated: use base_workers")
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Deprecated: use base_monthly_price")
    
    description = models.TextField(blank=True)
    features = models.JSONField(default=dict, blank=True)
    trial_days = models.PositiveIntegerField(default=30, help_text="Number of free trial days (0 = no trial)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Stripe fields
    stripe_product_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Product ID")
    stripe_price_id_monthly = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Price ID for monthly base")
    stripe_price_id_three_months = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Price ID for 3 months base")
    stripe_price_id_six_months = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Price ID for 6 months base")
    stripe_price_id_yearly = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Price ID for yearly base")
    stripe_additional_worker_price_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Price ID for additional workers")

    def __str__(self):
        return self.name
    
    def get_stripe_price_id(self, period):
        """Get the Stripe Price ID for a given billing period"""
        price_id_map = {
            'monthly': self.stripe_price_id_monthly,
            'three_months': self.stripe_price_id_three_months,
            'six_months': self.stripe_price_id_six_months,
            'yearly': self.stripe_price_id_yearly,
        }
        return price_id_map.get(period)
    
    def get_price_for_period(self, period, num_workers=None):
        """Calculate price based on billing period with discounts and worker count"""
        if num_workers is None:
            num_workers = self.base_workers
        
        discount = self.PERIOD_DISCOUNTS.get(period, Decimal('0.00'))
        multiplier = self.PERIOD_MULTIPLIERS.get(period, 1)
        
        # Calculate base price
        base_price = self.base_monthly_price if self.base_monthly_price else self.monthly_price
        
        # Calculate additional workers cost
        additional_workers = max(0, num_workers - self.base_workers)
        additional_cost = additional_workers * self.additional_worker_price
        
        # Total monthly price
        monthly_total = base_price + additional_cost
        
        # Apply period multiplier and discount
        total_price = monthly_total * multiplier * (Decimal('1.00') - discount)
        return total_price.quantize(Decimal('0.01'))
    
    def get_monthly_equivalent(self, period, num_workers=None):
        """Get the effective monthly price for a given period"""
        total_price = self.get_price_for_period(period, num_workers)
        months = self.PERIOD_MULTIPLIERS.get(period, 1)
        return (total_price / months).quantize(Decimal('0.01'))
    
    def calculate_worker_pricing(self, num_workers):
        """Calculate pricing breakdown for given number of workers"""
        base_price = self.base_monthly_price if self.base_monthly_price else self.monthly_price
        additional_workers = max(0, num_workers - self.base_workers)
        additional_cost = additional_workers * self.additional_worker_price
        total = base_price + additional_cost
        
        return {
            'base_price': base_price,
            'base_workers': self.base_workers,
            'additional_workers': additional_workers,
            'additional_cost': additional_cost,
            'total_monthly': total,
        }
    

class Subscription(models.Model):
    MONTHLY = 'monthly'
    THREE_MONTHS = 'three_months'
    SIX_MONTHS = 'six_months'
    YEARLY = 'yearly'
    
    BILLING_PERIOD_CHOICES = [
        (MONTHLY, 'Monthly'),
        (THREE_MONTHS, '3 Months (-10%)'),
        (SIX_MONTHS, '6 Months (-20%)'),
        (YEARLY, 'Yearly (-40%)'),
    ]
    
    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAST_DUE = 'past_due'
    STATUS_UNPAID = 'unpaid'
    
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_PAST_DUE, 'Past Due'),
        (STATUS_UNPAID, 'Unpaid'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIOD_CHOICES, default=MONTHLY)
    num_workers = models.PositiveIntegerField(default=3, help_text="Number of workers in this subscription")
    start_date = models.DateField()
    end_date = models.DateField()
    trial_end = models.DateField(blank=True, null=True, help_text="End date of trial period")
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    
    # Stripe fields
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Customer ID")
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Subscription ID")
    stripe_latest_invoice_id = models.CharField(max_length=255, blank=True, null=True, help_text="Latest Stripe Invoice ID")
    cancel_at_period_end = models.BooleanField(default=False, help_text="Cancel subscription at period end")
    cancelled_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.company.name} - {self.plan.name} ({self.get_billing_period_display()})"
    
    @property
    def price(self):
        """Get the calculated price for this subscription based on billing period and workers"""
        return self.plan.get_price_for_period(self.billing_period, self.num_workers)
    
    @property
    def monthly_equivalent(self):
        """Get the effective monthly price"""
        return self.plan.get_monthly_equivalent(self.billing_period, self.num_workers)
    
    @property
    def pricing_breakdown(self):
        """Get detailed pricing breakdown"""
        return self.plan.calculate_worker_pricing(self.num_workers)
    
    @property
    def is_trial(self):
        """Check if subscription is in trial period"""
        if not self.trial_end:
            return False
        from django.utils import timezone
        return timezone.now().date() <= self.trial_end
    

class Transaction(models.Model):
    PAYMENT_STATUS_PENDING = 'pending'
    PAYMENT_STATUS_SUCCEEDED = 'succeeded'
    PAYMENT_STATUS_FAILED = 'failed'
    PAYMENT_STATUS_REFUNDED = 'refunded'
    
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, 'Pending'),
        (PAYMENT_STATUS_SUCCEEDED, 'Succeeded'),
        (PAYMENT_STATUS_FAILED, 'Failed'),
        (PAYMENT_STATUS_REFUNDED, 'Refunded'),
    ]
    
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=255, unique=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING)
    
    # Stripe fields
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Payment Intent ID")
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Invoice ID")
    stripe_charge_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe Charge ID")

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount}"