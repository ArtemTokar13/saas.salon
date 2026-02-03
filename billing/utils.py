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
            features = subscription.plan.features or {}
            # Check if WhatsApp exists in any language
            if isinstance(features, dict):
                for lang_features in features.values():
                    if isinstance(lang_features, list) and 'WhatsApp' in lang_features:
                        return True
            elif isinstance(features, list) and 'WhatsApp' in features:
                # Fallback for old list format
                return True
    except Exception as e:
        print(f"Error checking WhatsApp feature for company {company.id}: {e}")
    return False