from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from core.mixins import role_required
from core.pdf import render_pdf
from store.models import Part
from store.services import InsufficientStock

from . import services
from .forms import PAINT_CHOICES, CustomerVehicleForm
from .models import CustomerVehicle, ServiceJob, ServicePart, ServiceType


@role_required("CUSTOMER")
def garage(request):
    cars = (request.user.garage.select_related("vehicle_model__make")
            .prefetch_related(Prefetch("jobs", queryset=ServiceJob.objects.select_related("service_type").order_by("-scheduled_date"))))
    return render(request, "service/garage.html", {"cars": cars})


@role_required("CUSTOMER")
def garage_add(request):
    form = CustomerVehicleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cv = form.save(commit=False)
        cv.owner = request.user
        cv.save()
        messages.success(request, f"{cv.vehicle_model} added to your garage.")
        return redirect("service:garage")
    return render(request, "service/garage_add.html", {"form": form, "paints": PAINT_CHOICES})


def _service_days():
    today = timezone.localdate()
    days, d = [], today + timedelta(days=1)
    while len(days) < 10:
        if d.weekday() != 6:  # closed on Sundays
            days.append(d)
        d += timedelta(days=1)
    return days


@login_required
def book(request):
    if not request.user.is_customer:
        raise PermissionDenied
    cars = list(request.user.garage.select_related("vehicle_model__make"))
    if not cars:
        messages.info(request, "Add your car to your garage first, then book a service.")
        return redirect("service:garage_add")
    types = ServiceType.objects.all()
    days = _service_days()
    selected_car = request.GET.get("car") or request.POST.get("car") or str(cars[0].pk)

    if request.method == "POST":
        try:
            car = request.user.garage.get(pk=request.POST.get("car"))
            stype = types.get(pk=request.POST.get("service_type"))
            date = datetime.strptime(request.POST.get("date", ""), "%Y-%m-%d").date()
            if date not in days:
                raise ValueError
        except (CustomerVehicle.DoesNotExist, ServiceType.DoesNotExist, ValueError, TypeError):
            messages.error(request, "Please choose a car, a service and a date.")
        else:
            if car.active_job:
                messages.warning(request, f"Your {car.vehicle_model.name} already has an open service job.")
                return redirect("service:job_detail", pk=car.active_job.pk)
            job = services.book_service(car, stype, date, request.POST.get("complaint", "")[:1000], request.user)
            messages.success(request, f"Service booked for {date:%a %d %b}. Track it live right here.")
            return redirect("service:job_detail", pk=job.pk)
    return render(request, "service/book.html", {"cars": cars, "types": types, "days": days, "selected_car": selected_car})


def _can_view(user, job):
    return user.is_admin_role or job.customer_vehicle.owner_id == user.pk or (user.is_mechanic and job.mechanic_id == user.pk)


@login_required
def job_detail(request, pk):
    job = get_object_or_404(
        ServiceJob.objects.select_related("customer_vehicle__vehicle_model__make", "customer_vehicle__owner", "service_type", "mechanic")
        .prefetch_related("logs__changed_by", "parts_used__part"), pk=pk)
    if not _can_view(request.user, job):
        raise PermissionDenied
    can_work = request.user.is_admin_role or (request.user.is_mechanic and job.mechanic_id == request.user.pk)
    steps = []
    for i, code in enumerate(ServiceJob.FLOW):
        state = "done" if i < job.step_index or job.status == "DELIVERED" else ("current" if i == job.step_index else "")
        steps.append((code, ServiceJob.Status(code).label, ServiceJob.STEP_ICONS[code], state))
    progress = 0 if job.step_index < 0 else job.step_index * 20
    ctx = {
        "job": job, "steps": steps, "progress": progress, "can_work": can_work,
        "next_action": services.NEXT_ACTION_LABEL.get(job.status), "next_status": services.NEXT_STEP.get(job.status),
        "can_cancel": job.status in ("BOOKED", "INSPECTION") and (can_work or job.customer == request.user),
    }
    if can_work and job.status == "IN_PROGRESS":
        ctx["parts"] = Part.objects.filter(
            Q(compatible_models=job.customer_vehicle.vehicle_model) | Q(is_universal=True), stock_qty__gt=0
        ).select_related("category").distinct().order_by("category__name", "name")
    if request.user.is_admin_role:
        ctx["mechanics"] = User.objects.filter(role=User.Role.MECHANIC).annotate(
            open_jobs=Count("assigned_jobs", filter=Q(assigned_jobs__status__in=ServiceJob.ACTIVE_STATUSES)))
    return render(request, "service/job_detail.html", ctx)


@login_required
@require_POST
def job_advance(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    target = request.POST.get("status")
    is_owner_cancel = target == "CANCELLED" and job.customer == request.user
    if not (request.user.is_admin_role or (request.user.is_mechanic and job.mechanic_id == request.user.pk) or is_owner_cancel):
        raise PermissionDenied
    try:
        odo = request.POST.get("odometer_km")
        services.advance(job, target, request.user, request.POST.get("note", "")[:200],
                         odometer_km=int(odo) if odo and odo.isdigit() else None)
        messages.success(request, f"{job.number} moved to {job.get_status_display()}.")
    except services.TransitionError as e:
        messages.error(request, str(e))
    return redirect("service:job_detail", pk=pk)


@role_required("ADMIN")
@require_POST
def job_assign(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    mechanic = get_object_or_404(User, pk=request.POST.get("mechanic"), role=User.Role.MECHANIC)
    services.assign_mechanic(job, mechanic, request.user)
    messages.success(request, f"{job.number} assigned to {mechanic.display_name}.")
    return redirect(request.POST.get("next") or "service:manage")


@role_required("MECHANIC", "ADMIN")
@require_POST
def job_add_part(request, pk):
    job = get_object_or_404(ServiceJob, pk=pk)
    if not (request.user.is_admin_role or job.mechanic_id == request.user.pk):
        raise PermissionDenied
    part = get_object_or_404(Part, pk=request.POST.get("part"))
    try:
        qty = max(1, int(request.POST.get("qty", 1)))
        services.add_part(job, part, qty)
        messages.success(request, f"Added {qty} × {part.name}. Stock updated.")
    except InsufficientStock as e:
        messages.error(request, str(e))
    except (services.TransitionError, ValueError) as e:
        messages.error(request, str(e))
    return redirect("service:job_detail", pk=pk)


@role_required("MECHANIC", "ADMIN")
@require_POST
def job_remove_part(request, pk, part_pk):
    sp = get_object_or_404(ServicePart, pk=part_pk, job_id=pk)
    if not (request.user.is_admin_role or sp.job.mechanic_id == request.user.pk):
        raise PermissionDenied
    try:
        services.remove_part(sp)
        messages.info(request, "Part removed and returned to stock.")
    except services.TransitionError as e:
        messages.error(request, str(e))
    return redirect("service:job_detail", pk=pk)


@login_required
def job_invoice(request, pk):
    job = get_object_or_404(ServiceJob.objects.select_related("customer_vehicle__vehicle_model__make", "customer_vehicle__owner", "service_type", "mechanic")
                            .prefetch_related("parts_used__part"), pk=pk)
    if not _can_view(request.user, job):
        raise PermissionDenied
    return render_pdf("invoices/service.html", {"job": job}, f"carcraft-{job.number}.pdf")


@role_required("MECHANIC")
def queue(request):
    jobs = (ServiceJob.objects.filter(mechanic=request.user, status__in=ServiceJob.ACTIVE_STATUSES)
            .select_related("customer_vehicle__vehicle_model__make", "customer_vehicle__owner", "service_type")
            .order_by("scheduled_date"))
    columns = [(code, ServiceJob.Status(code).label, ServiceJob.STEP_ICONS[code], [j for j in jobs if j.status == code])
               for code in ServiceJob.ACTIVE_STATUSES]
    done_recent = (ServiceJob.objects.filter(mechanic=request.user, status="DELIVERED")
                   .select_related("customer_vehicle__vehicle_model__make", "service_type").order_by("-completed_at")[:8])
    return render(request, "service/queue.html", {"columns": columns, "done_recent": done_recent, "total": len(jobs),
                                                  "today": timezone.localdate()})


@role_required("ADMIN")
def manage(request):
    tab = request.GET.get("tab", "active")
    base = ServiceJob.objects.select_related("customer_vehicle__vehicle_model__make", "customer_vehicle__owner", "service_type", "mechanic")
    tabs = [
        ("active", "Active", base.filter(status__in=ServiceJob.ACTIVE_STATUSES).count()),
        ("unassigned", "Unassigned", base.filter(status__in=ServiceJob.ACTIVE_STATUSES, mechanic__isnull=True).count()),
        ("DELIVERED", "Delivered", base.filter(status="DELIVERED").count()),
        ("CANCELLED", "Cancelled", base.filter(status="CANCELLED").count()),
    ]
    if tab == "active":
        jobs = base.filter(status__in=ServiceJob.ACTIVE_STATUSES).order_by("scheduled_date")
    elif tab == "unassigned":
        jobs = base.filter(status__in=ServiceJob.ACTIVE_STATUSES, mechanic__isnull=True).order_by("scheduled_date")
    else:
        jobs = base.filter(status=tab).order_by("-scheduled_date")
    page = Paginator(jobs, 25).get_page(request.GET.get("page"))
    mechanics = User.objects.filter(role=User.Role.MECHANIC)
    return render(request, "service/manage.html", {"page": page, "tabs": tabs, "tab": tab, "mechanics": mechanics})
