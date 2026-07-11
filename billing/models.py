from django.db import models
from django.contrib.auth.models import User
from companies.models import Company
from decimal import Decimal
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

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
        'six_months': Decimal('0.15'),    # 15% discount
        'yearly': Decimal('0.30'),        # 30% discount
    }
    
    name = models.CharField(max_length=255)
    base_workers = models.PositiveIntegerField(default=3, help_text="Number of workers included in base price")
    base_monthly_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Base monthly price for included workers")
    additional_worker_price = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Price per additional worker per month")
    
    description = models.JSONField(default=dict, blank=True, help_text="Description by language: {'en': 'Description in English', 'es': 'Descripción en español', 'ca': 'Descripció en català'}")
    features = models.JSONField(default=dict, blank=True, help_text="Features by language: {'en': ['WhatsApp', 'Email'], 'es': ['WhatsApp', 'Correo electrónico'], 'ca': ['WhatsApp', 'Correu electrònic']}")
    whatsapp_included = models.BooleanField(default=False, help_text="Whether WhatsApp feature is included in this plan")
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
        (MONTHLY, _('Monthly')),
        (THREE_MONTHS, _('3 Months')),
        (SIX_MONTHS, _('6 Months')),
        (YEARLY, _('Yearly')),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_PAST_DUE = 'past_due'
    STATUS_UNPAID = 'unpaid'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, _('Active')),
        (STATUS_CANCELLED, _('Cancelled')),
        (STATUS_PAST_DUE, _('Past Due')),
        (STATUS_UNPAID, _('Unpaid')),
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
    
    # Stripe fields for automatic renewals
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True, help_text='Stripe Subscription ID')
    stripe_customer_id = models.CharField(max_length=255, blank=True, null=True, help_text='Stripe Customer ID')

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
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text='Human-readable invoice number')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING)
    stripe_invoice_id = models.CharField(max_length=255, blank=True, null=True)
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, null=True)
    payment_method_display = models.CharField(max_length=100, blank=True, help_text='e.g. Mastercard - 4985')

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.invoice_number:
            year = self.transaction_date.year if self.transaction_date else timezone.now().year
            self.invoice_number = f"RCP-{year}-{self.pk:04d}"
            Transaction.objects.filter(pk=self.pk).update(invoice_number=self.invoice_number)


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


class SellerBillingInfo(models.Model):
    """Singleton: platform billing info shown on the FROM side of invoices"""
    company_name = models.CharField(max_length=255, verbose_name=_('Company Name'))
    tax_id = models.CharField(max_length=50, blank=True, verbose_name=_('Tax ID (NIF/VAT)'))
    address = models.CharField(max_length=255, verbose_name=_('Address'))
    city = models.CharField(max_length=100, verbose_name=_('City'))
    province = models.CharField(max_length=100, blank=True, verbose_name=_('Province / State'))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_('Postal Code'))
    country = models.CharField(max_length=100, default='España', verbose_name=_('Country'))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_('Phone'))
    email = models.EmailField(blank=True, verbose_name=_('Email'))

    class Meta:
        verbose_name = _('Seller Billing Info')
        verbose_name_plural = _('Seller Billing Info')

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    def __str__(self):
        return self.company_name


class ClientBillingInfo(models.Model):
    """Client billing details for invoices (the TO side)"""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='billing_info')
    billing_name = models.CharField(max_length=255, verbose_name=_('Billing Name (company or person)'))
    tax_id = models.CharField(max_length=50, blank=True, verbose_name=_('Tax ID (NIE/NIF/VAT)'))
    address = models.CharField(max_length=255, verbose_name=_('Address'))
    city = models.CharField(max_length=100, verbose_name=_('City'))
    province = models.CharField(max_length=100, blank=True, verbose_name=_('Province / State'))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_('Postal Code'))
    country = models.CharField(max_length=100, default='España', verbose_name=_('Country'))
    phone = models.CharField(max_length=30, blank=True, verbose_name=_('Phone'))
    email = models.EmailField(blank=True, verbose_name=_('Email'))

    class Meta:
        verbose_name = _('Client Billing Info')
        verbose_name_plural = _('Client Billing Info')

    def __str__(self):
        return f"{self.billing_name} ({self.company.name})"


class ManualInvoice(models.Model):
    """Admin-created invoice for manual billing (e.g. recurring Stripe charges)."""

    # --- Invoice metadata ---
    invoice_number = models.CharField(max_length=50, unique=True, blank=True, verbose_name=_('Invoice Number'),
                                      help_text=_('Auto-generated if left blank (e.g. INV-2026-0001)'))
    invoice_date = models.DateField(verbose_name=_('Invoice Date'))
    notes = models.TextField(blank=True, verbose_name=_('Internal Notes'))

    # --- Linked company (optional, used only for reference) ---
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name=_('Company (reference)'),
                                help_text=_('Select to auto-fill client fields from saved billing info'))

    # --- Seller fields (FROM side) ---
    seller_company_name = models.CharField(max_length=255, verbose_name=_('Seller – Company Name'))
    seller_tax_id = models.CharField(max_length=50, blank=True, verbose_name=_('Seller – Tax ID'))
    seller_address = models.CharField(max_length=255, blank=True, verbose_name=_('Seller – Address'))
    seller_city = models.CharField(max_length=100, blank=True, verbose_name=_('Seller – City'))
    seller_province = models.CharField(max_length=100, blank=True, verbose_name=_('Seller – Province'))
    seller_postal_code = models.CharField(max_length=20, blank=True, verbose_name=_('Seller – Postal Code'))
    seller_country = models.CharField(max_length=100, blank=True, default='España', verbose_name=_('Seller – Country'))
    seller_phone = models.CharField(max_length=30, blank=True, verbose_name=_('Seller – Phone'))
    seller_email = models.EmailField(blank=True, verbose_name=_('Seller – Email'))

    # --- Client fields (TO side) ---
    client_name = models.CharField(max_length=255, verbose_name=_('Client – Billing Name'))
    client_tax_id = models.CharField(max_length=50, blank=True, verbose_name=_('Client – Tax ID (NIE/NIF/VAT)'))
    client_address = models.CharField(max_length=255, blank=True, verbose_name=_('Client – Address'))
    client_city = models.CharField(max_length=100, blank=True, verbose_name=_('Client – City'))
    client_province = models.CharField(max_length=100, blank=True, verbose_name=_('Client – Province'))
    client_postal_code = models.CharField(max_length=20, blank=True, verbose_name=_('Client – Postal Code'))
    client_country = models.CharField(max_length=100, blank=True, default='España', verbose_name=_('Client – Country'))
    client_phone = models.CharField(max_length=30, blank=True, verbose_name=_('Client – Phone'))
    client_email = models.EmailField(blank=True, verbose_name=_('Client – Email'))

    # --- Line item ---
    description = models.CharField(max_length=255, verbose_name=_('Description'),
                                   help_text=_('e.g. Connect (1 month)'))
    period_start = models.DateField(null=True, blank=True, verbose_name=_('Period Start'))
    period_end = models.DateField(null=True, blank=True, verbose_name=_('Period End'))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_('Quantity'))
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name=_('Unit Price (€)'))

    # --- Payment ---
    payment_method = models.CharField(max_length=100, blank=True, verbose_name=_('Payment Method'),
                                      help_text=_('e.g. Mastercard - 4985'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Manual Invoice')
        verbose_name_plural = _('Manual Invoices')
        ordering = ['-invoice_date', '-created_at']

    def __str__(self):
        return f"{self.invoice_number} – {self.client_name} ({self.invoice_date})"

    @property
    def total(self):
        return self.unit_price * self.quantity

    def save(self, *args, **kwargs):
        # Auto-fill seller from SellerBillingInfo singleton if seller name is empty
        if not self.seller_company_name:
            seller = SellerBillingInfo.objects.filter(pk=1).first()
            if seller:
                self.seller_company_name = seller.company_name
                self.seller_tax_id = seller.tax_id
                self.seller_address = seller.address
                self.seller_city = seller.city
                self.seller_province = seller.province
                self.seller_postal_code = seller.postal_code
                self.seller_country = seller.country
                self.seller_phone = seller.phone
                self.seller_email = seller.email

        # Auto-fill client from ClientBillingInfo if client name is empty and company is set
        if not self.client_name and self.company:
            try:
                bi = self.company.billing_info
                self.client_name = bi.billing_name
                self.client_tax_id = bi.tax_id
                self.client_address = bi.address
                self.client_city = bi.city
                self.client_province = bi.province
                self.client_postal_code = bi.postal_code
                self.client_country = bi.country
                self.client_phone = bi.phone
                self.client_email = bi.email
            except ClientBillingInfo.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Auto-generate invoice number after we have a pk
        if not self.invoice_number:
            year = self.invoice_date.year
            self.invoice_number = f"RCP-{year}-{self.pk:04d}"
            ManualInvoice.objects.filter(pk=self.pk).update(invoice_number=self.invoice_number)

