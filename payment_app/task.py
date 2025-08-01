from django.utils import timezone
from payment_app.models import Subscriptions
from lugha_app.models import MyUser
from celery import shared_task

@shared_task
def my_subscription_inactivation_cron_job():
    now = timezone.now()
    expired_subscriptions = Subscriptions.objects.filter(
        subscription_end_date__lte=now,
        subscription_status='active'
    )

    count = expired_subscriptions.update(subscription_status='inactive')

    print(f"{count} subscriptions were inactivated.")

@shared_task
def delete_scheduled_users_cron_job():
    now = timezone.now()
    users_to_delete = MyUser.objects.filter(scheduled_deletion_date__lte=now)
    count = users_to_delete.count()
    users_to_delete.delete()

    print(f"{count} users were deleted.")