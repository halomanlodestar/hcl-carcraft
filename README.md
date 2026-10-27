# CarCraft: Automotive Inventory & Dealership Suite

Vehicle inventory and dealership management, an e-commerce store for parts and accessories, and service appointment scheduling, built with Django, Bootstrap 5 and PostgreSQL.

See [docs/DESIGN.md](docs/DESIGN.md) for the architecture, data model and feature map.

## Quick start

Requirements: Python 3.12, Docker (for PostgreSQL). If you already have PostgreSQL 16 running locally, skip the Docker step and put your credentials in `.env`.

```bash
# 1. Database
docker compose up -d

# 2. Python environment
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt

# 3. Config, schema and demo data
copy .env.example .env          # cp on macOS/Linux
python manage.py migrate
python manage.py seed --reset

# 4. Run
python manage.py runserver
```

Open http://127.0.0.1:8000.

## Demo accounts

All passwords are `demo1234`. The sign-in page has one-click buttons for each account.

| Username | Role | What to look at |
|---|---|---|
| `customer1` | Customer | Garage with one car in service (live tracker) and one due for service, a shipped order, a trade-in offer, a confirmed test drive, unread notifications |
| `sales1` | Sales executive | Test drives to confirm, trade-ins to value, record a sale, sales chart |
| `mech1` | Mechanic | Job board with jobs at Inspection and In progress; add parts used and advance the status |
| `admin` | Admin (and Django superuser) | Dashboard, analytics with 12 months of history, low-stock alerts, mechanic assignment, order shipping, `/admin/` |

`python manage.py seed --reset` wipes and recreates everything. The data is deterministic, so every teammate sees the same demo.

## Feature tour (about 8 minutes)

1. **Browse:** home, then *Cars*. Filter by brand logo, body type, fuel and budget. Search "creta". Add 2–3 cars to compare. Open a car and play with the EMI sliders.
2. **`customer1`:** book a test drive, then get a trade-in estimate. Open *Parts* and pick **Hyundai → Creta** to see only parts that fit. Add to cart and apply `WELCOME10` (try `DIWALI25` to see the expired-coupon message). Check out, pay on the mock gateway, then open the invoice PDF.
3. **`customer1`:** *My garage* shows the "Service due" badge on the Swift. Open the Creta's live tracker.
4. **`mech1`:** open the Creta job, add *Bosch Front Brake Pads* and click *Mark ready*.
5. **`customer1`:** the bell shows "Your Creta is ready for pickup!" and the tracker has moved on.
6. **`sales1`:** confirm a test drive, make a trade-in offer, and record a sale from any car page.
7. **`admin`:** look at the analytics (festive-season spike, top models, days to sell). The low-stock list now includes the brake pads; restock them. Ship an order and assign a mechanic.

## Project layout

```
accounts/    custom User with role, login/register/profile
inventory/   makes, models, vehicles, compare, EMI, test drives, trade-ins, sales
store/       parts, fits-my-car filter, cart, coupons, checkout, orders
service/     garage, service booking, job state machine, parts used
dashboard/   role dashboards, analytics (Chart.js), low stock
core/        base helpers, notifications, PDF rendering, seed command
templates/   all HTML (Bootstrap 5, Bootstrap Icons)
static/      app.css, small JS files, brand logos
```

Business rules live in each app's `services.py`. `store.services.adjust_stock()` is the only code that changes stock, so the store and the service centre always agree.

Brand logos come from [Simple Icons](https://simpleicons.org) (CC0). They are trademarks of their owners and are used here for identification only.
