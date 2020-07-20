import logging

from django.contrib.auth import get_user_model
from rest_framework import permissions
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .celery import fetch_access_token, fetch_transactions, delete_transactions
from .models import Account, Transaction
from .permissions import WebHookPermissions
from .serializers import UserSerializer, UserTokenSerializer, AccountSerializer, TransactionSerializer, \
    TrasactionWebHookSerializer

logger = logging.getLogger(__name__)

UserModel = get_user_model()


class CreateUserView(CreateAPIView):
    model = UserModel
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer


class UserToken(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserTokenSerializer

    def perform_create(self, serializer):
        user_id = self.request.user.pk
        public_token = serializer.validated_data["public_token"]
        fetch_access_token.delay(user_id, public_token)


class AccountViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        user = self.request.user
        return Account.objects.filter(user_item__user=user)


class TransactionViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(account__user_item__user=user)


class TransactionWebHook(CreateAPIView):
    permission_classes = [WebHookPermissions]
    serializer_class = TrasactionWebHookSerializer

    def perform_create(self, serializer):
        code = serializer.validated_data["webhook_code"]
        item_id = serializer.validated_data["item_id"]
        logger.debug(f"Invoked for {code} {item_id}")

        if code == "INITIAL_UPDATE" or code == "DEFAULT_UPDATE":
            fetch_transactions.delay(item_id)
            return
        if code == "HISTORICAL_UPDATE":
            fetch_transactions.delay(item_id, look_back_days=400)
            return
        if code == "TRANSACTIONS_REMOVED":
            transaction_list = serializer.validated_data["removed_transactions"]
            delete_transactions.delay(transaction_list)
            return
