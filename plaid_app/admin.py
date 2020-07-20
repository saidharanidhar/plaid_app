from django.contrib import admin

from .models import User, UserItem, Account, Transaction

admin.site.register(User)
admin.site.register(UserItem)
admin.site.register(Account)
admin.site.register(Transaction)
