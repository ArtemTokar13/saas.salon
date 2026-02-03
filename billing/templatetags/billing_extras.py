from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def get_localized_features(plan):
    """Get features for the current language"""
    if not plan.features:
        return []
    
    current_lang = get_language()
    
    # If features is a dict with language keys
    if isinstance(plan.features, dict):
        # Try current language first, then fall back to 'en', then any available language
        features = plan.features.get(current_lang) or plan.features.get('en') or list(plan.features.values())[0] if plan.features else []
        return features if isinstance(features, list) else []
    
    # If features is a simple list (backward compatibility)
    elif isinstance(plan.features, list):
        return plan.features
    
    return []


@register.filter
def get_period_price(plan, period):
    """Template filter to get price for a specific billing period"""
    return plan.get_price_for_period(period)


@register.filter
def get_period_discount(period):
    """Get the discount percentage for a billing period"""
    discounts = {
        'monthly': 0,
        'three_months': 10,
        'six_months': 20,
        'yearly': 40,
    }
    return discounts.get(period, 0)


@register.filter
def get_period_savings(plan, period):
    """Calculate savings compared to monthly billing"""
    monthly_total = plan.base_monthly_price * {
        'monthly': 1,
        'three_months': 3,
        'six_months': 6,
        'yearly': 12,
    }.get(period, 1)
    
    actual_price = plan.get_price_for_period(period)
    savings = monthly_total - actual_price
    return savings if savings > 0 else 0
