from rest_framework import serializers
from payment_app.models import Transactions, Subscriptions

class SubscriptionsSerializer(serializers.ModelSerializer):
    transaction_code=serializers.SerializerMethodField()
    transaction_amount=serializers.SerializerMethodField()
    transaction_status=serializers.SerializerMethodField()
    transaction_method=serializers.SerializerMethodField()
    class Meta:
        model = Subscriptions
        fields=['id','transaction_code','subscription_status','subscription_type','subscription_start_date','subscription_end_date','transaction_method','transaction_status','subscription_date','transaction_amount']
    
    def get_transaction_code(self, obj):
        return obj.transaction_id.transaction_code

    def get_transaction_amount(self, obj):
        return obj.transaction_id.amount
    
    def get_transaction_method(self, obj):
        return obj.transaction_id.payment_type
    
    def get_transaction_status(self, obj):
        return obj.transaction_id.transaction_status


