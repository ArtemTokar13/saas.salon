from django.db import models
from django.contrib.auth.models import User
from companies.models import Company
from decimal import Decimal
import traceback


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
    
    description = models.TextField(blank=True)
    features = models.JSONField(default=dict, blank=True)
    trial_days = models.PositiveIntegerField(default=30, help_text="Number of free trial days (0 = no trial)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def get_price(self, period):
        return self.base_monthly_price * self.PERIOD_MULTIPLIERS.get(period, 1)
    
    def get_price_for_period(self, period, num_workers=None):
        """Calculate price based on billing period with discounts and worker count"""
        if num_workers is None:
            num_workers = self.base_workers
        
        discount = self.PERIOD_DISCOUNTS.get(period, Decimal('0.00'))
        multiplier = self.PERIOD_MULTIPLIERS.get(period, 1)
        
        # Calculate base price
        base_price = self.base_monthly_price
        
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
        base_price = self.base_monthly_price
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
    num_workers = models.PositiveIntegerField(default=3)
    start_date = models.DateField()
    end_date = models.DateField()
    trial_end = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    cancelled_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.company.name} - {self.plan.name} ({self.get_billing_period_display()})"

    @property
    def price(self):
        return self.plan.get_price_for_period(self.billing_period, self.num_workers)

    @property
    def monthly_equivalent(self):
        return self.plan.get_monthly_equivalent(self.billing_period, self.num_workers)

    @property
    def pricing_breakdown(self):
        return self.plan.calculate_worker_pricing(self.num_workers)

    @property
    def is_trial(self):
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
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount}"


class StripeErrorLog(models.Model):
    """Simple log to track Stripe payment errors"""
    function_name = models.CharField(max_length=255, help_text="Function where error occurred")
    error_message = models.TextField(help_text="Stripe error message")
    error_type = models.CharField(max_length=100, blank=True, help_text="Stripe error type (e.g., card_error)")
    
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    
    request_params = models.JSONField(default=dict, blank=True, help_text="What was being attempted")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Admin notes")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.function_name} - {self.error_message[:50]} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @classmethod
    def log_error(cls, function_name, error, company=None, subscription=None, request_params=None):
        """Simple helper to log Stripe errors"""
        error_type = getattr(error, '__class__', type(error)).__name__
        
        return cls.objects.create(
            function_name=function_name,
            error_message=str(error),
            error_type=error_type,
            company=company,
            subscription=subscription,
            request_params=request_params or {},
        )
