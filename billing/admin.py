from django.contrib import admin
from .models import Plan, Subscription, Transaction


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price']
    search_fields = ['name']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['company', 'plan', 'start_date', 'end_date', 'is_active']
    list_filter = ['plan', 'is_active', 'start_date', 'end_date']
    search_fields = ['company__name']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'transaction_date', 'transaction_id']
    list_filter = ['transaction_date']
    search_fields = ['transaction_id']
