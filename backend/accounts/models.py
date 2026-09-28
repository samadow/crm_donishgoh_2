from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    class Language(models.TextChoices):
        TAJIK = "tj", "Тоҷикӣ"
        RUSSIAN = "ru", "Русский"
        ENGLISH = "en", "English"

    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT, db_index=True)
    preferred_language = models.CharField(max_length=2, choices=Language.choices, default=Language.RUSSIAN)
    avatar_color = models.CharField(max_length=7, default="#2f6bff")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.email

    def __str__(self):
        return self.display_name

