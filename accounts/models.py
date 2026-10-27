from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        SALES = "SALES", "Sales Executive"
        MECHANIC = "MECHANIC", "Mechanic"
        CUSTOMER = "CUSTOMER", "Customer"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=60, blank=True)

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_sales(self):
        return self.role == self.Role.SALES

    @property
    def is_mechanic(self):
        return self.role == self.Role.MECHANIC

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        parts = [self.first_name, self.last_name]
        letters = "".join(p[0] for p in parts if p)
        return (letters or self.username[:2]).upper()
