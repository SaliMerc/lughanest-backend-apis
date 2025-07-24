from django.db import models
from lugha_app.models import MyUser
from django.utils import timezone

SUBSCRIPTION_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
class Transactions(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    student_id = models.ForeignKey(MyUser, on_delete=models.CASCADE, default=1, related_name='transactions')
    student_name=models.CharField(max_length=80, null=True, blank=True)
    student_email=models.CharField(max_length=30, null=True, blank=True)

    phone_number=models.CharField(max_length=16)
    amount=models.DecimalField(decimal_places=2, max_digits=10)

    transaction_subscription_type=models.CharField(max_length=50, null=True, blank=True, choices=SUBSCRIPTION_CHOICES, default='monthly')
    payment_type=models.CharField(max_length=50,null=True, blank=True)
    transaction_code=models.CharField(max_length=50,null=True, blank=True)
    transaction_reference_number=models.CharField(max_length=50,null=True, blank=True)
    transaction_result_description=models.TextField(null=True, blank=True)
    transaction_status = models.CharField(max_length=20, choices=STATUS_CHOICES,null=True, blank=True, default='pending')

    transaction_date=models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.student_id.first_name} has paid {self.amount}"


class Subscriptions(models.Model):
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
     
    transaction_id=models.ForeignKey(Transactions, on_delete=models.SET_NULL, related_name='subscriptions', null=True, blank=True)

    student_id=models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='student_subscriptions', null=True, blank=True)
    student_name=models.CharField(max_length=80, null=True, blank=True)

    subscription_type=models.CharField(max_length=10, null=True, blank=True)
    subscription_status=models.CharField(max_length=10, null=True, blank=True, choices=SUBSCRIPTION_STATUS_CHOICES, default='inactive')

    subscription_start_date=models.DateTimeField(null=True, blank=True)
    subscription_end_date=models.DateTimeField(null=True, blank=True)
    subscription_date=models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    def __str__(self):
        return self.subscription_status
    