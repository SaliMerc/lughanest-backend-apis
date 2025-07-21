from django.db import models
from lugha_app.models import MyUser
from django.utils import timezone

class Transactions(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    SUBSCRIPTION_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    student = models.ForeignKey(MyUser, on_delete=models.CASCADE, default=1, related_name='my_student')
    student_name=models.CharField(max_length=80, null=True, blank=True)
    student_email=models.CharField(max_length=30, null=True, blank=True)


    phone_number=models.CharField(max_length=16)
    subscription_type=models.CharField(max_length=10, null=True, blank=True, choices=SUBSCRIPTION_CHOICES, default='monthly')
    amount=models.DecimalField(decimal_places=2, max_digits=10)

    mpesa_code=models.CharField(max_length=50,null=True, blank=True)
    checkout_id=models.CharField(max_length=50,null=True, blank=True)
    result_description=models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,null=True, blank=True, default='pending')

    payment_date=models.DateTimeField(auto_now_add=True)
    subscription_start_date=models.DateTimeField(null=True, blank=True)
    subscription_end_date=models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.subscription_start_date is not None and
            self.subscription_end_date is not None and
            self.subscription_start_date <= now < self.subscription_end_date
        )

    def __str__(self):
        return f"{self.student.first_name} has paid {self.amount} for subscription {self.subscription_type}"

