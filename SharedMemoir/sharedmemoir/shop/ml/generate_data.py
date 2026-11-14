"""Step 1 of the ML part: create the training data.

MEMORA is a new shop, so we do not have real past orders yet. This script
creates 2,000 made-up (synthetic) past orders and saves them as
past_orders.csv. Each row is one finished memory book:

    travel ... everyday      1 if the customer ticked that occasion tag, else 0
    family ... colleagues    1 if the customer ticked that people tag, else 0
    group_size               how many people are in the story
    event_days               how many days the story spans
    photo_count              how many photos ended up in the book  <-- what we predict

Run it from the folder that contains manage.py:

    python shop/ml/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROWS = 2000
rng = np.random.default_rng(2108)  # fixed seed, so we get the same file every time

OCCASIONS = ["travel", "wedding", "sports", "celebrations", "everyday"]
PEOPLE = ["family", "friends", "classmates", "colleagues"]

# How often each occasion is ordered.
OCCASION_CHANCE = [0.35, 0.15, 0.15, 0.20, 0.15]

# Who usually appears in each kind of story (same order as PEOPLE).
PEOPLE_CHANCE = {
    "travel": [0.35, 0.40, 0.15, 0.10],
    "wedding": [0.60, 0.30, 0.05, 0.05],
    "sports": [0.10, 0.35, 0.35, 0.20],
    "celebrations": [0.40, 0.30, 0.15, 0.15],
    "everyday": [0.55, 0.30, 0.10, 0.05],
}

# Some people bring more photos than others.
PEOPLE_EXTRA_PHOTOS = {"family": 3, "friends": 1, "classmates": 2, "colleagues": -3}


def make_order():
    occasion = rng.choice(OCCASIONS, p=OCCASION_CHANCE)
    people = rng.choice(PEOPLE, p=PEOPLE_CHANCE[occasion])

    # Each occasion has its own typical group size, length and number of photos.
    if occasion == "travel":
        group_size = 1 + rng.poisson(3)
        event_days = 2 + rng.poisson(5)
        photos = 8 * np.sqrt(event_days) + 0.8 * group_size
    elif occasion == "wedding":
        group_size = 2 if rng.random() < 0.3 else 4 + rng.poisson(14)
        event_days = 1 + rng.poisson(0.6)
        photos = 22 + 0.5 * group_size + 4 * (event_days - 1)
    elif occasion == "sports":
        group_size = 2 + rng.poisson(8)
        event_days = 1 + rng.poisson(1.5)
        photos = 2 + 0.9 * group_size + 3.5 * event_days
    elif occasion == "celebrations":
        group_size = 2 + rng.poisson(6)
        event_days = 1 + rng.poisson(0.3)
        photos = 1 + 1.1 * group_size + 2 * event_days
    else:  # everyday
        group_size = 1 + rng.poisson(2)
        event_days = 1 + rng.poisson(20)
        photos = 1 + 2.5 * np.sqrt(event_days) + 1.0 * group_size

    photos = photos + PEOPLE_EXTRA_PHOTOS[people]

    # Start the row with every tag switched off, then switch on the chosen ones.
    row = {name: 0 for name in OCCASIONS + PEOPLE}
    row[occasion] = 1
    row[people] = 1

    # Some customers tick a second tag. A mixed story has a few more photos.
    if rng.random() < 0.15:
        row[rng.choice(OCCASIONS)] = 1
        photos = photos + 4
    if rng.random() < 0.20:
        row[rng.choice(PEOPLE)] = 1
        photos = photos + 2

    # Real customers are never perfectly predictable, so add random noise.
    photos = photos + rng.normal(0, 3.5)

    row["group_size"] = min(int(group_size), 50)   # same limits as the order form
    row["event_days"] = min(int(event_days), 60)
    row["photo_count"] = int(np.clip(round(photos), 1, 50))  # packages hold 1-50 photos
    return row


orders = pd.DataFrame([make_order() for _ in range(ROWS)])

csv_path = Path(__file__).resolve().parent / "past_orders.csv"
orders.to_csv(csv_path, index=False)

print(f"Saved {len(orders)} orders to {csv_path}")
print(orders.head())
