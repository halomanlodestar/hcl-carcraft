import random
import string
from datetime import timedelta
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from faker import Faker

from accounts.models import User
from core.models import Notification
from core.seed_data import catalog as C
from core.seed_data.history import STORY_REGS, create_record
from inventory import services as inv_services
from inventory.models import Make, Sale, TestDrive, TradeInRequest, Vehicle, VehicleModel
from passport.models import RegistryRecord
from passport.valuation import passport_for
from service.models import CustomerVehicle, ServiceJob, ServicePart, ServiceStatusLog, ServiceType
from store.models import Coupon, Order, OrderItem, Part, PartCategory
from store.services import compute_totals

PASSWORD = "demo1234"
CITIES = ["Pune"] * 6 + ["Mumbai"] * 3 + ["Pimpri-Chinchwad", "Nashik", "Thane"]
VIN_CHARS = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"


class Command(BaseCommand):
    help = "Populate the database with deterministic demo data (12 months of history)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Wipe all app data before seeding")

    def handle(self, *args, reset=False, **options):
        if User.objects.exists() and not reset:
            self.stdout.write(self.style.WARNING("Database already has data. Run with --reset to wipe and reseed."))
            return
        random.seed(42)
        Faker.seed(42)
        self.fake = Faker("en_IN")
        self.now = timezone.now()
        self.local_now = timezone.localtime(self.now)
        self.password = make_password(PASSWORD)

        with transaction.atomic():
            if reset:
                self.truncate()
            self.build_months()
            self.seed_users()
            self.seed_catalog()
            self.seed_parts()
            self.seed_coupons()
            self.seed_vehicles_and_sales()
            self.seed_trade_ins()
            self.seed_test_drives()
            self.seed_orders()
            self.seed_service()
            self.seed_registry()
            self.seed_notifications()
        self.report()

    # ------------------------------------------------------------------ helpers

    def truncate(self):
        tables = []
        for label in ("core", "accounts", "inventory", "store", "service", "passport"):
            tables += [m._meta.db_table for m in apps.get_app_config(label).get_models()]
        tables += ["django_session", "django_admin_log"]
        with connection.cursor() as cur:
            cur.execute("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE")
        self.stdout.write("Wiped existing data.")

    def build_months(self):
        first = self.local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        starts = []
        for _ in range(12):
            starts.append(first)
            first = (first - timedelta(days=1)).replace(day=1)
        starts.reverse()
        self.month_starts = starts
        self.month_weights = []
        for i, s in enumerate(starts):
            w = 0.7 + 0.6 * i / 11  # slow upward trend
            if s.month in (10, 11):  # festive season
                w *= 1.6
            elif s.month == 3:  # financial-year end
                w *= 1.3
            self.month_weights.append(w)

    def hist_dt(self, not_after_days=1):
        """A business-hours datetime in the last 12 months, weighted by month."""
        start = random.choices(self.month_starts, weights=self.month_weights)[0]
        nxt = (start + timedelta(days=32)).replace(day=1)
        limit = min(nxt, self.local_now - timedelta(days=not_after_days))
        span_days = max(1, (limit - start).days)
        dt = start + timedelta(days=random.randrange(span_days), hours=random.randint(10, 18), minutes=random.choice([0, 15, 30, 45]))
        return min(dt, limit - timedelta(hours=1))

    def spread_dates(self, total):
        """`total` datetimes allocated to months in proportion to their weight (largest remainder), random day within."""
        shares = [w / sum(self.month_weights) * total for w in self.month_weights]
        counts = [int(s) for s in shares]
        for i in sorted(range(12), key=lambda i: shares[i] - counts[i], reverse=True)[: total - sum(counts)]:
            counts[i] += 1
        dates = []
        for start, n in zip(self.month_starts, counts):
            nxt = (start + timedelta(days=32)).replace(day=1)
            limit = min(nxt, self.local_now - timedelta(days=2))
            for _ in range(n):
                day = random.randrange(max(1, (limit - start).days))
                dates.append(start + timedelta(days=day, hours=random.randint(10, 18), minutes=random.choice([0, 15, 30, 45])))
        return dates

    def ago(self, days=0, hours=0, minutes=0):
        return self.now - timedelta(days=days, hours=hours, minutes=minutes)

    def phone(self):
        return f"{random.choice('6789')}{random.randint(100000000, 999999999)}"

    def vin(self):
        return "MA" + "".join(random.choices(VIN_CHARS, k=15))

    def reg_number(self):
        reg = inv_services.random_reg_number()
        while reg in self.used_regs:
            reg = inv_services.random_reg_number()
        self.used_regs.add(reg)
        return reg

    def log(self, job, status, at, by=None, note=""):
        ServiceStatusLog.objects.create(job=job, status=status, changed_by=by, note=note, created_at=at)

    # ------------------------------------------------------------------ people

    def seed_users(self):
        self.staff = {}
        for username, first, last, role, phone in C.STAFF:
            u = User.objects.create(
                username=username, first_name=first, last_name=last, role=role, phone=phone,
                email=f"{username}@carcraft.in", password=self.password, city="Pune",
                is_staff=(role == "ADMIN"), is_superuser=(role == "ADMIN"),
                date_joined=self.ago(days=random.randint(500, 900)),
            )
            self.staff[username] = u
        self.sales_team = [self.staff["sales1"], self.staff["sales2"], self.staff["sales3"]]
        self.mechanics = [self.staff[f"mech{i}"] for i in range(1, 5)]

        self.customer1 = User.objects.create(
            username="customer1", first_name="Ananya", last_name="Iyer", role="CUSTOMER", phone="9890011223",
            email="ananya.iyer@example.com", password=self.password, city="Pune",
            address="Flat 1202, Tower B, Kumar Primavera, Wanowrie, Pune 411040",
            date_joined=self.ago(days=640),
        )
        self.customers = [self.customer1]
        seen = {"customer1"}
        while len(self.customers) < 40:
            first, last = self.fake.first_name(), self.fake.last_name()
            username = f"{first}.{last}".lower().replace(" ", "")
            if username in seen:
                continue
            seen.add(username)
            city = random.choice(CITIES)
            self.customers.append(User.objects.create(
                username=username, first_name=first, last_name=last, role="CUSTOMER", phone=self.phone(),
                email=f"{username}@example.com", password=self.password, city=city,
                address=f"{self.fake.building_number()}, {self.fake.street_name()}, {city} {random.randint(411001, 411062)}",
                date_joined=self.ago(days=random.randint(30, 720)),
            ))

    # ------------------------------------------------------------------ catalogue

    def seed_catalog(self):
        self.makes = {}
        for name, slug, country, logo in C.MAKES:
            self.makes[name] = Make.objects.create(name=name, slug=slug, country=country, logo=logo)
        self.models = {}
        self.model_specs = {}
        for make, name, body, base, fuels, variants, specs in C.MODELS:
            vm = VehicleModel.objects.create(make=self.makes[make], name=name, body_type=body, base_price=base)
            self.models[name] = vm
            self.model_specs[name] = (fuels, variants, specs)
        self.service_types = [
            ServiceType.objects.create(name=n, description=d, icon=i, labour_charge=c, est_hours=h)
            for n, d, i, c, h in C.SERVICE_TYPES
        ]

    def seed_parts(self):
        cats = {slug: PartCategory.objects.create(name=n, slug=slug, icon=icon) for n, slug, icon in C.PART_CATEGORIES}
        self.parts = []
        for sku, name, cat, brand, price, universal, compat, desc in C.PARTS:
            reorder = 4 if cat in ("tyres-wheels",) or price > 7000 else (10 if price < 700 else 5)
            stock = C.LOW_STOCK_SKUS.get(sku, C.NEAR_LOW_SKUS.get(sku, random.randint(reorder + 8, 60)))
            if sku == "BRK-PAD-0010":
                reorder = 5
            p = Part.objects.create(
                sku=sku, name=name, category=cats[cat], brand=brand, price=price, description=desc,
                stock_qty=stock, reorder_level=reorder, is_universal=universal, created_at=self.ago(days=400),
            )
            if compat:
                p.compatible_models.set([self.models[m] for m in dict.fromkeys(compat)])
            self.parts.append(p)
        self.universal_parts = [p for p in self.parts if p.is_universal]
        self.parts_by_model = {}
        for p in self.parts:
            for vm in p.compatible_models.all():
                self.parts_by_model.setdefault(vm.pk, []).append(p)

    def seed_coupons(self):
        Coupon.objects.create(code="WELCOME10", description="10% off your order, up to ₹500", discount_type="PERCENT",
                              value=10, max_discount=500, min_order=0, valid_from=self.ago(days=400), valid_to=self.ago(days=-365))
        Coupon.objects.create(code="FLAT500", description="₹500 off orders above ₹2,500", discount_type="FLAT",
                              value=500, min_order=2500, valid_from=self.ago(days=400), valid_to=self.ago(days=-365))
        last_year = self.local_now.year - 1
        Coupon.objects.create(code="DIWALI25", description="Diwali special: 25% off", discount_type="PERCENT",
                              value=25, max_discount=2000, min_order=1000,
                              valid_from=self.local_now.replace(year=last_year, month=10, day=15),
                              valid_to=self.local_now.replace(year=last_year, month=11, day=15))

    # ------------------------------------------------------------------ vehicles

    def make_vehicle(self, model_name, created_at, condition=None, tier=None, fuel=None, transmission=None, color=None):
        vm = self.models[model_name]
        fuels, variants, base_specs = self.model_specs[model_name]
        tier = random.choices([0, 1, 2], weights=[3, 4, 3])[0] if tier is None else tier
        fuel = fuel or random.choice(fuels)
        if transmission is None:
            transmission = "AUTOMATIC" if fuel in ("EV", "HYBRID") or random.random() < 0.45 else "MANUAL"
        condition = condition or ("USED" if random.random() < 0.35 else "NEW")
        local_created = timezone.localtime(created_at)

        price = float(vm.base_price) * [1.0, 1.16, 1.34][tier]
        price *= {"DIESEL": 1.09, "CNG": 1.06, "HYBRID": 1.18}.get(fuel, 1.0)
        price *= 1.07 if transmission == "AUTOMATIC" else 1.0
        if condition == "NEW":
            year, mileage = local_created.year, random.randint(5, 40)
        else:
            age = random.randint(1, 6)
            year = local_created.year - age
            mileage = random.randint(7000, 14000) * age
            price *= 0.85 ** age * random.uniform(0.95, 1.05)
        price = round(price, -3)

        specs = dict(base_specs)
        if fuel == "DIESEL" and "mileage_kmpl" in specs:
            specs["mileage_kmpl"] = round(specs["mileage_kmpl"] + 3.6, 1)
            specs["torque_nm"] = int(specs["torque_nm"] * 1.7)
        elif fuel == "CNG":
            specs["power_bhp"] = int(specs["power_bhp"] * 0.88)
            specs["mileage_kmpl"] = round(base_specs.get("mileage_kmpl", 20) * 1.3, 1)
        elif fuel == "HYBRID":
            specs["mileage_kmpl"] = round(specs.get("mileage_kmpl", 20) + 7.5, 1)
        if transmission == "AUTOMATIC" and "mileage_kmpl" in specs and fuel not in ("HYBRID", "EV"):
            specs["mileage_kmpl"] = round(specs["mileage_kmpl"] - 0.6, 1)

        features = list(C.FEATURES_BY_TIER[0])
        if tier >= 1:
            features += random.sample(C.FEATURES_BY_TIER[1], 5)
        if tier == 2:
            features += random.sample(C.FEATURES_BY_TIER[2], 5)
            if model_name in C.ADAS_MODELS:
                features.append("ADAS Level 2")
        features = list(dict.fromkeys(features))

        cname, chex = color or random.choices([(n, h) for n, h, _ in C.COLORS], weights=[w for *_, w in C.COLORS])[0]
        return Vehicle.objects.create(
            vehicle_model=vm, variant=variants[tier], year=year, condition=condition, price=price, mileage_km=mileage,
            fuel=fuel, transmission=transmission, color=cname, color_hex=chex, vin=self.vin(), specs=specs,
            features=features, created_at=created_at, reg_number=self.reg_number() if condition == "USED" else "",
        )

    def seed_vehicles_and_sales(self):
        self.used_regs = set()
        model_names = list(self.models)

        # customer1 bought a Creta here ~9 months ago
        creta = self.make_vehicle("Creta", self.ago(days=300), condition="NEW", tier=1, fuel="PETROL",
                                  transmission="AUTOMATIC", color=("Titan Grey", "#5d636b"))
        self.c1_sale = inv_services.record_sale(creta, self.customer1, self.staff["sales1"], creta.price - 15000,
                                                sold_at=self.ago(days=270), notify_customer=False)

        # 45 historic sales over the last 12 months
        popular = ["Creta", "Nexon", "Swift", "Seltos", "Brezza", "XUV700", "Punch", "Baleno", "City", "Sonet", "Scorpio-N", "Innova Hycross"]
        for sold_at in self.spread_dates(54):
            name = random.choice(popular) if random.random() < 0.6 else random.choice(model_names)
            v = self.make_vehicle(name, sold_at - timedelta(days=random.randint(10, 90)))
            buyer = random.choice(self.customers[1:])
            seller = random.choices(self.sales_team, weights=[5, 3, 2])[0]
            price = round(float(v.price) * random.uniform(0.96, 1.0), -3)
            inv_services.record_sale(v, buyer, seller, price, sold_at=sold_at, notify_customer=False)
        self.used_regs.update(CustomerVehicle.objects.values_list("reg_number", flat=True))

        # 35 cars in stock: every model at least once
        self.stock = []
        names = model_names + random.sample(popular, 5)
        for name in names:
            v = self.make_vehicle(name, self.ago(days=random.randint(1, 80), hours=random.randint(0, 8)))
            self.stock.append(v)
        for v in random.sample(self.stock, 3):
            v.status = Vehicle.Status.RESERVED
            v.save(update_fields=["status"])

    def seed_trade_ins(self):
        def create(customer, status, created_at, offered=False, model_name=None):
            vm = self.models[model_name or random.choice(list(self.models))]
            year = self.local_now.year - random.randint(3, 9)
            km = random.randint(9000, 14000) * (self.local_now.year - year)
            cond = random.choices(["EXCELLENT", "GOOD", "FAIR", "POOR"], weights=[2, 5, 3, 1])[0]
            est = inv_services.estimate_trade_in(vm, year, km, cond)
            return TradeInRequest.objects.create(
                customer=customer, vehicle_model=vm, year=year, km_driven=km, condition_rating=cond,
                estimated_value=est, offered_value=round(est * Decimal(random.uniform(0.92, 1.0)), -3) if offered else None,
                status=status, created_at=created_at,
            )

        self.story_trade_ins = []
        stories = [("challans", "Seltos", 2019, 68000, "GOOD"), ("rollback", "City", 2017, 41000, "EXCELLENT"),
                   ("flood", "Baleno", 2018, 52000, "GOOD")]
        for c, (story, model_name, year, km, cond) in zip(random.sample(self.customers[1:], 3), stories):
            vm = self.models[model_name]
            t = TradeInRequest.objects.create(
                customer=c, vehicle_model=vm, year=year, km_driven=km, condition_rating=cond, reg_number=STORY_REGS[story],
                estimated_value=inv_services.estimate_trade_in(vm, year, km, cond), status="PENDING",
                created_at=self.ago(days=random.randint(0, 4), hours=random.randint(1, 9)))
            self.story_trade_ins.append((story, t))
            self.used_regs.add(STORY_REGS[story])
        self.c1_trade_in = create(self.customer1, "OFFERED", self.ago(days=1, hours=3), offered=True, model_name="Baleno")
        for c in random.sample(self.customers[1:], 2):
            create(c, "OFFERED", self.ago(days=random.randint(1, 6)), offered=True)
        for sale in random.sample(list(Sale.objects.exclude(customer=self.customer1)), 2):
            t = create(sale.customer, "ACCEPTED", sale.sold_at - timedelta(days=6), offered=True)
            sale.trade_in = t
            sale.save(update_fields=["trade_in"])

    def seed_test_drives(self):
        available = [v for v in self.stock if v.status == "AVAILABLE"]
        taken = set()

        def slot(day_offset, hour):
            d = (self.local_now + timedelta(days=day_offset)).replace(hour=hour, minute=0, second=0, microsecond=0)
            return d

        # customer1: confirmed drive in a Seltos (or any SUV) in two days
        c1_car = next((v for v in available if v.vehicle_model.name == "Seltos"), available[0])
        self.c1_drive = TestDrive.objects.create(vehicle=c1_car, customer=self.customer1, scheduled_at=slot(2, 11),
                                                 status="CONFIRMED", handled_by=self.staff["sales1"], created_at=self.ago(days=1),
                                                 notes="Would like to try it on the highway")
        taken.add((c1_car.pk, 2, 11))
        statuses = ["REQUESTED"] * 6 + ["CONFIRMED"] * 3
        for status in statuses:
            while True:
                v, day, hour = random.choice(available), random.randint(1, 6), random.randint(10, 17)
                if (v.pk, day, hour) not in taken:
                    taken.add((v.pk, day, hour))
                    break
            TestDrive.objects.create(vehicle=v, customer=random.choice(self.customers[1:]), scheduled_at=slot(day, hour),
                                     status=status, handled_by=self.staff["sales1"] if status == "CONFIRMED" else None,
                                     created_at=self.ago(days=random.randint(0, 3), hours=random.randint(1, 8)))
        all_vehicles = list(Vehicle.objects.all())
        past_taken = set()
        for status in ["COMPLETED"] * 11 + ["CANCELLED"] * 4:
            while True:
                v = random.choice(all_vehicles)
                when = (self.local_now - timedelta(days=random.randint(2, 60))).replace(hour=random.randint(10, 17), minute=0, second=0, microsecond=0)
                if (v.pk, when) not in past_taken:
                    past_taken.add((v.pk, when))
                    break
            TestDrive.objects.create(vehicle=v, customer=random.choice(self.customers),
                                     scheduled_at=when, status=status, handled_by=random.choice(self.sales_team),
                                     created_at=when - timedelta(days=2))

    # ------------------------------------------------------------------ store

    def pick_order_parts(self, customer):
        garage_models = list(customer.garage.values_list("vehicle_model_id", flat=True))
        pool = list(self.universal_parts) * 2
        for mid in garage_models:
            pool += self.parts_by_model.get(mid, [])
        n = random.choices([1, 2, 3, 4], weights=[4, 4, 2, 1])[0]
        chosen = list(dict.fromkeys(random.sample(pool, min(n, len(pool)))))
        return [(p, random.choices([1, 2], weights=[4, 1])[0]) for p in chosen]

    def create_order(self, customer, created_at, status):
        lines = self.pick_order_parts(customer)
        subtotal = sum(Decimal(p.price) * q for p, q in lines)
        coupon = None
        if random.random() < 0.2:
            coupon = Coupon.objects.get(code="FLAT500") if subtotal >= 2500 and random.random() < 0.5 else Coupon.objects.get(code="WELCOME10")
        totals = compute_totals(subtotal, coupon)
        paid = created_at + timedelta(minutes=random.randint(1, 8)) if status != "PENDING" else None
        shipped = paid + timedelta(days=random.randint(1, 2), hours=random.randint(1, 6)) if status in ("SHIPPED", "DELIVERED") else None
        delivered = shipped + timedelta(days=random.randint(1, 3)) if status == "DELIVERED" else None
        order = Order.objects.create(
            customer=customer, status=status, coupon=coupon, created_at=created_at, paid_at=paid,
            shipped_at=shipped, delivered_at=delivered, shipping_address=f"{customer.address}", **totals,
        )
        OrderItem.objects.bulk_create([OrderItem(order=order, part=p, quantity=q, unit_price=p.price) for p, q in lines])
        return order

    def seed_orders(self):
        # customer1: three delivered and one on its way
        for days in (230, 140, 60):
            self.create_order(self.customer1, self.ago(days=days, hours=random.randint(1, 8)), "DELIVERED")
        self.c1_order = self.create_order(self.customer1, self.ago(days=2, hours=5), "SHIPPED")

        recent = ["PENDING", "PAID", "PAID", "PAID", "PAID", "SHIPPED", "SHIPPED", "SHIPPED", "DELIVERED"]
        for status in recent:
            self.create_order(random.choice(self.customers[1:]), self.ago(days=random.randint(0, 5), hours=random.randint(1, 10)), status)
        for _ in range(137):
            created = self.hist_dt(not_after_days=7)
            status = "CANCELLED" if random.random() < 0.035 else "DELIVERED"
            self.create_order(random.choice(self.customers[1:]), created, status)

    # ------------------------------------------------------------------ service

    def add_job_parts(self, job, n=None):
        options = self.parts_by_model.get(job.customer_vehicle.vehicle_model_id, []) + [
            p for p in self.universal_parts if p.category.slug in ("engine-oil", "car-care")]
        n = random.choices([0, 1, 2, 3], weights=[2, 4, 3, 1])[0] if n is None else n
        for p in random.sample(options, min(n, len(options))):
            ServicePart.objects.create(job=job, part=p, quantity=random.choice([1, 1, 1, 2]), unit_price=p.price)

    def delivered_job(self, cv, when, stype=None, mechanic=None, parts=None):
        stype = stype or random.choices(self.service_types, weights=[2, 4, 2, 2, 2, 5])[0]
        mechanic = mechanic or random.choice(self.mechanics)
        booked = (when - timedelta(days=random.randint(2, 6))).replace(hour=random.randint(10, 19), minute=random.choice([5, 20, 35, 50]))
        cv.km_driven += random.randint(4000, 9000)
        job = ServiceJob.objects.create(
            customer_vehicle=cv, service_type=stype, scheduled_date=timezone.localtime(when).date(),
            complaint=random.choice(C.COMPLAINTS), status="DELIVERED", mechanic=mechanic, odometer_km=cv.km_driven,
            labour_charge=stype.labour_charge, created_at=booked, completed_at=when + timedelta(hours=7),
        )
        self.log(job, "BOOKED", booked, cv.owner, "Booking received")
        self.log(job, "INSPECTION", when, mechanic)
        self.log(job, "IN_PROGRESS", when + timedelta(hours=1, minutes=10), mechanic)
        self.log(job, "READY", when + timedelta(hours=5), mechanic, "All done, car washed and ready")
        self.log(job, "DELIVERED", when + timedelta(hours=7), self.staff["admin"])
        self.add_job_parts(job, parts)
        return job

    def seed_service(self):
        # Extra (non-purchased) cars for ~60% of customers
        paints = ["#f4f4f2", "#17191e", "#b9bdc3", "#5d636b", "#c3282f", "#1f4fa3"]
        for c in self.customers[1:]:
            if random.random() < 0.6:
                name = random.choice(list(self.models))
                year = self.local_now.year - random.randint(2, 8)
                CustomerVehicle.objects.create(
                    owner=c, vehicle_model=self.models[name], year=year, reg_number=self.reg_number(),
                    km_driven=random.randint(9000, 13000) * (self.local_now.year - year), color_hex=random.choice(paints),
                    created_at=self.ago(days=random.randint(200, 620)),
                )
        self.c1_swift = CustomerVehicle.objects.create(
            owner=self.customer1, vehicle_model=self.models["Swift"], year=self.local_now.year - 6,
            reg_number="MH12KT4821", km_driven=58000, color_hex="#f4f4f2", created_at=self.ago(days=620),
        )
        self.c1_creta = self.c1_sale.vehicle.owner_record

        # customer1's history: Swift last serviced 230 days ago (so it's due), Creta had its first free service
        general, oil = self.service_types[5], self.service_types[1]
        for days, st in ((520, general), (380, oil), (230, general)):
            self.delivered_job(self.c1_swift, self.ago(days=days), st, self.staff["mech1"], parts=2)
        self.delivered_job(self.c1_creta, self.ago(days=150), general, self.staff["mech1"], parts=1)
        self.c1_swift.save()
        self.c1_creta.save()

        # Everyone else: a service every 4–7 months since they got the car
        active_candidates = []
        for cv in CustomerVehicle.objects.exclude(owner=self.customer1).select_related("owner"):
            t = cv.created_at + timedelta(days=random.randint(90, 200))
            while t < self.now - timedelta(days=20):
                self.delivered_job(cv, t.replace(hour=random.randint(9, 12)))
                t += timedelta(days=random.randint(120, 220))
            cv.save(update_fields=["km_driven"])
            active_candidates.append(cv)

        for cv in random.sample(active_candidates, 3):  # a few cancellations
            when = self.hist_dt(not_after_days=10)
            job = ServiceJob.objects.create(customer_vehicle=cv, service_type=random.choice(self.service_types),
                                            scheduled_date=timezone.localtime(when).date(), status="CANCELLED",
                                            labour_charge=899, created_at=when - timedelta(days=3))
            self.log(job, "BOOKED", job.created_at, cv.owner, "Booking received")
            self.log(job, "CANCELLED", when - timedelta(days=1), cv.owner)

        # 12 active jobs spread across every stage
        today = self.local_now.replace(hour=9, minute=40, second=0, microsecond=0)
        if today > self.local_now:
            today -= timedelta(days=1)
        m1, m2, m3, m4 = self.mechanics
        plan = [
            ("BOOKED", None), ("BOOKED", None), ("BOOKED", m2),
            ("INSPECTION", m1), ("INSPECTION", m3), ("INSPECTION", m4),
            ("IN_PROGRESS", m1), ("IN_PROGRESS", m2), ("IN_PROGRESS", m3),
            ("READY", m1), ("READY", m2), ("READY", m4),
        ]
        cars = random.sample(active_candidates, 11)
        c1_index = 6  # customer1's Creta is the IN_PROGRESS job with mech1
        cars.insert(c1_index, self.c1_creta)
        flow = ServiceJob.FLOW
        for (status, mech), cv in zip(plan, cars):
            stype = self.service_types[5] if cv == self.c1_creta else random.choices(self.service_types, weights=[2, 4, 2, 2, 2, 5])[0]
            booked_at = (today - timedelta(days=random.randint(1, 4))).replace(hour=random.randint(10, 18), minute=random.choice([5, 20, 35, 50]))
            sched = (today + timedelta(days=random.randint(0, 2))).date() if status == "BOOKED" else today.date()
            job = ServiceJob.objects.create(
                customer_vehicle=cv, service_type=stype, scheduled_date=sched, status=status, mechanic=mech,
                complaint="Squeaking noise when braking, and periodic service due" if cv == self.c1_creta else random.choice(C.COMPLAINTS),
                labour_charge=stype.labour_charge, created_at=booked_at,
                odometer_km=cv.km_driven + random.randint(3000, 7000) if status in ("IN_PROGRESS", "READY") else None,
            )
            self.log(job, "BOOKED", booked_at, cv.owner, "Booking received")
            t = today
            for step in flow[1:flow.index(status) + 1]:
                t += timedelta(minutes=random.randint(35, 90))
                self.log(job, step, min(t, self.now - timedelta(minutes=5)), mech,
                         "Brake pads are worn, will replace" if (cv == self.c1_creta and step == "IN_PROGRESS") else "")
            if status in ("IN_PROGRESS", "READY"):
                if cv == self.c1_creta:
                    for sku in ("FLT-OIL-0020", "ENG-OIL-0001"):
                        p = next(p for p in self.parts if p.sku == sku)
                        ServicePart.objects.create(job=job, part=p, quantity=1, unit_price=p.price)
                    self.c1_job = job
                else:
                    self.add_job_parts(job, random.randint(1, 3))

    # ------------------------------------------------------------------ registry (mock VAHAN)

    def seed_registry(self):
        rng = random.Random(7)

        # Used cars in our stock: history ends the day we bought them. One is the "clean" showcase.
        used_stock = [v for v in Vehicle.objects.filter(condition="USED").exclude(status="SOLD").select_related("vehicle_model")]
        for i, v in enumerate(used_stock):
            story = "clean" if i == 0 else None
            if story:
                v.reg_number = STORY_REGS["clean"]
                v.save(update_fields=["reg_number"])
            create_record(rng, v.reg_number, v.vehicle_model, v.year, v.mileage_km, v.fuel, v.color,
                          history_end=timezone.localtime(v.created_at).date(), story=story)

        # Every car in a customer's garage
        loans = {self.c1_creta.pk: ("HDFC Bank", 640000, 18900), self.c1_swift.pk: ("Bajaj Finance", 85000, 7400)}
        for cv in CustomerVehicle.objects.select_related("vehicle_model", "purchased_vehicle", "owner"):
            jobs = cv.jobs.filter(status="DELIVERED", odometer_km__isnull=False)
            cc = [(timezone.localtime(j.completed_at).date(), j.odometer_km) for j in jobs]
            bought = timezone.localtime(cv.created_at).date()
            pv = cv.purchased_vehicle
            lender = loans.get(cv.pk, (None,))[0]
            kwargs = {"carcraft_readings": cc, "open_loan": lender}
            if pv and pv.condition == "NEW":
                kwargs.update(owners=1, reg_date=bought)
            elif pv:
                kwargs.update(owners=random.choice([2, 2, 3]), current_owner_from=bought)
            elif cv == self.c1_swift:
                kwargs.update(owners=2, current_owner_from=bought)
            fuel = pv.fuel if pv else random.choice(self.model_specs[cv.vehicle_model.name][0])
            rec = create_record(rng, cv.reg_number, cv.vehicle_model, cv.year, cv.km_driven, fuel,
                                pv.color if pv else "", **kwargs)
            if cv.pk in loans:
                _, cv.loan_outstanding, cv.current_emi = loans[cv.pk]
            elif rec.hypothecated_to:
                cv.loan_outstanding = round(float(cv.vehicle_model.base_price) * random.uniform(0.15, 0.6), -3)
                cv.current_emi = round(float(cv.loan_outstanding) / random.randint(24, 48), -2)
            cv.save(update_fields=["loan_outstanding", "current_emi"])

        # The three story trade-ins: valued from their history, so the sales queue shows the real number
        for story, t in self.story_trade_ins:
            create_record(rng, t.reg_number, t.vehicle_model, t.year, t.km_driven, "PETROL", "", story=story)
            _, valuation = passport_for(t.reg_number, t.km_driven, t.condition_rating)
            t.estimated_value = valuation.final
            t.save(update_fields=["estimated_value"])

    # ------------------------------------------------------------------ notifications

    def seed_notifications(self):
        c1 = self.customer1
        job = self.c1_job
        N = Notification.objects.create
        items = [
            (job.logs.get(status="IN_PROGRESS").created_at, "Work has begun on your Creta", f"/service/jobs/{job.pk}/", "INFO", "bi-wrench-adjustable", False),
            (job.logs.get(status="INSPECTION").created_at, "Our technician has started inspecting your Creta", f"/service/jobs/{job.pk}/", "INFO", "bi-search", False),
            (self.c1_trade_in.created_at + timedelta(hours=5), f"We've made an offer of ₹{self.c1_trade_in.offered_value:,.0f} for your Baleno", "/inventory/my/trade-ins/", "SUCCESS", "bi-tag", False),
            (self.ago(days=1, hours=1), f"Your test drive of the {self.c1_drive.vehicle.title} on {timezone.localtime(self.c1_drive.scheduled_at):%d %b, %I:%M %p} is confirmed", f"/inventory/{self.c1_drive.vehicle_id}/", "SUCCESS", "bi-calendar-check", False),
            (self.c1_order.shipped_at, f"Order {self.c1_order.number} is shipped", f"/store/orders/{self.c1_order.pk}/", "INFO", "bi-truck", False),
            (self.c1_order.paid_at, f"Payment received for order {self.c1_order.number}", f"/store/orders/{self.c1_order.pk}/", "SUCCESS", "bi-credit-card", True),
        ]
        for o in c1.orders.filter(status="DELIVERED"):
            items.append((o.delivered_at, f"Order {o.number} is delivered", f"/store/orders/{o.pk}/", "INFO", "bi-box2-heart", True))
            items.append((o.paid_at, f"Payment received for order {o.number}", f"/store/orders/{o.pk}/", "SUCCESS", "bi-credit-card", True))
        for j in ServiceJob.objects.filter(customer_vehicle__owner=c1, status="DELIVERED"):
            items.append((j.completed_at - timedelta(hours=2), f"Your {j.customer_vehicle.vehicle_model.name} is ready for pickup!", f"/service/jobs/{j.pk}/", "SUCCESS", "bi-check2-circle", True))
        items.append((self.c1_sale.sold_at, "Congratulations on your new Hyundai Creta! It's been added to your garage.", "/service/garage/", "SUCCESS", "bi-trophy", True))
        for at, msg, link, kind, icon, read in items:
            N(user=c1, message=msg, link=link, kind=kind, icon=icon, is_read=read, created_at=at)

        for j in ServiceJob.objects.filter(mechanic=self.staff["mech1"], status__in=["INSPECTION", "IN_PROGRESS"]):
            N(user=self.staff["mech1"], message=f"New job assigned: {j.number} · {j.customer_vehicle.vehicle_model}",
              link=f"/service/jobs/{j.pk}/", kind="INFO", icon="bi-person-gear", created_at=j.created_at + timedelta(hours=2))

    # ------------------------------------------------------------------ summary

    def report(self):
        rows = [
            ("Users", User.objects.count()), ("Vehicles", Vehicle.objects.count()),
            ("  in stock", Vehicle.objects.exclude(status="SOLD").count()), ("Sales", Sale.objects.count()),
            ("Test drives", TestDrive.objects.count()), ("Trade-ins", TradeInRequest.objects.count()),
            ("Parts", Part.objects.count()), ("Orders", Order.objects.count()),
            ("Garage cars", CustomerVehicle.objects.count()), ("Service jobs", ServiceJob.objects.count()),
            ("  active", ServiceJob.objects.filter(status__in=ServiceJob.ACTIVE_STATUSES).count()),
            ("Notifications", Notification.objects.count()),
            ("Registry records", RegistryRecord.objects.count()),
        ]
        self.stdout.write(self.style.SUCCESS("\nSeed complete"))
        for label, n in rows:
            self.stdout.write(f"  {label:<16}{n:>6}")
        self.stdout.write("\nDemo logins (password: demo1234): admin · sales1 · mech1 · customer1")
