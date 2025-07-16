from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transactions
from django.utils import timezone
from dateutil.relativedelta import relativedelta

@receiver(post_save, sender=Transactions)
def handle_subscription_status(sender, instance, **kwargs):
    """
    Signal to handle all subscription calculations and status updates.
    If user already has an active subscription, carry forward the new one.
    """
    if instance.status != 'completed':
        return

    """If not already initialized"""
    if not instance.subscription_start_date:
        now = timezone.now()

        """Find existing active or future subscriptions of the same type"""
        existing_sub = Transactions.objects.filter(
            student=instance.student,
            subscription_type=instance.subscription_type,
            status='completed',
            subscription_end_date__gte=now
        ).exclude(id=instance.id).order_by('-subscription_end_date').first()

        """Start after current active subscription if it exists"""
        if existing_sub:
            instance.subscription_start_date = existing_sub.subscription_end_date
        else:
            instance.subscription_start_date = now

        """Calculate end date"""
        if instance.subscription_type == 'monthly':
            instance.subscription_end_date = instance.subscription_start_date + relativedelta(months=1)
        elif instance.subscription_type == 'yearly':
            instance.subscription_end_date = instance.subscription_start_date + relativedelta(years=1)

        """Check if it's active now"""
        instance.subscription_active = instance.subscription_start_date <= now < instance.subscription_end_date
        instance.save()
    else:
        """Check if current subscription is active"""
        now = timezone.now()
        is_currently_active = instance.subscription_end_date and instance.subscription_end_date > now
        if instance.subscription_active != is_currently_active:
            instance.subscription_active = is_currently_active
            instance.save()
