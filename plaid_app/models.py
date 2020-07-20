from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class UserItem(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    user = models.ForeignKey(User, related_name="user_items", on_delete=models.CASCADE)
    access_token = models.CharField(max_length=100, null=True)
    institution_id = models.CharField(max_length=100, null=True)


class Account(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    balance = models.FloatField()
    name = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    subtype = models.CharField(max_length=50)
    iso_currency_code = models.CharField(max_length=10)
    official_name = models.CharField(max_length=100, null=True)
    user_item = models.ForeignKey(UserItem, related_name="accounts", on_delete=models.CASCADE)


class Transaction(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    account = models.ForeignKey(Account, related_name="transactions", on_delete=models.CASCADE)
    type = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    amount = models.FloatField()
    date = models.DateField()
