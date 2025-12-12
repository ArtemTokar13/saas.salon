from django.contrib import admin
from .models import Plan, Subscription, Transaction


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'monthly_price', 'is_active', 'display_pricing']
    search_fields = ['name']
    list_filter = ['is_active']
    
    def display_pricing(self, obj):
        """Display all pricing tiers"""
        return (
            f"Monthly: ${obj.get_price_for_period('monthly')} | "
            f"3mo: ${obj.get_price_for_period('three_months')} | "
            f"6mo: ${obj.get_price_for_period('six_months')} | "
            f"Year: ${obj.get_price_for_period('yearly')}"
        )
    display_pricing.short_description = 'Pricing Tiers'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['company', 'plan', 'billing_period', 'calculated_price', 'start_date', 'end_date', 'is_active']
    list_filter = ['plan', 'billing_period', 'is_active', 'start_date', 'end_date']
    search_fields = ['company__name']
    
    def calculated_price(self, obj):
        """Display the calculated price for this subscription"""
        return f"${obj.price} ({obj.get_billing_period_display()})"
    calculated_price.short_description = 'Total Price'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'transaction_date', 'transaction_id']
    list_filter = ['transaction_date']
    search_fields = ['transaction_id']
