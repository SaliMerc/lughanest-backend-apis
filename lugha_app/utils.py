from django.utils import timezone
from payment_app.models import Subscriptions

def has_active_subscription(user):
    """
    Check if the given user has an active subscription.
    True if the user has an active subscription, False otherwise.
    """
    now = timezone.now()
    active_subscriptions = Subscriptions.objects.filter(
        student_id=user,  
        transaction_id__transaction_status='completed',
        subscription_start_date__lte=now,
        subscription_end_date__gte=now
    )
    return active_subscriptions.exists()
