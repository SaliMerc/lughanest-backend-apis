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

@receiver(post_save, sender=Transactions)
def notify_user_payment_status(sender, instance, **kwargs):
    """Send email to user based on transaction status (success or failed or pending)"""
    if getattr(instance, '_email_sent', False):
        return

    instance._email_sent = True 

    user = instance.student

    if not user or not user.email:
        return

    if instance.status == "completed":
        subject = "Your Subscription is Confirmed!"
        message = f"""
        Dear {user.last_name},

        Thank you for your payment. Your {instance.subscription_type} subscription has been successfully activated.

        ✅ Subscription Details:
        - Type: {instance.subscription_type.title()}
        - Start Date: {instance.subscription_start_date.strftime('%Y-%m-%d')}
        - End Date: {instance.subscription_end_date.strftime('%Y-%m-%d')}
        - Status: {instance.status.title()}

        You now have full access to your subscription benefits.

        If you have any questions, feel free to contact us.

        Best regards,  
        LughaNest Team
        """
    elif instance.status == "failed":
        # Failed email
        subject = "Payment Failed – Subscription Not Activated"
        message = f"""
        Dear {user.last_name},

        Unfortunately, your payment for the {instance.subscription_type.title()} subscription was not successful.

        ❌ Payment Details:
        - Type: {instance.subscription_type.title()}
        - Amount: {instance.amount}
        - Phone: {instance.phone_number}
        - Status: {instance.status.title()}
        - Reason: {instance.result_description or "Unknown"}

        Since the transaction did not complete, your subscription has not been activated.

        Please try again or contact support if the issue persists.

        Best regards,  
        LughaNest Team
        """
    
    elif instance.status.lower() == "pending":
        subject = "You have initiated a payment"
        message = f"""
        Dear {user.last_name},

        We have received your payment initiation request for the {instance.subscription_type.title()} subscription.

        ⏳ Payment Status: Pending

        Your transaction is currently being processed. It may take a few moments to confirm the payment.

        📄 Transaction Summary:
        - Type: {instance.subscription_type.title()}
        - Amount: {instance.amount}
        - Phone: {instance.phone_number}
        - Status: {instance.status.title()}

        We will notify you once your subscription is successfully activated.

        If you have any questions or did not initiate this transaction, please contact our support team immediately.

        Best regards,  
        LughaNest Team
        """
    else:
        return

    send_mail(
        subject=subject,
        message=message.strip(),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[user.email],
        fail_silently=False
    )
