from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.models import Notification, notify
from store.services import adjust_stock

from .models import ServiceJob, ServicePart, ServiceStatusLog

ALLOWED = {
    "BOOKED": {"INSPECTION", "CANCELLED"},
    "INSPECTION": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"READY"},
    "READY": {"DELIVERED"},
}

NEXT_STEP = {"BOOKED": "INSPECTION", "INSPECTION": "IN_PROGRESS", "IN_PROGRESS": "READY", "READY": "DELIVERED"}

NEXT_ACTION_LABEL = {
    "BOOKED": ("Start inspection", "bi-search"),
    "INSPECTION": ("Begin work", "bi-wrench-adjustable"),
    "IN_PROGRESS": ("Mark ready", "bi-check2-circle"),
    "READY": ("Hand over keys", "bi-key"),
}

CUSTOMER_MESSAGES = {
    "INSPECTION": ("Our technician has started inspecting your {car}", Notification.Kind.INFO),
    "IN_PROGRESS": ("Work has begun on your {car}", Notification.Kind.INFO),
    "READY": ("Your {car} is ready for pickup!", Notification.Kind.SUCCESS),
    "DELIVERED": ("Thanks for choosing CarCraft. Your {car} has been delivered.", Notification.Kind.SUCCESS),
    "CANCELLED": ("Your service booking for the {car} was cancelled", Notification.Kind.WARNING),
}


class TransitionError(Exception):
    pass


@transaction.atomic
def book_service(customer_vehicle, service_type, scheduled_date, complaint, by_user):
    job = ServiceJob.objects.create(
        customer_vehicle=customer_vehicle, service_type=service_type, scheduled_date=scheduled_date,
        complaint=complaint, labour_charge=service_type.labour_charge,
    )
    ServiceStatusLog.objects.create(job=job, status=job.status, changed_by=by_user, note="Booking received")
    return job


@transaction.atomic
def advance(job, new_status, by_user, note="", odometer_km=None):
    if new_status not in ALLOWED.get(job.status, set()):
        raise TransitionError(f"Can't move a job from {job.get_status_display()} to {new_status.title()}.")
    if new_status == "INSPECTION" and not job.mechanic:
        raise TransitionError("Assign a mechanic before starting the inspection.")
    if new_status == "IN_PROGRESS":
        if not odometer_km and not job.odometer_km:
            raise TransitionError("Record the odometer reading before starting work.")
        if odometer_km:
            job.odometer_km = odometer_km
            cv = job.customer_vehicle
            cv.km_driven = max(cv.km_driven, int(odometer_km))
            cv.save(update_fields=["km_driven"])

    job.status = new_status
    if new_status == "DELIVERED":
        job.completed_at = timezone.now()
    job.save()
    ServiceStatusLog.objects.create(job=job, status=new_status, changed_by=by_user, note=note)

    template, kind = CUSTOMER_MESSAGES[new_status]
    notify(job.customer, template.format(car=job.customer_vehicle.vehicle_model.name),
           reverse("service:job_detail", args=[job.pk]), kind, ServiceJob.STEP_ICONS[new_status])
    return job


@transaction.atomic
def assign_mechanic(job, mechanic, by_user):
    job.mechanic = mechanic
    job.save(update_fields=["mechanic"])
    notify(mechanic, f"New job assigned: {job.number} · {job.customer_vehicle.vehicle_model}",
           reverse("service:job_detail", args=[job.pk]), Notification.Kind.INFO, "bi-person-gear")


@transaction.atomic
def add_part(job, part, quantity):
    if job.status != ServiceJob.Status.IN_PROGRESS:
        raise TransitionError("Parts can only be added while work is in progress.")
    adjust_stock(part, -quantity)
    existing = job.parts_used.filter(part=part).first()
    if existing:
        existing.quantity += quantity
        existing.save(update_fields=["quantity"])
        return existing
    return ServicePart.objects.create(job=job, part=part, quantity=quantity, unit_price=part.price)


@transaction.atomic
def remove_part(service_part):
    if service_part.job.status != ServiceJob.Status.IN_PROGRESS:
        raise TransitionError("Parts can only be changed while work is in progress.")
    adjust_stock(service_part.part, service_part.quantity)
    service_part.delete()
