#!/usr/bin/env python3
"""Generate realistic sample CSV files for pipeline demo."""

import random
import csv
import os

random.seed(42)

# ── Products CSV ──────────────────────────────────────────────────────────────
products = []
categories = ["Electronics", "Books", "Clothing", "Home & Garden", "Sports"]
adjectives = ["Premium", "Ultra", "Classic", "Pro", "Deluxe", "Smart", "Eco"]
items = ["Headphones", "Keyboard", "Watch", "Backpack", "Lamp", "Notebook", "Jacket"]

for i in range(500):
    name = f"{random.choice(adjectives)} {random.choice(items)} {random.randint(100,999)}"
    products.append({
        "id": i + 1,
        "name": name,
        "category": random.choice(categories),
        "price": round(random.uniform(9.99, 499.99), 2),
        "rating": round(random.uniform(1.0, 5.0), 1),
        "reviews": random.randint(0, 5000),
        "description": f"This {name.lower()} is designed for everyday use. "
                       f"Features include high durability, modern design, and exceptional performance. "
                       f"Perfect for professionals and enthusiasts alike. "
                       f"Available in multiple variants with free shipping on orders over $50.",
        "in_stock": random.choice([True, False, None]),  # introduce some nulls
        "sku": f"SKU-{random.randint(10000,99999)}" if random.random() > 0.1 else None,
    })

os.makedirs("data", exist_ok=True)
with open("data/products.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=products[0].keys())
    writer.writeheader()
    writer.writerows(products)

# ── Customers CSV (with messy data) ──────────────────────────────────────────
first_names = ["Alice", "Bob", "Carlos", "Diana", "Ethan", "Fatima", "George"]
last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
cities = ["New York", "London", "Cairo", "Tokyo", "Berlin", "Sydney", "Mumbai"]

customers = []
for i in range(300):
    customers.append({
        "customer_id": f"C{1000 + i}",
        "first_name": random.choice(first_names),
        "last_name": random.choice(last_names) if random.random() > 0.05 else None,
        "email": f"user{i}@example.com" if random.random() > 0.03 else "",
        "city": random.choice(cities),
        "age": random.randint(18, 75) if random.random() > 0.1 else None,
        "loyalty_points": random.randint(0, 10000),
        "bio": f"Customer from {random.choice(cities)} interested in {random.choice(categories).lower()}. "
               f"Member since {random.randint(2015, 2024)}. Prefers {random.choice(['email', 'SMS', 'push'])} notifications.",
    })

# Inject duplicates and fully null rows for cleaning demo
customers.append(customers[0].copy())
customers.append(customers[10].copy())
customers.append({k: None for k in customers[0].keys()})

with open("data/customers.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=customers[0].keys())
    writer.writeheader()
    writer.writerows(customers)

# ── Reviews CSV ───────────────────────────────────────────────────────────────
sentiments = ["positive", "negative", "neutral"]
review_texts = [
    "Absolutely love this product! Works exactly as described and arrived fast.",
    "Disappointed with the quality. Expected much better for the price.",
    "Decent product overall. Nothing exceptional but gets the job done.",
    "Five stars! Best purchase I've made this year. Highly recommend.",
    "Returned immediately. The item was damaged upon arrival.",
    "Good value for money. Setup was straightforward and quick.",
    "Outstanding build quality. Premium feel and works flawlessly.",
    "Average product. The description was slightly misleading.",
]

reviews = []
for i in range(400):
    reviews.append({
        "review_id": f"R{5000 + i}",
        "product_id": random.randint(1, 500),
        "stars": random.randint(1, 5),
        "sentiment": random.choice(sentiments),
        "review_text": random.choice(review_texts) + f" Order #{random.randint(10000,99999)}.",
        "helpful_votes": random.randint(0, 200) if random.random() > 0.15 else None,
        "verified_purchase": random.choice(["yes", "no"]),
        "date": f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
    })

with open("data/reviews.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=reviews[0].keys())
    writer.writeheader()
    writer.writerows(reviews)

print("✓ Generated sample CSVs in data/:")
print(f"  • products.csv  — {len(products)} rows")
print(f"  • customers.csv — {len(customers)} rows (incl. 2 dupes + 1 null row)")
print(f"  • reviews.csv   — {len(reviews)} rows")
