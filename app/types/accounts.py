# Libs
from graphene_django.types import DjangoObjectType

# Models
from app.models.users import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")

    def resolve_username(self, info):
        return self.username.capitalize()
