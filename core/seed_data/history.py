"""Generates believable registry histories (owners, challans, claims, odometer readings) for the mock VAHAN registry."""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

# Fixed registrations with a deliberate story, used as one-tap samples on the Car Passport search page
STORY_REGS = {
    "clean": "MH14GH2087",
    "challans": "MH12RS6640",
    "rollback": "MH04KL9132",
    "flood": "MH01FD3305",
}

STATES = {
    "MH": ("Maharashtra", ["Pune", "Mumbai", "Thane", "Nashik", "Nagpur"]),
    "DL": ("Delhi", ["New Delhi"]),
    "KA": ("Karnataka", ["Bengaluru", "Mysuru"]),
    "TN": ("Tamil Nadu", ["Chennai", "Coimbatore"]),
    "GJ": ("Gujarat", ["Ahmedabad", "Surat"]),
    "UP": ("Uttar Pradesh", ["Lucknow", "Noida"]),
    "HR": ("Haryana", ["Gurugram", "Faridabad"]),
    "TS": ("Telangana", ["Hyderabad"]),
}
# Real RTO codes for the cities we use; anything else falls back to a city in the state
RTO_CITIES = {
    "MH01": "Mumbai (Central)", "MH02": "Mumbai (West)", "MH03": "Mumbai (East)", "MH04": "Thane", "MH05": "Kalyan",
    "MH12": "Pune", "MH14": "Pimpri-Chinchwad", "MH15": "Nashik", "MH31": "Nagpur",
    "DL01": "New Delhi", "KA01": "Bengaluru (Central)", "KA05": "Bengaluru (South)", "TN01": "Chennai (Central)",
    "GJ01": "Ahmedabad", "GJ05": "Surat", "UP32": "Lucknow", "UP16": "Noida", "HR26": "Gurugram", "TS09": "Hyderabad",
}

LENDERS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Prime", "Bajaj Finance", "Mahindra Finance"]
INSURERS = ["ICICI Lombard", "HDFC ERGO", "Bajaj Allianz", "Tata AIG", "New India Assurance", "Acko"]

OFFENCE_WEIGHTS = [("OVERSPEEDING", 30), ("PARKING", 25), ("RED_LIGHT", 12), ("NO_SEATBELT", 12),
                   ("NO_PUC", 8), ("DANGEROUS", 4), ("NO_INSURANCE", 3)]
OFFENCE_FINE = {"OVERSPEEDING": 2000, "PARKING": 500, "RED_LIGHT": 1000, "NO_SEATBELT": 1000,
                "NO_PUC": 10000, "DANGEROUS": 5000, "NO_INSURANCE": 2000}
CLAIM_AMOUNTS = {"MINOR": (8000, 45000), "GLASS": (6000, 18000), "MAJOR": (90000, 260000), "FLOOD": (120000, 240000)}

_challan_seq = [0]


def _rand_date(rng, start, end):
    days = max(0, (end - start).days)
    return start + timedelta(days=rng.randint(0, days)) if days else start


def _challan_no(state_code):
    _challan_seq[0] += 1
    return f"{state_code}{20000000000 + _challan_seq[0] * 7919}"


def create_record(rng, reg, vehicle_model, year, km_now, fuel, color, *, owners=None, reg_date=None,
                  current_owner_from=None, history_end=None, story=None, carcraft_readings=(), open_loan=None):
    """
    Build a RegistryRecord with a coherent history.

    current_owner_from: date the latest owner took over (e.g. when a customer bought it from us).
    history_end: last date with activity (for cars sitting in dealer stock, the day we bought it).
    carcraft_readings: (date, km) pairs from our own delivered service jobs, inserted verbatim.
    open_loan: lender name to force an active hypothecation on the current owner.
    """
    from passport.models import Challan, InsuranceClaim, OdometerReading, OwnershipPeriod, RegistryRecord

    today = timezone.localdate()
    end = history_end or today
    state_code = reg[:2] if reg[:2] in STATES else "MH"
    state_name, cities = STATES[state_code]
    rto_city = RTO_CITIES.get(reg[:4]) or rng.choice(cities)
    home_city = rto_city.split(" (")[0]

    if reg_date is None:
        reg_date = date(year, rng.randint(1, 12), rng.randint(1, 28))
        if reg_date > end - timedelta(days=60):
            reg_date = end - timedelta(days=rng.randint(60, 200))
    age_years = max(0.2, (end - reg_date).days / 365.25)

    if owners is None:
        owners = 1 if age_years < 2.5 else rng.choice([1, 1, 2]) if age_years < 5 else rng.choice([1, 2, 2, 3])
    if story == "clean":
        owners = 1
    elif story == "challans":
        owners = 2

    # Ownership periods: split [reg_date, current_owner_from] between earlier owners
    cut_points = []
    if owners > 1:
        last_start = current_owner_from or _rand_date(rng, reg_date + timedelta(days=200 * (owners - 1)), end - timedelta(days=90))
        span = (last_start - reg_date).days
        inner = sorted(rng.sample(range(150, max(151 + owners, span - 120)), owners - 2)) if owners > 2 else []
        cut_points = [reg_date + timedelta(days=d) for d in inner] + [last_start]
    starts = [reg_date] + cut_points
    interstate = owners > 1 and (story == "challans" or rng.random() < 0.12)
    other_state = rng.choice([s for s in STATES if s != state_code])

    record = RegistryRecord.objects.create(
        reg_number=reg, vehicle_model=vehicle_model, manufacture_year=year, registration_date=reg_date,
        rto=f"{rto_city} RTO ({reg[:4]})", fuel=fuel, color=color, hypothecated_to="",
        insurance_valid_till=today + timedelta(days=rng.randint(20, 330)) if rng.random() > 0.08 else today - timedelta(days=rng.randint(10, 90)),
        puc_valid_till=today + timedelta(days=rng.randint(15, 170)) if rng.random() > 0.15 else today - timedelta(days=rng.randint(5, 60)),
    )

    periods = []
    for i, start in enumerate(starts):
        is_last = i == len(starts) - 1
        stop = None if is_last else starts[i + 1]
        in_other_state = interstate and i == 0
        p_state = other_state if in_other_state else state_code
        p_city = rng.choice(STATES[p_state][1]) if in_other_state or (not is_last and rng.random() < 0.3) else home_city
        event = "NEW" if i == 0 else ("INTERSTATE" if interstate and i == 1 else "SALE")
        financed = open_loan if (is_last and open_loan) else (rng.choice(LENDERS) if rng.random() < 0.55 else "")
        closed = None
        if financed and not is_last:
            closed = stop - timedelta(days=rng.randint(10, 40))
        elif financed and is_last and not open_loan:
            loan_end = start + timedelta(days=rng.choice([3, 4, 5]) * 365)
            closed = loan_end if loan_end < today else None
        if is_last and financed and not closed:
            record.hypothecated_to = financed
        periods.append(OwnershipPeriod.objects.create(
            record=record, serial=i + 1, event=event, from_date=start, to_date=stop if not is_last else (history_end if history_end and history_end < today else None),
            city=p_city, state=p_state, financed_by=financed, loan_closed_on=closed))
    record.save(update_fields=["hypothecated_to"])

    # Challans: rate per year depends on each owner's driving style
    for p in periods:
        p_end = p.to_date or end
        years = max(0.1, (p_end - p.from_date).days / 365.25)
        style = rng.choice([0.15, 0.4, 0.9, 1.6])
        if story == "clean":
            style = 0.12
        if story == "challans" and p.serial == len(periods):
            style = 1.6
        count = int(years * style + rng.random())
        for _ in range(count):
            offence = rng.choices([o for o, _ in OFFENCE_WEIGHTS], weights=[w for _, w in OFFENCE_WEIGHTS])[0]
            if story == "clean" and offence in ("OVERSPEEDING", "RED_LIGHT", "DANGEROUS"):
                offence = "PARKING"
            if story == "challans" and rng.random() < 0.6:
                offence = rng.choice(["OVERSPEEDING", "OVERSPEEDING", "RED_LIGHT", "DANGEROUS"])
            issued = _rand_date(rng, p.from_date, p_end)
            recent = (today - issued).days < 365
            status = "PENDING" if recent and rng.random() < 0.35 else ("COURT" if not recent and rng.random() < 0.03 else "PAID")
            if story == "clean":
                status = "PAID"
            Challan.objects.create(record=record, owner_serial=p.serial, challan_no=_challan_no(p.state), offence=offence,
                                   issued_on=issued, city=p.city, amount=OFFENCE_FINE[offence], status=status)

        # Insurance claims
        if story != "clean":
            for kind, per_year in (("MINOR", 0.08), ("GLASS", 0.03), ("MAJOR", 0.012)):
                if rng.random() < per_year * years:
                    lo, hi = CLAIM_AMOUNTS[kind]
                    InsuranceClaim.objects.create(record=record, owner_serial=p.serial, kind=kind,
                                                  claimed_on=_rand_date(rng, p.from_date, p_end),
                                                  amount=round(rng.randint(lo, hi), -2), insurer=rng.choice(INSURERS))
    if story == "flood":
        flood_day = date(today.year - 1 if today.month > 7 else today.year - 2, 7, rng.randint(8, 24))
        InsuranceClaim.objects.create(record=record, owner_serial=len(periods), kind="FLOOD", claimed_on=flood_day,
                                      amount=round(rng.randint(*CLAIM_AMOUNTS["FLOOD"]), -2), insurer=rng.choice(INSURERS))

    # Odometer: PDI, yearly insurance renewals, PUC tests and workshop visits along a steady usage curve
    total_days = max(1, (end - reg_date).days)
    true_end = int(km_now / 0.6) if story == "rollback" else km_now
    points = [(reg_date, rng.randint(8, 40), "PDI")]
    d = reg_date
    while True:
        d = d + timedelta(days=365)
        if d >= end:
            break
        points.append((d - timedelta(days=rng.randint(0, 12)), None, "INSURANCE"))
        points.append((d + timedelta(days=rng.randint(80, 140)), None, "PUC"))
        if rng.random() < 0.7:
            points.append((d + timedelta(days=rng.randint(150, 300)), None, "SERVICE"))
    readings = []
    for when, km, source in points:
        if when >= end:
            continue
        if km is None:
            frac = (when - reg_date).days / total_days
            km = int(true_end * frac * rng.uniform(0.94, 1.04))
        readings.append([when, max(km, 10), source])
    readings.sort(key=lambda r: r[0])
    for i in range(1, len(readings)):  # odometers only go up
        readings[i][1] = max(readings[i][1], readings[i - 1][1] + rng.randint(300, 900))

    if story == "rollback" and len(readings) >= 4:
        cut = int(len(readings) * 0.6)
        for r in readings[cut:]:
            r[1] = int(r[1] * 0.6)

    cc_dates = {when for when, _ in carcraft_readings}
    readings = [r for r in readings if not any(abs((r[0] - c).days) < 45 for c in cc_dates)]
    for when, km in carcraft_readings:
        readings.append([when, km, "CARCRAFT"])
    readings.sort(key=lambda r: r[0])
    if story != "rollback":  # keep the merged series strictly increasing
        for i in range(1, len(readings)):
            readings[i][1] = max(readings[i][1], readings[i - 1][1] + rng.randint(300, 900))
    OdometerReading.objects.bulk_create([OdometerReading(record=record, read_on=w, km=k, source=s) for w, k, s in readings])
    return record
