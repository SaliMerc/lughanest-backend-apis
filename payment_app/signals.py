from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transactions
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from django.core.mail import send_mail
from django.conf import settings

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
    
    notify_user_payment_success(instance)


def notify_user_payment_success(transaction):
    """Send confirmation email to the user about successful subscription"""
    user = transaction.student
    if not user.email:
        return

    subject = "Your Subscription is Confirmed!"
    message = f"""
    Dear {user.last_name},

    Thank you for your payment. Your {transaction.subscription_type} subscription has been successfully activated.

    ✅ Subscription Details:
    - Type: {transaction.subscription_type.title()}
    - Start Date: {transaction.subscription_start_date.strftime('%Y-%m-%d')}
    - End Date: {transaction.subscription_end_date.strftime('%Y-%m-%d')}
    - Status: {transaction.status.title()}

    You now have full access to your subscription benefits.

    If you have any questions, feel free to contact us.

    Best regards,  
    LughaNest Team
    """

    send_mail(
        subject=subject,
        message=message.strip(),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False
    )


def notify_user_payment_failed(transaction):
    """Send email to the user if their payment failed."""
    user = transaction.student
    if not user.email:
        return

    subject = "Payment Failed Subscription Not Activated"
    message = f"""
    Dear {user.last_name},

    Unfortunately, your payment for the {transaction.subscription_type.title()} subscription was not successful.

    ❌ Payment Details:
    - Type: {transaction.subscription_type.title()}
    - Amount: {transaction.amount}
    - Phone: {transaction.phone_number}
    - Status: {transaction.status.title()}
    - Reason: {transaction.result_description or "Unknown"}

    Since the transaction did not complete, your subscription has not been activated.

    Please try again or contact support if the issue persists.

    Best regards,  
    LughaNest Team
    """

    send_mail(
        subject=subject,
        message=message.strip(),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False
    )

