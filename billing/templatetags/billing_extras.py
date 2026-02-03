from django import template
from django.utils.translation import get_language

register = template.Library()


@register.filter
def get_localized_description(description):
    """Get description for the current language"""
    if not description:
        return ""
    
    current_lang = get_language()
    
    # If description is a dict with language keys
    if isinstance(description, dict):
        # Try current language first, then fall back to 'en', then any available language
        localized_desc = description.get(current_lang) or description.get('en') or list(description.values())[0] if description else ""
        return localized_desc if isinstance(localized_desc, str) else ""
    
    # If description is a simple string (backward compatibility)
    elif isinstance(description, str):
        return description
    
    return ""


@register.filter
def get_localized_features(features):
    """Get features for the current language"""
    if not features:
        return []
    
    current_lang = get_language()
    
    # If features is a dict with language keys
    if isinstance(features, dict):
        # Try current language first, then fall back to 'en', then any available language
        localized_features = features.get(current_lang) or features.get('en') or list(features.values())[0] if features else []
        return localized_features if isinstance(localized_features, list) else []
    
    # If features is a simple list (backward compatibility)
    elif isinstance(features, list):
        return features
    
    return []


@register.filter
def get_period_price(plan, period):
    """Template filter to get price for a specific billing period"""
    return plan.get_price_for_period(period)


@register.filter
def get_monthly_equivalent(plan, period):
    """Template filter to get the effective monthly price for a billing period"""
    return plan.get_monthly_equivalent(period)


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
