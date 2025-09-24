# Django
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# Models
from apps.users.models.user import User


@admin.register(User)
class UserAdmin(UserAdmin):
    pass
