from django.contrib import admin
from payment_app.models import Transactions, Subscriptions


@admin.register(Transactions)
class TransactionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student_id','payment_type', 'student_name', 'student_email', 'phone_number',
        'amount', 'transaction_status', 'payment_date'
    )
    list_filter = ('transaction_status', 'payment_date')
    search_fields = (
        'student_id__username', 'student_name', 'student_email',
        'transaction_code', 'transaction_reference_number', 'phone_number'
    )

@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student_name', 'subscription_type', 'subscription_status',
        'subscription_start_date', 'subscription_end_date', 'transaction_id'
    )
    list_filter = ('subscription_type', 'subscription_status', 'subscription_start_date')
    search_fields = (
        'student_name', 'transaction_id__transaction_code', 'transaction_id__phone_number'
    )

  
