from django.db import models
from django.contrib.auth.models import User
from companies.models import Company
from decimal import Decimal


class Plan(models.Model):
    """Base plan with monthly pricing"""
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
    max_number_of_staff = models.PositiveIntegerField(default=1)
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Base monthly price")
    description = models.TextField(blank=True)
    features = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    def get_price_for_period(self, period):
        """Calculate price based on billing period with discounts"""
        
        discount = self.PERIOD_DISCOUNTS.get(period, Decimal('0.00'))
        multiplier = self.PERIOD_MULTIPLIERS.get(period, 1)
        
        # Calculate: (monthly_price * months) * (1 - discount)
        total_price = self.monthly_price * multiplier * (Decimal('1.00') - discount)
        return total_price.quantize(Decimal('0.01'))
    
    def get_monthly_equivalent(self, period):
        """Get the effective monthly price for a given period"""
        PERIOD_MULTIPLIERS = {
            'monthly': 1,
            'three_months': 3,
            'six_months': 6,
            'yearly': 12,
        }
        
        total_price = self.get_price_for_period(period)
        months = PERIOD_MULTIPLIERS.get(period, 1)
        return (total_price / months).quantize(Decimal('0.01'))
    

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
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIOD_CHOICES, default=MONTHLY)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company.name} - {self.plan.name} ({self.get_billing_period_display()})"
    
    @property
    def price(self):
        """Get the calculated price for this subscription based on billing period"""
        return self.plan.get_price_for_period(self.billing_period)
    
    @property
    def monthly_equivalent(self):
        """Get the effective monthly price"""
        return self.plan.get_monthly_equivalent(self.billing_period)
    

class Transaction(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount}"