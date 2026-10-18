# Django
from django.contrib.auth.models import AbstractUser

# Models
from app.models.base_model import BaseModel


class User(BaseModel, AbstractUser):
    class Meta:
        # Every table keeps the name of the old per-app layout (apps/users,
        # apps/driver…), so existing databases need no data migration.
        db_table = "users_user"
