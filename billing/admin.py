from django.contrib import admin
from django.utils.html import format_html
from .models import Plan, Subscription, Transaction


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_monthly_price', 'base_workers', 'additional_worker_price', 'trial_days', 'is_active', 'has_stripe_config']
    search_fields = ['name']
    list_filter = ['is_active']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Pricing Configuration', {
            'fields': ('base_workers', 'base_monthly_price', 'additional_worker_price', 'trial_days'),
            'description': 'Set base price for included workers, price per additional worker, and trial period'
        }),
        ('Legacy Fields (Deprecated)', {
            'fields': ('max_number_of_staff', 'monthly_price', 'features'),
            'classes': ('collapse',)
        }),
        ('Stripe Configuration', {
            'fields': ('stripe_product_id', 'stripe_price_id_monthly', 'stripe_price_id_three_months', 
                      'stripe_price_id_six_months', 'stripe_price_id_yearly', 'stripe_additional_worker_price_id'),
            'classes': ('collapse',)
        }),
    )
    
    def has_stripe_config(self, obj):
        """Check if Stripe is fully configured"""
        if obj.stripe_product_id and obj.stripe_price_id_monthly:
            return format_html('<span style="color: green;">✓ Configured</span>')
        return format_html('<span style="color: red;">✗ Not Configured</span>')
    has_stripe_config.short_description = 'Stripe Status'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['company', 'plan', 'num_workers', 'billing_period', 'status', 'trial_status', 'calculated_price', 'start_date', 'end_date', 'is_active']
    list_filter = ['plan', 'billing_period', 'status', 'is_active', 'start_date', 'end_date']
    search_fields = ['company__name', 'stripe_customer_id', 'stripe_subscription_id']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id', 'stripe_latest_invoice_id']
    fieldsets = (
        ('Subscription Details', {
            'fields': ('company', 'plan', 'num_workers', 'billing_period', 'start_date', 'end_date', 'trial_end', 'is_active', 'status')
        }),
        ('Stripe Information', {
            'fields': ('stripe_customer_id', 'stripe_subscription_id', 'stripe_latest_invoice_id', 
                      'cancel_at_period_end', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )
    
    def trial_status(self, obj):
        """Display trial status"""
        if obj.is_trial:
            return format_html('<span style="color: blue;">🎁 Trial until {}</span>', obj.trial_end)
        return '-'
    trial_status.short_description = 'Trial'
    
    def calculated_price(self, obj):
        """Display the calculated price for this subscription"""
        breakdown = obj.pricing_breakdown
        price_display = f'${obj.price}'
        if obj.is_trial:
            price_display = f'<del>${obj.price}</del> <strong style="color: green;">FREE (Trial)</strong>'
        return format_html(
            '{} <small>(${}/mo × {} workers)</small>',
            price_display,
            breakdown['total_monthly'],
            obj.num_workers
        )
    calculated_price.short_description = 'Total Price'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'subscription', 'amount', 'payment_status', 'transaction_date']
    list_filter = ['payment_status', 'transaction_date']
    search_fields = ['transaction_id', 'stripe_payment_intent_id', 'stripe_invoice_id', 'stripe_charge_id']
    readonly_fields = ['stripe_payment_intent_id', 'stripe_invoice_id', 'stripe_charge_id']
    fieldsets = (
        ('Transaction Details', {
            'fields': ('subscription', 'amount', 'transaction_id', 'payment_status', 'transaction_date')
        }),
        ('Stripe Information', {
            'fields': ('stripe_payment_intent_id', 'stripe_invoice_id', 'stripe_charge_id'),
            'classes': ('collapse',)
        }),
    )
