from django.conf import settings
from django.db import models
from django.utils import timezone


class PartCategory(models.Model):
    name = models.CharField(max_length=60)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=40, default="bi-box", help_text="Bootstrap icon class")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "part categories"

    def __str__(self):
        return self.name


class Part(models.Model):
    sku = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    category = models.ForeignKey(PartCategory, on_delete=models.PROTECT, related_name="parts")
    brand = models.CharField(max_length=40)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_qty = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    is_universal = models.BooleanField(default=False, help_text="Fits every vehicle")
    compatible_models = models.ManyToManyField("inventory.VehicleModel", blank=True, related_name="parts")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def is_low_stock(self):
        return self.stock_qty <= self.reorder_level

    @property
    def in_stock(self):
        return self.stock_qty > 0


class CartItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "part"], name="uniq_cart_part")]

    @property
    def line_total(self):
        return self.part.price * self.quantity


class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENT = "PERCENT", "Percent"
        FLAT = "FLAT", "Flat amount"

    code = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=120, blank=True)
    discount_type = models.CharField(max_length=7, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    min_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Awaiting payment"
        PAID = "PAID", "Paid"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.PENDING)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_address = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk}"

    @property
    def number(self):
        return f"CC-{self.pk:05d}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    part = models.ForeignKey(Part, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity
