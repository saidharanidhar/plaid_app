from django.contrib.auth import get_user_model
from rest_framework import serializers

from plaid_app.models import Account, Transaction, UserItem

UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserModel
        fields = ('id', 'username', 'password', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = UserModel.objects.create(
            **validated_data
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class UserTokenSerializer(serializers.Serializer):
    public_token = serializers.CharField(max_length=100)


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class TrasactionWebHookSerializer(serializers.Serializer):
    webhook_type = serializers.CharField(max_length=20, required=True)
    webhook_code = serializers.CharField(max_length=20, required=True)
    item_id = serializers.CharField(max_length=50, required=True)
    removed_transactions = serializers.ListField(child=serializers.CharField(), required=False)
