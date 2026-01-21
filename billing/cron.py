def expire_subscriptions():
    from billing.models import Subscription
    from django.utils import timezone

    now = timezone.now()
    expired_subscriptions = Subscription.objects.filter(end_date__lt=now, is_active=True)

    for subscription in expired_subscriptions:
        subscription.is_active = False
        subscription.save()
        # Optionally, notify the user about expiration
        # send_expiration_email(subscription.user)