from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Make(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    country = models.CharField(max_length=40, blank=True)
    logo = models.CharField(max_length=40, blank=True, help_text="File name in static/brands/, without .svg")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    class BodyType(models.TextChoices):
        HATCHBACK = "HATCHBACK", "Hatchback"
        SEDAN = "SEDAN", "Sedan"
        SUV = "SUV", "SUV"
        MUV = "MUV", "MUV"
        PICKUP = "PICKUP", "Pickup"

    make = models.ForeignKey(Make, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=60)
    body_type = models.CharField(max_length=10, choices=BodyType.choices)
    base_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["make__name", "name"]
        constraints = [models.UniqueConstraint(fields=["make", "name"], name="uniq_make_model")]

    def __str__(self):
        return f"{self.make.name} {self.name}"


class Vehicle(models.Model):
    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        USED = "USED", "Pre-owned"

    class Fuel(models.TextChoices):
        PETROL = "PETROL", "Petrol"
        DIESEL = "DIESEL", "Diesel"
        CNG = "CNG", "CNG"
        EV = "EV", "Electric"
        HYBRID = "HYBRID", "Hybrid"

    class Transmission(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATIC = "AUTOMATIC", "Automatic"

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        RESERVED = "RESERVED", "Reserved"
        SOLD = "SOLD", "Sold"

    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT, related_name="vehicles")
    variant = models.CharField(max_length=60)
    year = models.PositiveSmallIntegerField()
    condition = models.CharField(max_length=4, choices=Condition.choices, default=Condition.NEW)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mileage_km = models.PositiveIntegerField(default=0)
    fuel = models.CharField(max_length=6, choices=Fuel.choices)
    transmission = models.CharField(max_length=9, choices=Transmission.choices)
    color = models.CharField(max_length=30)
    color_hex = models.CharField(max_length=7, default="#9ca3af")
    vin = models.CharField(max_length=17, unique=True)
    specs = models.JSONField(default=dict, blank=True)
    features = ArrayField(models.CharField(max_length=40), default=list, blank=True)
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["price"]),
            GinIndex(fields=["features"]),
        ]

    def __str__(self):
        return f"{self.year} {self.vehicle_model} {self.variant}"

    @property
    def title(self):
        return f"{self.vehicle_model.make.name} {self.vehicle_model.name}"

    @property
    def is_available(self):
        return self.status != self.Status.SOLD


SPEC_LABELS = {
    "engine_cc": ("Engine", "cc", "bi-gear-wide-connected"),
    "battery_kwh": ("Battery", "kWh", "bi-battery-charging"),
    "power_bhp": ("Power", "bhp", "bi-lightning-charge"),
    "torque_nm": ("Torque", "Nm", "bi-arrow-repeat"),
    "mileage_kmpl": ("Mileage", "km/l", "bi-fuel-pump"),
    "range_km": ("Range", "km", "bi-ev-station"),
    "seats": ("Seats", "", "bi-people"),
    "boot_l": ("Boot space", "L", "bi-box-seam"),
    "airbags": ("Airbags", "", "bi-shield-check"),
    "ground_clearance_mm": ("Ground clearance", "mm", "bi-arrows-vertical"),
}


class TestDrive(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="test_drives")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="test_drives")
    scheduled_at = models.DateTimeField()
    status = models.CharField(max_length=9, choices=Status.choices, default=Status.REQUESTED)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="handled_test_drives"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["scheduled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle", "scheduled_at"], condition=~Q(status="CANCELLED"), name="uniq_testdrive_slot"
            )
        ]

    def __str__(self):
        return f"{self.vehicle} @ {self.scheduled_at:%d %b %H:%M}"


class TradeInRequest(models.Model):
    class ConditionRating(models.TextChoices):
        EXCELLENT = "EXCELLENT", "Excellent"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        POOR = "POOR", "Poor"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        OFFERED = "OFFERED", "Offer made"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trade_ins")
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    km_driven = models.PositiveIntegerField()
    condition_rating = models.CharField(max_length=9, choices=ConditionRating.choices)
    estimated_value = models.DecimalField(max_digits=12, decimal_places=2)
    offered_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.year} {self.vehicle_model} ({self.customer})"


class Sale(models.Model):
    vehicle = models.OneToOneField(Vehicle, on_delete=models.PROTECT, related_name="sale")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchases")
    salesperson = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales_made")
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    trade_in = models.OneToOneField(TradeInRequest, on_delete=models.SET_NULL, null=True, blank=True)
    sold_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-sold_at"]

    def __str__(self):
        return f"Sale #{self.pk} — {self.vehicle}"

    @property
    def trade_in_credit(self):
        return self.trade_in.offered_value if self.trade_in and self.trade_in.offered_value else 0

    @property
    def amount_payable(self):
        return self.sale_price - self.trade_in_credit
