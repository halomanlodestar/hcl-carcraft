"""Hand-curated catalogue used by `manage.py seed`. Prices are realistic ex-showroom figures in INR."""

MAKES = [
    # name, slug, country, logo file (static/brands/<logo>.svg)
    ("Maruti Suzuki", "maruti-suzuki", "India / Japan", "suzuki"),
    ("Hyundai", "hyundai", "South Korea", "hyundai"),
    ("Tata", "tata", "India", "tata"),
    ("Mahindra", "mahindra", "India", "mahindra"),
    ("Honda", "honda", "Japan", "honda"),
    ("Toyota", "toyota", "Japan", "toyota"),
    ("Kia", "kia", "South Korea", "kia"),
    ("MG", "mg", "United Kingdom / China", "mg"),
]

# Each model: make, name, body, base_price, fuels, variants (base → top), spec template
MODELS = [
    ("Maruti Suzuki", "Swift", "HATCHBACK", 649000, ["PETROL", "CNG"], ["LXi", "VXi", "ZXi+"],
     {"engine_cc": 1197, "power_bhp": 81, "torque_nm": 112, "mileage_kmpl": 24.8, "seats": 5, "boot_l": 265, "airbags": 6, "ground_clearance_mm": 163}),
    ("Maruti Suzuki", "Baleno", "HATCHBACK", 699000, ["PETROL", "CNG"], ["Sigma", "Zeta", "Alpha"],
     {"engine_cc": 1197, "power_bhp": 89, "torque_nm": 113, "mileage_kmpl": 22.4, "seats": 5, "boot_l": 318, "airbags": 6, "ground_clearance_mm": 170}),
    ("Maruti Suzuki", "Dzire", "SEDAN", 679000, ["PETROL", "CNG"], ["LXi", "VXi", "ZXi+"],
     {"engine_cc": 1197, "power_bhp": 81, "torque_nm": 112, "mileage_kmpl": 24.8, "seats": 5, "boot_l": 382, "airbags": 6, "ground_clearance_mm": 163}),
    ("Maruti Suzuki", "Brezza", "SUV", 869000, ["PETROL", "CNG"], ["LXi", "VXi", "ZXi+"],
     {"engine_cc": 1462, "power_bhp": 102, "torque_nm": 137, "mileage_kmpl": 19.8, "seats": 5, "boot_l": 328, "airbags": 6, "ground_clearance_mm": 198}),
    ("Maruti Suzuki", "Ertiga", "MUV", 929000, ["PETROL", "CNG"], ["LXi", "VXi", "ZXi+"],
     {"engine_cc": 1462, "power_bhp": 102, "torque_nm": 137, "mileage_kmpl": 20.5, "seats": 7, "boot_l": 209, "airbags": 4, "ground_clearance_mm": 185}),
    ("Hyundai", "i20", "HATCHBACK", 749000, ["PETROL"], ["Magna", "Sportz", "Asta (O)"],
     {"engine_cc": 1197, "power_bhp": 82, "torque_nm": 115, "mileage_kmpl": 20.3, "seats": 5, "boot_l": 311, "airbags": 6, "ground_clearance_mm": 170}),
    ("Hyundai", "Venue", "SUV", 799000, ["PETROL", "DIESEL"], ["S", "SX", "SX(O)"],
     {"engine_cc": 1197, "power_bhp": 82, "torque_nm": 114, "mileage_kmpl": 18.3, "seats": 5, "boot_l": 350, "airbags": 6, "ground_clearance_mm": 195}),
    ("Hyundai", "Creta", "SUV", 1111000, ["PETROL", "DIESEL"], ["E", "SX", "SX(O)"],
     {"engine_cc": 1497, "power_bhp": 113, "torque_nm": 144, "mileage_kmpl": 17.4, "seats": 5, "boot_l": 433, "airbags": 6, "ground_clearance_mm": 190}),
    ("Hyundai", "Verna", "SEDAN", 1107000, ["PETROL"], ["EX", "SX", "SX(O)"],
     {"engine_cc": 1497, "power_bhp": 113, "torque_nm": 144, "mileage_kmpl": 18.6, "seats": 5, "boot_l": 528, "airbags": 6, "ground_clearance_mm": 165}),
    ("Tata", "Punch", "SUV", 613000, ["PETROL", "CNG"], ["Pure", "Adventure", "Creative"],
     {"engine_cc": 1199, "power_bhp": 86, "torque_nm": 113, "mileage_kmpl": 20.1, "seats": 5, "boot_l": 366, "airbags": 2, "ground_clearance_mm": 187}),
    ("Tata", "Altroz", "HATCHBACK", 665000, ["PETROL", "DIESEL", "CNG"], ["XE", "XM+", "XZ+"],
     {"engine_cc": 1199, "power_bhp": 86, "torque_nm": 113, "mileage_kmpl": 19.3, "seats": 5, "boot_l": 345, "airbags": 6, "ground_clearance_mm": 165}),
    ("Tata", "Nexon", "SUV", 799000, ["PETROL", "DIESEL"], ["Smart", "Creative", "Fearless+"],
     {"engine_cc": 1199, "power_bhp": 118, "torque_nm": 170, "mileage_kmpl": 17.4, "seats": 5, "boot_l": 382, "airbags": 6, "ground_clearance_mm": 208}),
    ("Tata", "Nexon EV", "SUV", 1449000, ["EV"], ["Creative", "Fearless", "Empowered+"],
     {"battery_kwh": 40.5, "power_bhp": 143, "torque_nm": 215, "range_km": 465, "seats": 5, "boot_l": 350, "airbags": 6, "ground_clearance_mm": 190}),
    ("Tata", "Harrier", "SUV", 1549000, ["DIESEL"], ["Smart", "Adventure", "Fearless+"],
     {"engine_cc": 1956, "power_bhp": 168, "torque_nm": 350, "mileage_kmpl": 16.8, "seats": 5, "boot_l": 445, "airbags": 7, "ground_clearance_mm": 205}),
    ("Mahindra", "Thar", "SUV", 1135000, ["PETROL", "DIESEL"], ["AX (O)", "LX", "LX Hard Top"],
     {"engine_cc": 2184, "power_bhp": 130, "torque_nm": 300, "mileage_kmpl": 15.2, "seats": 4, "boot_l": 130, "airbags": 2, "ground_clearance_mm": 226}),
    ("Mahindra", "Scorpio-N", "SUV", 1385000, ["PETROL", "DIESEL"], ["Z2", "Z6", "Z8 L"],
     {"engine_cc": 2184, "power_bhp": 172, "torque_nm": 400, "mileage_kmpl": 15.4, "seats": 7, "boot_l": 460, "airbags": 6, "ground_clearance_mm": 187}),
    ("Mahindra", "XUV700", "SUV", 1399000, ["PETROL", "DIESEL"], ["MX", "AX5", "AX7 L"],
     {"engine_cc": 2184, "power_bhp": 182, "torque_nm": 450, "mileage_kmpl": 16.0, "seats": 7, "boot_l": 240, "airbags": 7, "ground_clearance_mm": 200}),
    ("Honda", "Amaze", "SEDAN", 719000, ["PETROL"], ["V", "VX", "ZX"],
     {"engine_cc": 1199, "power_bhp": 89, "torque_nm": 110, "mileage_kmpl": 18.6, "seats": 5, "boot_l": 416, "airbags": 6, "ground_clearance_mm": 172}),
    ("Honda", "City", "SEDAN", 1182000, ["PETROL", "HYBRID"], ["SV", "VX", "ZX"],
     {"engine_cc": 1498, "power_bhp": 119, "torque_nm": 145, "mileage_kmpl": 18.4, "seats": 5, "boot_l": 506, "airbags": 6, "ground_clearance_mm": 165}),
    ("Honda", "Elevate", "SUV", 1169000, ["PETROL"], ["SV", "VX", "ZX"],
     {"engine_cc": 1498, "power_bhp": 119, "torque_nm": 145, "mileage_kmpl": 16.9, "seats": 5, "boot_l": 458, "airbags": 6, "ground_clearance_mm": 220}),
    ("Toyota", "Glanza", "HATCHBACK", 699000, ["PETROL", "CNG"], ["E", "G", "V"],
     {"engine_cc": 1197, "power_bhp": 89, "torque_nm": 113, "mileage_kmpl": 22.3, "seats": 5, "boot_l": 318, "airbags": 6, "ground_clearance_mm": 170}),
    ("Toyota", "Innova Hycross", "MUV", 1977000, ["PETROL", "HYBRID"], ["GX", "VX", "ZX (O)"],
     {"engine_cc": 1987, "power_bhp": 184, "torque_nm": 206, "mileage_kmpl": 21.1, "seats": 7, "boot_l": 300, "airbags": 6, "ground_clearance_mm": 185}),
    ("Toyota", "Fortuner", "SUV", 3343000, ["PETROL", "DIESEL"], ["4x2", "4x4", "Legender"],
     {"engine_cc": 2755, "power_bhp": 201, "torque_nm": 500, "mileage_kmpl": 10.0, "seats": 7, "boot_l": 296, "airbags": 7, "ground_clearance_mm": 225}),
    ("Toyota", "Hilux", "PICKUP", 3040000, ["DIESEL"], ["Standard", "High", "High 4x4"],
     {"engine_cc": 2755, "power_bhp": 201, "torque_nm": 500, "mileage_kmpl": 10.0, "seats": 5, "boot_l": 435, "airbags": 7, "ground_clearance_mm": 230}),
    ("Kia", "Sonet", "SUV", 799000, ["PETROL", "DIESEL"], ["HTE", "HTX", "GTX+"],
     {"engine_cc": 1197, "power_bhp": 82, "torque_nm": 115, "mileage_kmpl": 18.4, "seats": 5, "boot_l": 385, "airbags": 6, "ground_clearance_mm": 211}),
    ("Kia", "Seltos", "SUV", 1099000, ["PETROL", "DIESEL"], ["HTE", "HTX", "GTX+"],
     {"engine_cc": 1497, "power_bhp": 113, "torque_nm": 144, "mileage_kmpl": 17.0, "seats": 5, "boot_l": 433, "airbags": 6, "ground_clearance_mm": 190}),
    ("Kia", "Carens", "MUV", 1052000, ["PETROL", "DIESEL"], ["Premium", "Prestige", "Luxury Plus"],
     {"engine_cc": 1497, "power_bhp": 113, "torque_nm": 144, "mileage_kmpl": 16.5, "seats": 7, "boot_l": 216, "airbags": 6, "ground_clearance_mm": 195}),
    ("MG", "Astor", "SUV", 1082000, ["PETROL"], ["Sprint", "Shine", "Savvy Pro"],
     {"engine_cc": 1498, "power_bhp": 108, "torque_nm": 144, "mileage_kmpl": 15.4, "seats": 5, "boot_l": 488, "airbags": 6, "ground_clearance_mm": 180}),
    ("MG", "Hector", "SUV", 1399000, ["PETROL", "DIESEL"], ["Style", "Smart Pro", "Savvy Pro"],
     {"engine_cc": 1451, "power_bhp": 141, "torque_nm": 250, "mileage_kmpl": 13.8, "seats": 5, "boot_l": 587, "airbags": 6, "ground_clearance_mm": 192}),
    ("MG", "ZS EV", "SUV", 1898000, ["EV"], ["Executive", "Exclusive", "Exclusive Pro"],
     {"battery_kwh": 50.3, "power_bhp": 174, "torque_nm": 280, "range_km": 461, "seats": 5, "boot_l": 448, "airbags": 6, "ground_clearance_mm": 177}),
]

FEATURES_BY_TIER = [
    ["ABS with EBD", "Rear parking sensors", "Power windows", "Bluetooth audio", "ISOFIX mounts"],
    ["Touchscreen infotainment", "Android Auto & CarPlay", "Rear camera", "Steering-mounted controls", "Alloy wheels", "Automatic climate control", "Push-button start"],
    ["Electric sunroof", "Cruise control", "Ventilated front seats", "360° camera", "Wireless charging", "Connected car tech", "LED projector headlamps", "Premium sound system"],
]
ADAS_MODELS = {"XUV700", "Creta", "Seltos", "Hector", "Elevate", "City", "Harrier", "Innova Hycross", "Verna", "ZS EV"}

COLORS = [
    ("Arctic White", "#f4f4f2", 22), ("Phantom Black", "#17191e", 14), ("Silky Silver", "#b9bdc3", 16),
    ("Titan Grey", "#5d636b", 14), ("Fiery Red", "#c3282f", 9), ("Ocean Blue", "#1f4fa3", 8),
    ("Midnight Blue", "#1e2a4a", 6), ("Forest Green", "#2f5d46", 4), ("Bronze", "#8a6a4a", 4), ("Sunset Orange", "#d9622b", 3),
]

PART_CATEGORIES = [
    ("Engine & Oil", "engine-oil", "bi-droplet-half"),
    ("Brakes", "brakes", "bi-disc"),
    ("Filters", "filters", "bi-funnel"),
    ("Electrical & Lighting", "electrical", "bi-lightning-charge"),
    ("Tyres & Wheels", "tyres-wheels", "bi-vinyl"),
    ("Body & Exterior", "body-exterior", "bi-car-front"),
    ("Interior Accessories", "interior", "bi-grid-3x3-gap"),
    ("Car Care", "car-care", "bi-stars"),
]

COMPACT = ["Swift", "Baleno", "Dzire", "Glanza", "i20", "Altroz", "Punch", "Amaze"]
MID_SUV = ["Creta", "Seltos", "Venue", "Sonet", "Brezza", "Elevate", "Astor", "Nexon"]
BIG_SUV = ["XUV700", "Scorpio-N", "Harrier", "Hector", "Fortuner", "Thar"]
MUVS = ["Ertiga", "Carens", "Innova Hycross"]
SEDANS = ["City", "Verna", "Dzire", "Amaze"]

# sku, name, category, brand, price, universal, compatible model names, description
PARTS = [
    # Engine & oil
    ("ENG-OIL-0001", "Castrol EDGE 5W-30 Fully Synthetic (3.5 L)", "engine-oil", "Castrol", 3290, True, [], "Advanced full-synthetic oil with Fluid TITANIUM for maximum engine performance."),
    ("ENG-OIL-0002", "Mobil 1 0W-40 Synthetic Engine Oil (4 L)", "engine-oil", "Mobil", 4150, True, [], "Premium synthetic oil for turbocharged petrol and diesel engines."),
    ("ENG-OIL-0003", "Shell Helix HX7 10W-40 (3 L)", "engine-oil", "Shell", 1890, True, [], "Semi-synthetic oil with active cleansing technology."),
    ("ENG-SPK-0004", "NGK Iridium Spark Plug (set of 4)", "engine-oil", "NGK", 2240, False, COMPACT + ["Brezza", "Ertiga", "City", "Verna"], "Long-life iridium tip for sharper throttle response and better mileage."),
    ("ENG-BLT-0005", "Gates Timing Belt Kit", "engine-oil", "Gates", 5480, False, ["City", "Amaze", "Elevate", "Verna", "Creta", "Seltos"], "Complete kit with belt, tensioner and idler pulley."),
    ("ENG-CLT-0006", "Valeo Clutch Plate & Pressure Plate Kit", "engine-oil", "Valeo", 7890, False, ["Swift", "Dzire", "Baleno", "Brezza", "Glanza", "Ertiga"], "OE-grade clutch kit for smooth engagement."),
    ("ENG-COL-0007", "Prestone Coolant Concentrate (1 L)", "engine-oil", "Prestone", 690, True, [], "Long-life antifreeze and coolant, mixes 50:50 with water."),
    # Brakes
    ("BRK-PAD-0010", "Bosch Front Brake Pads, Creta / Seltos", "brakes", "Bosch", 2650, False, ["Creta", "Seltos", "Carens", "Verna"], "Low-dust ceramic compound with noise-damping shims."),
    ("BRK-PAD-0011", "Brembo Front Brake Pads, Swift / Dzire", "brakes", "Brembo", 2190, False, ["Swift", "Dzire", "Baleno", "Glanza"], "Italian-engineered pads with consistent bite in all weather."),
    ("BRK-PAD-0012", "TVS Apache Front Brake Pads, Nexon / Punch", "brakes", "TVS Girling", 1980, False, ["Nexon", "Nexon EV", "Punch", "Altroz"], "Fade-resistant semi-metallic pads."),
    ("BRK-PAD-0013", "Bosch Front Brake Pads, XUV700 / Scorpio-N", "brakes", "Bosch", 3450, False, ["XUV700", "Scorpio-N", "Thar"], "Heavy-duty pads for large SUVs."),
    ("BRK-PAD-0014", "Akebono Brake Pads, City / Elevate", "brakes", "Akebono", 2890, False, ["City", "Elevate", "Amaze"], "OE supplier to Honda, quiet ceramic formula."),
    ("BRK-DSC-0015", "Brembo Front Brake Disc (pair)", "brakes", "Brembo", 6890, False, ["Creta", "Seltos", "Verna", "City", "Elevate"], "Precision-balanced vented discs, UV-coated against rust."),
    ("BRK-FLD-0016", "Bosch DOT 4 Brake Fluid (500 ml)", "brakes", "Bosch", 450, True, [], "High boiling point fluid for ABS-equipped vehicles."),
    ("BRK-SHO-0017", "Rane Rear Brake Shoes", "brakes", "Rane", 1350, False, COMPACT + ["Brezza", "Ertiga"], "Asbestos-free rear drum brake shoes."),
    # Filters
    ("FLT-OIL-0020", "Bosch Oil Filter, Hyundai / Kia 1.5", "filters", "Bosch", 420, False, ["Creta", "Seltos", "Verna", "Carens", "Venue", "Sonet", "i20"], "Fine-mesh filter media traps 99% of harmful particles."),
    ("FLT-OIL-0021", "Mann Oil Filter, Maruti / Toyota", "filters", "Mann-Filter", 380, False, ["Swift", "Dzire", "Baleno", "Brezza", "Ertiga", "Glanza"], "German-engineered filter for K-series engines."),
    ("FLT-OIL-0022", "Purolator Oil Filter, Mahindra mHawk", "filters", "Purolator", 560, False, ["XUV700", "Scorpio-N", "Thar"], "High-capacity filter for diesel engines."),
    ("FLT-AIR-0023", "K&N High-Flow Air Filter, Creta / Seltos", "filters", "K&N", 4590, False, ["Creta", "Seltos", "Carens", "Verna"], "Washable, reusable performance air filter. Lasts the life of the car."),
    ("FLT-AIR-0024", "Bosch Air Filter, Swift / Baleno", "filters", "Bosch", 490, False, ["Swift", "Baleno", "Dzire", "Glanza"], "OE-quality engine air filter."),
    ("FLT-AIR-0025", "Mann Air Filter, Honda City / Elevate", "filters", "Mann-Filter", 640, False, ["City", "Elevate", "Amaze"], "Multi-layer media for dusty Indian roads."),
    ("FLT-CAB-0026", "Bosch Cabin AC Filter with Activated Carbon", "filters", "Bosch", 790, False, MID_SUV + SEDANS + ["XUV700", "Hector"], "Blocks PM2.5, pollen and odours from the cabin."),
    ("FLT-FUL-0027", "Mahle Diesel Fuel Filter", "filters", "Mahle", 1290, False, ["Creta", "Seltos", "Harrier", "XUV700", "Scorpio-N", "Fortuner", "Hilux", "Thar", "Nexon"], "Water-separating fuel filter protects injectors."),
    # Electrical
    ("ELC-BAT-0030", "Exide Mileage 45Ah Battery", "electrical", "Exide", 5490, False, COMPACT + ["Brezza", "Venue", "Sonet"], "Maintenance-free battery with 48-month warranty."),
    ("ELC-BAT-0031", "Amaron Pro 65Ah Battery", "electrical", "Amaron", 7690, False, MID_SUV + MUVS + SEDANS, "Silver-alloy technology for high cranking power."),
    ("ELC-BAT-0032", "Amaron Hi-Life 80Ah Battery", "electrical", "Amaron", 9890, False, BIG_SUV + ["Hilux"], "Heavy-duty battery for large diesel SUVs."),
    ("ELC-LED-0033", "Philips Ultinon LED Headlight Bulbs H4", "electrical", "Philips", 4290, False, ["Swift", "Dzire", "Punch", "Amaze", "Ertiga", "Thar"], "Up to 160% brighter, 6000K cool white."),
    ("ELC-HRN-0034", "Bosch EC6 Twin Horn Set", "electrical", "Bosch", 1150, True, [], "Loud, weather-sealed 12V dual-tone horns."),
    ("ELC-CHG-0035", "Portronics Dual USB-C Fast Car Charger", "electrical", "Portronics", 899, True, [], "45W PD fast charging for phones and tablets."),
    ("ELC-DCM-0036", "70mai A500S Dash Cam with Rear Camera", "electrical", "70mai", 9990, True, [], "1944p front + 1080p rear recording, built-in GPS and ADAS alerts."),
    ("ELC-INF-0037", "Pioneer 9\" Android Infotainment Kit", "electrical", "Pioneer", 18990, False, ["Swift", "Dzire", "Baleno", "i20", "Amaze", "Glanza"], "Wireless CarPlay and Android Auto with fitting frame."),
    # Tyres & wheels
    ("TYR-MRF-0040", "MRF ZLX 185/65 R15 Tyre", "tyres-wheels", "MRF", 5290, False, ["Dzire", "Amaze", "Baleno", "Glanza", "i20", "Altroz"], "Quiet, fuel-efficient tubeless tyre."),
    ("TYR-MCH-0041", "Michelin Primacy 4 ST 215/60 R17", "tyres-wheels", "Michelin", 9650, False, ["Creta", "Seltos", "Elevate", "Astor", "Carens"], "Long-lasting comfort tyre with short wet braking distance."),
    ("TYR-BRG-0042", "Bridgestone Dueler 235/65 R17", "tyres-wheels", "Bridgestone", 11850, False, ["XUV700", "Scorpio-N", "Harrier", "Hector"], "SUV tyre balancing on-road comfort and off-road grip."),
    ("TYR-APL-0043", "Apollo Alnac 4G 195/55 R16", "tyres-wheels", "Apollo", 5890, False, ["City", "Verna", "Venue", "Sonet", "Nexon", "Brezza"], "Sporty handling with aqua-planing resistance."),
    ("TYR-INF-0044", "Michelin Digital Tyre Inflator", "tyres-wheels", "Michelin", 3490, True, [], "Programmable auto-stop inflator with LED torch."),
    ("TYR-TPM-0045", "Steelbird Solar TPMS (4 sensors)", "tyres-wheels", "Steelbird", 4290, True, [], "Real-time tyre pressure and temperature alerts."),
    # Body & exterior
    ("BDY-WPR-0050", "Bosch Clear Advantage Wiper Blades (pair)", "body-exterior", "Bosch", 1190, False, MID_SUV + SEDANS + COMPACT, "Frameless beam blades for streak-free wiping."),
    ("BDY-WPR-0051", "Valeo First Wiper Blades, large SUV (pair)", "body-exterior", "Valeo", 1490, False, BIG_SUV + MUVS + ["Hilux"], "All-season blades for long windscreens."),
    ("BDY-MIR-0052", "Hyundai Genuine Side Mirror, Right (Creta)", "body-exterior", "Hyundai Mobis", 6890, False, ["Creta"], "Electrically adjustable, folding, with turn indicator."),
    ("BDY-MDF-0053", "Mud Flaps Set of 4", "body-exterior", "Autofurnish", 790, False, COMPACT + MID_SUV, "Protects paint from stone chips and mud."),
    ("BDY-CVR-0054", "Water-Resistant Car Body Cover", "body-exterior", "Autofurnish", 1690, True, [], "Triple-layer cover with mirror pockets, UV protection."),
    ("BDY-RRL-0055", "Roof Rails, Aluminium (pair)", "body-exterior", "Thule", 7490, False, ["Creta", "Seltos", "Brezza", "Nexon", "Venue", "Sonet"], "Load-rated roof rails for carriers and bike racks."),
    # Interior
    ("INT-MAT-0060", "3D Custom-Fit Floor Mats", "interior", "Kagu", 3990, False, MID_SUV + SEDANS, "Laser-measured TPE mats with raised edges."),
    ("INT-MAT-0061", "7D Floor Mats, 7-seater", "interior", "Kagu", 5490, False, MUVS + ["XUV700", "Scorpio-N", "Fortuner"], "Full-coverage mats for all three rows."),
    ("INT-SCV-0062", "Leatherette Seat Covers (full set)", "interior", "Autofurnish", 6990, False, COMPACT + MID_SUV + SEDANS, "Perforated, breathable seat covers in black and beige."),
    ("INT-PHN-0063", "Magnetic Dashboard Phone Holder", "interior", "Spigen", 1299, True, [], "Strong N52 magnets, one-hand mounting."),
    ("INT-PRF-0064", "Godrej aer Twist Car Perfume", "interior", "Godrej", 349, True, [], "Gel-based freshener, lasts up to 60 days."),
    ("INT-PUR-0065", "Philips GoPure Car Air Purifier", "interior", "Philips", 7990, True, [], "Removes 99% of PM2.5 and bacteria from cabin air."),
    ("INT-ORG-0066", "Backseat Organiser with Tablet Holder", "interior", "Kagu", 899, True, [], "Multiple pockets and kick-mat protection."),
    # Car care
    ("CAR-SHP-0070", "3M Car Shampoo (1 L)", "car-care", "3M", 599, True, [], "pH-balanced foaming shampoo safe on wax and ceramic."),
    ("CAR-WAX-0071", "Meguiar's Ultimate Liquid Wax", "car-care", "Meguiar's", 2190, True, [], "Synthetic polymer wax for a deep, wet-look shine."),
    ("CAR-MFC-0072", "Microfibre Cloth Pack of 6", "car-care", "Sheeba", 449, True, [], "350 GSM, scratch-free drying and buffing."),
    ("CAR-CRM-0073", "Wavex Ceramic Coating Kit", "car-care", "Wavex", 2490, True, [], "DIY 9H ceramic coating, up to 12 months protection."),
    ("CAR-DSH-0074", "Armor All Dashboard Polish", "car-care", "Armor All", 399, True, [], "UV-protectant, non-greasy matte finish."),
    ("CAR-VAC-0075", "Black+Decker Cordless Car Vacuum", "car-care", "Black+Decker", 3290, True, [], "Powerful handheld vacuum with crevice tool."),
    ("CAR-GLS-0076", "Sonax Windscreen Washer Concentrate", "car-care", "Sonax", 299, True, [], "Streak-free washer fluid, makes 25 L."),
]

# Parts seeded at or below their reorder level so the low-stock alerts have something to show
LOW_STOCK_SKUS = {"FLT-AIR-0023": 2, "ELC-BAT-0032": 0, "TYR-MCH-0041": 3, "BRK-DSC-0015": 4, "INT-MAT-0061": 1, "ENG-CLT-0006": 2}
# Creta front pads sit one unit above the threshold: adding them to a job in the demo pushes them into the alert
NEAR_LOW_SKUS = {"BRK-PAD-0010": 6}

SERVICE_TYPES = [
    ("Wheel Alignment & Balancing", "Computerised 3D alignment plus balancing of all four wheels", "bi-vinyl", 799, 1.0),
    ("Oil & Filter Change", "Engine oil, oil filter and a 20-point safety check", "bi-droplet-half", 899, 1.0),
    ("Full Inspection", "75-point inspection with a detailed health report", "bi-search", 1199, 1.5),
    ("Brake Service", "Inspect, clean and adjust brakes; replace pads if worn", "bi-disc", 1499, 2.0),
    ("AC Service", "Gas top-up, condenser clean and cabin filter check", "bi-snow", 1799, 2.5),
    ("General Service", "Complete periodic maintenance as per manufacturer schedule", "bi-clipboard-check", 2499, 3.0),
]

COMPLAINTS = [
    "Squeaking noise when braking", "AC not cooling enough", "Steering pulls slightly to the left",
    "Check engine light came on", "Vibration at high speed", "Periodic service due", "Clutch feels hard",
    "Rattling sound from the dashboard", "Battery drains overnight", "", "", "",
]

STAFF = [
    # username, first, last, role, phone
    ("admin", "Arjun", "Mehta", "ADMIN", "9820012345"),
    ("sales1", "Priya", "Sharma", "SALES", "9820023456"),
    ("sales2", "Rohan", "Verma", "SALES", "9820034567"),
    ("sales3", "Neha", "Kapoor", "SALES", "9820045678"),
    ("mech1", "Suresh", "Patil", "MECHANIC", "9820056789"),
    ("mech2", "Imran", "Khan", "MECHANIC", "9820067890"),
    ("mech3", "Vikram", "Singh", "MECHANIC", "9820078901"),
    ("mech4", "Anil", "Joshi", "MECHANIC", "9820089012"),
]
