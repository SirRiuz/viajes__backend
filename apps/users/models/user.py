# Django
from django.contrib.auth.models import AbstractUser
from django.db import models

# Models
from apps.default.models.base_model import BaseModel


class User(BaseModel, AbstractUser):
    pass
