from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transactions
from django.utils import timezone
from dateutil.relativedelta import relativedelta

@receiver(post_save, sender=Transactions)
def handle_subscription_status(sender, instance, **kwargs):
    """
    Signal to handle all subscription calculations and status updates
    """
    if instance.status != 'completed':
        return
    
    # Calculate subscription period if this is a new completed payment
    if not instance.subscription_start_date:
        instance.subscription_start_date = timezone.now()
        
        """Calculate end date based on subscription type"""
        if instance.subscription_type == 'monthly':
            instance.subscription_end_date = instance.subscription_start_date + relativedelta(months=1)
        elif instance.subscription_type == 'yearly':
            instance.subscription_end_date = instance.subscription_start_date + relativedelta(years=1)
        
        """Mark as active since it's a new subscription"""
        instance.subscription_active = True        
        instance.save()
    
    # Check and update active status for existing subscriptions"""
    else:
        current_time = timezone.now()
        is_currently_active = instance.subscription_end_date and instance.subscription_end_date > current_time
        
        # Only update if status has changed
        if instance.subscription_active != is_currently_active:
            instance.subscription_active = is_currently_active
            instance.save()
    
    """Handle overlapping subscriptions (prevent multiple active subscriptions for same user)"""
    if instance.subscription_active:
        overlapping_subs = Transactions.objects.filter(
            student=instance.student,
            subscription_active=True,
            subscription_type=instance.subscription_type
        ).exclude(id=instance.id)
        
        """Deactivate any overlapping subscriptions"""
        if overlapping_subs.exists():
            overlapping_subs.update(is_active=False)