from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Transactions, Subscriptions
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
    if instance.transaction_status != 'completed':
        return
    
    subscription, subscription_created=Subscriptions.objects.get_or_create(
        transaction_id=instance,
        student_id=instance.student_id,
        student_name=instance.student_name,
        subscription_type=instance.transaction_subscription_type
    )

    """If not already initialized"""
    if subscription_created or not subscription.subscription_start_date:
        now = timezone.now()

        """Find existing active or future subscriptions of the same type"""
        existing_subscription = Subscriptions.objects.filter(
            student_id=instance.student_id,
            transaction_id__transaction_status='completed',
            subscription_end_date__gte=now
        ).exclude(id=subscription.id).order_by('-subscription_end_date').first()

        """Start after current active subscription if it exists"""
        if existing_subscription:
            subscription.subscription_start_date = existing_subscription.subscription_end_date
        else:
            subscription.subscription_start_date = now

        """Calculate end date"""
        if subscription.subscription_type == 'monthly':
            subscription.subscription_end_date = subscription.subscription_start_date + relativedelta(months=1)
        elif subscription.subscription_type == 'yearly':
            subscription.subscription_end_date = subscription.subscription_start_date + relativedelta(years=1)
    subscription.subscription_status = 'active'
    subscription.save()

@receiver(post_save, sender=Transactions)
def notify_user_payment_status(sender, instance, **kwargs):
    """Send email to user based on transaction status (success or failed or pending)"""
    if getattr(instance, '_email_sent', False):
        return

    instance._email_sent = True 

    user = instance.student_id

    if not user or not user.email:
        return
    
    if instance.transaction_status == "completed":
        subscription=Subscriptions.objects.get(
        transaction_id=instance,
        student_id=instance.student_id
    )
         
        subject = "Your Subscription is Confirmed!"
        message = f"""
        Dear {user.last_name},

        Thank you for your payment. Your {instance.transaction_subscription_type.title()} subscription has been successfully activated.

        ✅ Subscription Details:
        - Type: {instance.transaction_subscription_type.title()}
        - Start Date: {subscription.subscription_start_date.strftime('%Y-%m-%d')}
        - End Date: {subscription.subscription_end_date.strftime('%Y-%m-%d')}
        - Payment Status: {instance.transaction_status.title()}

        You now have full access to your subscription benefits.

        If you have any questions, feel free to contact us.

        Best regards,  
        LughaNest Team
        """
    elif instance.transaction_status == "failed":
        # Failed email
        subject = "Payment Failed – Subscription Not Activated"
        message = f"""
        Dear {user.last_name},

        Unfortunately, your payment for the {instance.transaction_subscription_type.title()} subscription was not successful.

        ❌ Payment Details:
        - Type: {instance.transaction_subscription_type.title()}
        - Amount: {instance.amount}
        - Phone: {instance.phone_number}
        - Payment Status: {instance.transaction_status.title()}
        - Reference Number: {instance.transaction_reference_number}

        Since the transaction did not complete, your subscription has not been activated.

        Please try again or contact support if the issue persists.

        Best regards,  
        LughaNest Team
        """
    
    elif instance.transaction_status.lower() == "pending":
        subject = "You have initiated a payment"
        message = f"""
        Dear {user.last_name},

        We have received your payment initiation request for the {instance.transaction_subscription_type.title()} subscription.

        ⏳ Payment Status: Pending

        Your transaction is currently being processed. It may take a few moments to confirm the payment.

        📄 Transaction Summary:
        - Type: {instance.transaction_subscription_type.title()}
        - Amount: {instance.amount}
        - Phone: {instance.phone_number}
        - Status: {instance.transaction_status.title()}
        - Reference Number: {instance.transaction_reference_number}

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
