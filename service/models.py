from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class CustomerVehicle(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="garage")
    vehicle_model = models.ForeignKey("inventory.VehicleModel", on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    reg_number = models.CharField(max_length=15, unique=True)
    km_driven = models.PositiveIntegerField(default=0)
    color_hex = models.CharField(max_length=7, default="#9ca3af")
    purchased_vehicle = models.OneToOneField(
        "inventory.Vehicle", on_delete=models.SET_NULL, null=True, blank=True, related_name="owner_record"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vehicle_model} · {self.reg_number}"

    @property
    def last_service_date(self):
        job = self.jobs.filter(status=ServiceJob.Status.DELIVERED).order_by("-completed_at").first()
        return job.completed_at if job else None

    @property
    def is_service_due(self):
        last = self.last_service_date
        reference = last or self.created_at
        return timezone.now() - reference > timedelta(days=settings.SERVICE_INTERVAL_DAYS)

    @property
    def active_job(self):
        return self.jobs.filter(status__in=ServiceJob.ACTIVE_STATUSES).first()


class ServiceType(models.Model):
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=40, default="bi-tools")
    labour_charge = models.DecimalField(max_digits=10, decimal_places=2)
    est_hours = models.DecimalField(max_digits=4, decimal_places=1)

    class Meta:
        ordering = ["labour_charge"]

    def __str__(self):
        return self.name


class ServiceJob(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        INSPECTION = "INSPECTION", "Inspection"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        READY = "READY", "Ready for pickup"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    FLOW = ["BOOKED", "INSPECTION", "IN_PROGRESS", "READY", "DELIVERED"]
    ACTIVE_STATUSES = ["BOOKED", "INSPECTION", "IN_PROGRESS", "READY"]
    STEP_ICONS = {
        "BOOKED": "bi-calendar-check",
        "INSPECTION": "bi-search",
        "IN_PROGRESS": "bi-wrench-adjustable",
        "READY": "bi-check2-circle",
        "DELIVERED": "bi-key",
        "CANCELLED": "bi-x-circle",
    }

    customer_vehicle = models.ForeignKey(CustomerVehicle, on_delete=models.CASCADE, related_name="jobs")
    service_type = models.ForeignKey(ServiceType, on_delete=models.PROTECT)
    scheduled_date = models.DateField()
    complaint = models.TextField(blank=True)
    status = models.CharField(max_length=11, choices=Status.choices, default=Status.BOOKED)
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_jobs"
    )
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    labour_charge = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-scheduled_date", "-created_at"]

    def __str__(self):
        return f"Job #{self.pk} — {self.customer_vehicle}"

    @property
    def number(self):
        return f"JC-{self.pk:05d}"

    @property
    def customer(self):
        return self.customer_vehicle.owner

    @property
    def parts_total(self):
        return sum((p.line_total for p in self.parts_used.all()), 0)

    @property
    def subtotal(self):
        return self.labour_charge + self.parts_total

    @property
    def tax(self):
        return round(self.subtotal * settings.GST_RATE / 100, 2)

    @property
    def grand_total(self):
        return self.subtotal + self.tax

    @property
    def step_index(self):
        return self.FLOW.index(self.status) if self.status in self.FLOW else -1

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES


class ServiceStatusLog(models.Model):
    job = models.ForeignKey(ServiceJob, on_delete=models.CASCADE, related_name="logs")
    status = models.CharField(max_length=11, choices=ServiceJob.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    @property
    def icon(self):
        return ServiceJob.STEP_ICONS.get(self.status, "bi-dot")


class ServicePart(models.Model):
    job = models.ForeignKey(ServiceJob, on_delete=models.CASCADE, related_name="parts_used")
    part = models.ForeignKey("store.Part", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def line_total(self):
        return self.unit_price * self.quantity
