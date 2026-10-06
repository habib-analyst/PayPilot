"""
Mock product catalog for the PayPilot demo store.

In a real deployment this would be a merchant's product database or a
marketplace API. For the hackathon it is a curated local catalog so the
agentic-commerce loop (search -> compare -> PayPal checkout -> capture)
is fully demonstrable in the sandbox.
"""

from __future__ import annotations

PRODUCTS: list[dict] = [
    {
        "id": "p001",
        "name": "Aurora X9 Noise-Cancelling Headphones",
        "category": "audio",
        "price": 189.99,
        "currency": "USD",
        "rating": 4.7,
        "reviews": 2314,
        "description": "Over-ear Bluetooth headphones, 40h battery, hybrid ANC, USB-C fast charge.",
        "tags": ["headphones", "audio", "noise cancelling", "bluetooth", "travel"],
    },
    {
        "id": "p002",
        "name": "PulseBuds Pro Wireless Earbuds",
        "category": "audio",
        "price": 89.99,
        "currency": "USD",
        "rating": 4.5,
        "reviews": 5821,
        "description": "In-ear wireless earbuds, wireless charging case, IPX5 sweat resistant.",
        "tags": ["earbuds", "audio", "wireless", "running", "gym"],
    },
    {
        "id": "p003",
        "name": "VoltCore 65W GaN Fast Charger",
        "category": "accessories",
        "price": 39.99,
        "currency": "USD",
        "rating": 4.8,
        "reviews": 9102,
        "description": "65W GaN charger, 2x USB-C + 1x USB-A, folds flat for travel.",
        "tags": ["charger", "usb-c", "travel", "laptop", "phone"],
    },
    {
        "id": "p004",
        "name": "LumenDesk 34in Ultrawide Monitor",
        "category": "computing",
        "price": 449.00,
        "currency": "USD",
        "rating": 4.6,
        "reviews": 1187,
        "description": "34-inch 1440p ultrawide IPS, 144Hz, HDR400, height-adjustable stand.",
        "tags": ["monitor", "ultrawide", "gaming", "productivity", "desk setup"],
    },
    {
        "id": "p005",
        "name": "TypeFlow Mechanical Keyboard",
        "category": "computing",
        "price": 119.00,
        "currency": "USD",
        "rating": 4.7,
        "reviews": 3340,
        "description": "75% mechanical keyboard, hot-swappable switches, PBT keycaps, 2.4GHz + BT.",
        "tags": ["keyboard", "mechanical", "typing", "desk setup", "coding"],
    },
    {
        "id": "p006",
        "name": "StrideBand Fitness Tracker",
        "category": "wearables",
        "price": 59.99,
        "currency": "USD",
        "rating": 4.4,
        "reviews": 12044,
        "description": "Heart-rate + SpO2 tracking, 14-day battery, 5ATM water resistance.",
        "tags": ["fitness", "tracker", "running", "health", "wearable"],
    },
    {
        "id": "p007",
        "name": "OrbitCam 4K Action Camera",
        "category": "cameras",
        "price": 249.99,
        "currency": "USD",
        "rating": 4.6,
        "reviews": 2876,
        "description": "4K60 action camera, waterproof to 10m, image stabilization, 128GB support.",
        "tags": ["camera", "action cam", "4k", "travel", "vlogging"],
    },
    {
        "id": "p008",
        "name": "Nimbus Go Power Bank 20000mAh",
        "category": "accessories",
        "price": 34.99,
        "currency": "USD",
        "rating": 4.5,
        "reviews": 15620,
        "description": "20000mAh power bank, 22.5W fast charge, dual USB-C output, LED display.",
        "tags": ["power bank", "charger", "travel", "phone"],
    },
    {
        "id": "p009",
        "name": "EchoStand Laptop Stand Pro",
        "category": "computing",
        "price": 49.99,
        "currency": "USD",
        "rating": 4.6,
        "reviews": 4210,
        "description": "Aluminum laptop stand, adjustable height/angle, fits 11-17 inch laptops.",
        "tags": ["laptop", "stand", "ergonomic", "desk setup", "remote work"],
    },
    {
        "id": "p010",
        "name": "TerraGrow Smart Herb Garden",
        "category": "home",
        "price": 129.99,
        "currency": "USD",
        "rating": 4.3,
        "reviews": 987,
        "description": "Indoor smart garden, automated LED grow light + watering, app controlled.",
        "tags": ["smart home", "garden", "gift", "kitchen"],
    },
    {
        "id": "p011",
        "name": "SonicBar Mini Soundbar",
        "category": "audio",
        "price": 149.99,
        "currency": "USD",
        "rating": 4.5,
        "reviews": 1932,
        "description": "Compact Dolby Atmos soundbar, HDMI ARC, Bluetooth 5.3, wall-mountable.",
        "tags": ["soundbar", "audio", "tv", "home theater"],
    },
    {
        "id": "p012",
        "name": "AeroPack 25L Travel Backpack",
        "category": "travel",
        "price": 79.99,
        "currency": "USD",
        "rating": 4.7,
        "reviews": 6530,
        "description": "25L anti-theft travel backpack, USB passthrough, fits 16in laptop.",
        "tags": ["backpack", "travel", "laptop", "commute"],
    },
]


def search(query: str, max_price: float | None = None, category: str | None = None) -> list[dict]:
    q = query.lower().strip()
    terms = [t for t in q.split() if len(t) > 2]
    results: list[tuple[float, dict]] = []
    for p in PRODUCTS:
        if max_price is not None and p["price"] > max_price:
            continue
        if category and p["category"] != category.lower():
            continue
        hay = f"{p['name']} {p['description']} {p['category']} {' '.join(p['tags'])}".lower()
        score = sum(2.0 if t in p["name"].lower() else 1.0 for t in terms if t in hay)
        # small boost for highly rated items so the agent recommends quality
        score += p["rating"] / 10.0
        if score > 0.5:
            results.append((score, p))
    results.sort(key=lambda r: -r[0])
    return [p for _, p in results[:6]]


def get(product_id: str) -> dict | None:
    return next((p for p in PRODUCTS if p["id"] == product_id), None)
