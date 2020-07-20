import datetime
import logging
import os

from celery import Celery
from django.apps import apps
from django.conf import settings
from django.db import transaction
from plaid.errors import PlaidError

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plaid_app.settings')

app = Celery('plaid_app')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

client = settings.PLAID_CLIENT
logger = logging.getLogger(__name__)


@app.task(name="delete_transactions")
@transaction.atomic
def delete_transactions(transaction_list):
    transaction_model = apps.get_model('plaid_app', 'Transaction')
    transaction_model.objects.filter(id__in=transaction_list).delete()


@transaction.atomic
def update_transactions(transaction_model, transaction_object_list):
    transaction_model.objects.bulk_update(
        transaction_object_list,
        ["name", "date", "amount", "account_id", "type"]
    )


@transaction.atomic
def insert_transactions(transaction_model, transaction_object_list):
    transaction_model.objects.bulk_create(transaction_object_list)


@app.task(name="fetch_transactions")
def fetch_transactions(item_id, look_back_days=30):
    logger.info(f"fetch_transactions {item_id} {look_back_days}")
    user_items_model = apps.get_model('plaid_app', 'UserItem')
    user_item = user_items_model.objects.get(pk=item_id)
    access_token = user_item.access_token

    current_time = datetime.datetime.now()
    end_date = '{:%Y-%m-%d}'.format(current_time)
    start_date = '{:%Y-%m-%d}'.format(current_time - datetime.timedelta(look_back_days))

    try:
        response = client.Transactions.get(
            access_token, start_date, end_date
        )
    except PlaidError as e:
        logger.error({
            'error': {
                'display_message': e.display_message,
                'error_code': e.code,
                'error_type': e.type
            }
        })
        return

    transactions = response["transactions"]
    transaction_model = apps.get_model('plaid_app', 'Transaction')
    transaction_objects = []
    for transaction in transactions:
        transaction_objects.append(transaction_model(
            name=transaction["name"],
            date=transaction["date"],
            amount=transaction["amount"],
            id=transaction["transaction_id"],
            account_id=transaction["account_id"],
            type=transaction["transaction_type"],
        ))

    transaction_ids = transaction_model.objects.filter(
        account__user_item__id=item_id
    ).values_list("id", flat=True)

    create_list = []
    update_list = []

    for transaction_object in transaction_objects:
        if transaction_object.id in transaction_ids:
            update_list.append(transaction_object)
        else:
            create_list.append(transaction_object)

    update_transactions(transaction_model, update_list)
    insert_transactions(transaction_model, create_list)


@app.task(name="fetch_accounts")
def fetch_accounts(access_token, user_item):
    logger.info(f"fetch_accounts {user_item}")
    try:
        response = client.Accounts.get(access_token)
    except PlaidError as e:
        logger.error({
            'error': {
                'display_message': e.display_message,
                'error_code': e.code,
                'error_type': e.type
            }
        })
        return

    accounts = response["accounts"]
    for account in accounts:
        account.pop("mask", None)
        account_id = account.pop("account_id")
        balances = account.pop("balances", {})

        account["id"] = account_id
        account["user_item_id"] = user_item
        account["balance"] = balances["current"]
        account["iso_currency_code"] = balances["iso_currency_code"]

    account_model = apps.get_model('plaid_app', 'Account')
    account_model.objects.bulk_create([account_model(**data) for data in accounts])

    # fetch_transactions.delay(user_item)


@app.task(name="fetch_item_data")
def fetch_item_data(item_id, access_token):
    logger.info(f"fetch_item_data {item_id}")
    response = client.Item.get(access_token)
    institution_id = response["item"]["item_id"]

    user_items_model = apps.get_model('plaid_app', 'UserItem')
    user_item = user_items_model.objects.get(pk=item_id)
    user_item.institution_id = institution_id
    user_item.save()

    fetch_accounts.delay(access_token, item_id)


@app.task(name="fetch_access_token")
def fetch_access_token(user_id, public_token):
    logger.debug(f"fetch_access_token {user_id}")
    try:
        response = client.Item.public_token.exchange(public_token)
    except PlaidError as e:
        logger.error({
            'error': {
                'display_message': e.display_message,
                'error_code': e.code,
                'error_type': e.type
            }
        })
        return

    access_token = response["access_token"]
    item_id = response["item_id"]

    user_items_model = apps.get_model('plaid_app', 'UserItem')
    user_items_model.objects.create(
        user_id=user_id,
        access_token=access_token,
        id=item_id
    )
    fetch_item_data.delay(item_id, access_token)
