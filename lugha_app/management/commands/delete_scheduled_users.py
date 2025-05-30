from django.core.management.base import BaseCommand
from django.utils import timezone
from lugha_app.models import MyUser

class Command(BaseCommand):
    help = 'Delete users scheduled for deletion'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        users_to_delete = MyUser.objects.filter(scheduled_deletion_date__lte=now)
        count = users_to_delete.count()
        users_to_delete.delete()
        self.stdout.write(f"Deleted {count} user(s).")
