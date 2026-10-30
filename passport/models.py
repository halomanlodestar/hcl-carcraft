"""A simulated government vehicle registry (VAHAN + e-challan + insurance claims), keyed by registration number.

The shapes mirror what licensed RC-verification APIs return, so the mock can later be swapped for live data.
Owner names are deliberately never stored: the passport shows owner count, dates and places only.
"""
from django.db import models
from django.utils import timezone


class RegistryRecord(models.Model):
    reg_number = models.CharField(max_length=15, unique=True)
    vehicle_model = models.ForeignKey("inventory.VehicleModel", on_delete=models.PROTECT)
    manufacture_year = models.PositiveSmallIntegerField()
    registration_date = models.DateField()
    rto = models.CharField(max_length=60)
    fuel = models.CharField(max_length=10)
    color = models.CharField(max_length=30)
    hypothecated_to = models.CharField(max_length=60, blank=True, help_text="Lender with an open loan; blank if none")
    insurance_valid_till = models.DateField()
    puc_valid_till = models.DateField()
    fetched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["reg_number"]

    def __str__(self):
        return self.reg_number

    @property
    def owner_count(self):
        return self.ownerships.count()

    @property
    def insurance_active(self):
        return self.insurance_valid_till >= timezone.localdate()

    @property
    def puc_active(self):
        return self.puc_valid_till >= timezone.localdate()


class OwnershipPeriod(models.Model):
    class Event(models.TextChoices):
        NEW = "NEW", "First registration"
        SALE = "SALE", "Ownership transfer"
        INTERSTATE = "INTERSTATE", "Interstate transfer (NOC)"

    record = models.ForeignKey(RegistryRecord, on_delete=models.CASCADE, related_name="ownerships")
    serial = models.PositiveSmallIntegerField()
    event = models.CharField(max_length=10, choices=Event.choices)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=40)
    state = models.CharField(max_length=2)
    financed_by = models.CharField(max_length=60, blank=True)
    loan_closed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["serial"]

    @property
    def years(self):
        end = self.to_date or timezone.localdate()
        return round((end - self.from_date).days / 365.25, 1)


class Challan(models.Model):
    class Offence(models.TextChoices):
        OVERSPEEDING = "OVERSPEEDING", "Overspeeding"
        RED_LIGHT = "RED_LIGHT", "Jumping a red light"
        DANGEROUS = "DANGEROUS", "Dangerous driving"
        NO_SEATBELT = "NO_SEATBELT", "Driving without seatbelt"
        PARKING = "PARKING", "Wrong parking"
        NO_PUC = "NO_PUC", "No valid PUC"
        NO_INSURANCE = "NO_INSURANCE", "No valid insurance"

    class Status(models.TextChoices):
        PAID = "PAID", "Paid"
        PENDING = "PENDING", "Pending"
        COURT = "COURT", "Sent to court"

    # Offences that say something about how hard the car itself was driven
    WEAR_OFFENCES = {"OVERSPEEDING", "RED_LIGHT", "DANGEROUS"}
    ICONS = {
        "OVERSPEEDING": "bi-speedometer", "RED_LIGHT": "bi-stoplights", "DANGEROUS": "bi-exclamation-octagon",
        "NO_SEATBELT": "bi-person-exclamation", "PARKING": "bi-p-circle", "NO_PUC": "bi-cloud-haze2",
        "NO_INSURANCE": "bi-shield-x",
    }

    record = models.ForeignKey(RegistryRecord, on_delete=models.CASCADE, related_name="challans")
    owner_serial = models.PositiveSmallIntegerField()
    challan_no = models.CharField(max_length=24, unique=True)
    offence = models.CharField(max_length=12, choices=Offence.choices)
    issued_on = models.DateField()
    city = models.CharField(max_length=40)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=7, choices=Status.choices)

    class Meta:
        ordering = ["-issued_on"]

    @property
    def affects_wear(self):
        return self.offence in self.WEAR_OFFENCES

    @property
    def icon(self):
        return self.ICONS[self.offence]

    @property
    def is_unpaid(self):
        return self.status != self.Status.PAID


class InsuranceClaim(models.Model):
    class Kind(models.TextChoices):
        MINOR = "MINOR", "Minor accident damage"
        MAJOR = "MAJOR", "Major accident damage"
        FLOOD = "FLOOD", "Flood / water damage"
        GLASS = "GLASS", "Windscreen / glass"

    ICONS = {"MINOR": "bi-bandaid", "MAJOR": "bi-car-front", "FLOOD": "bi-water", "GLASS": "bi-window"}

    record = models.ForeignKey(RegistryRecord, on_delete=models.CASCADE, related_name="claims")
    owner_serial = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=5, choices=Kind.choices)
    claimed_on = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    insurer = models.CharField(max_length=40)

    class Meta:
        ordering = ["-claimed_on"]

    @property
    def icon(self):
        return self.ICONS[self.kind]


class OdometerReading(models.Model):
    class Source(models.TextChoices):
        PDI = "PDI", "Pre-delivery inspection"
        SERVICE = "SERVICE", "Workshop service"
        INSURANCE = "INSURANCE", "Insurance renewal"
        PUC = "PUC", "PUC test"
        CARCRAFT = "CARCRAFT", "CarCraft service"

    record = models.ForeignKey(RegistryRecord, on_delete=models.CASCADE, related_name="odometer")
    read_on = models.DateField()
    km = models.PositiveIntegerField()
    source = models.CharField(max_length=9, choices=Source.choices)

    class Meta:
        ordering = ["read_on"]
