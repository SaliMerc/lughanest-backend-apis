from django.contrib import admin
from payment_app.models import Transactions


@admin.register(Transactions)
class TransactionsAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'student', 'phone_number', 'subscription_type', 'amount', 'status',
        'subscription_start_date', 'subscription_end_date', 'subscription_active'
    )
    list_filter = ('status', 'subscription_type', 'subscription_active', 'subscription_start_date')
    search_fields = (
        'student__username', 'student__first_name', 'student__last_name',
        'mpesa_code', 'checkout_id', 'phone_number'
    )
  
