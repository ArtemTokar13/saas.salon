from django import template

register = template.Library()


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
    monthly_total = plan.monthly_price * {
        'monthly': 1,
        'three_months': 3,
        'six_months': 6,
        'yearly': 12,
    }.get(period, 1)
    
    actual_price = plan.get_price_for_period(period)
    savings = monthly_total - actual_price
    return savings if savings > 0 else 0
