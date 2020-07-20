import time

import jwt
from django.conf import settings
from jose import jwt
from rest_framework.permissions import BasePermission

client = settings.PLAID_CLIENT


class WebHookPermissions(BasePermission):

    def has_permission(self, request, view):
        token = request.headers["Plaid-Verification"]
        headers = jwt.get_unverified_header(token)
        if headers["alg"] != "ES256":
            return False
        key_id = headers["kid"]
        response = client.Webhooks.get_verification_key(key_id)
        key = response["key"]
        try:
            claims = jwt.decode(token, key, algorithms=['ES256'])
        except jwt.JWTError:
            return False
        if claims["iat"] < time.time() - 5 * 60:
            return False
        return True
