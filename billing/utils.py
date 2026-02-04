from billing.models import Subscription


def has_whatsapp_feature(company):
    """Check if company has WhatsApp feature in their subscription plan"""
    try:
        subscription = Subscription.objects.filter(
            company=company, 
            is_active=True, 
            status='active'
        ).first()
        if subscription and subscription.plan:
            return subscription.plan.whatsapp_included
    except Exception as e:
        print(f"Error checking WhatsApp feature for company {company.id}: {e}")
    return False