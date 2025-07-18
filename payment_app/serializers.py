from rest_framework import serializers
from payment_app.models import Transactions

class TransactionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transactions
        fields = '__all__'

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['student'] = request.user 

            if not validated_data.get('incident_location'):
                user_location = request.user.unit_number.unit_name
                if user_location:
                    validated_data['incident_location'] = user_location 
                else:
                    validated_data['incident_location'] = "Not Set"
        return super().create(validated_data)

