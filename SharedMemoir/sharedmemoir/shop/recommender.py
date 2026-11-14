"""Connects the trained ML model to the shop.

The model (shop/ml/photo_model.joblib, trained by shop/ml/train_model.py)
predicts how many photos a memory book will have. We use that number to
recommend a photo package to the customer.
"""
from pathlib import Path

import joblib
import pandas as pd

from .models import PackageTier

MODEL_PATH = Path(__file__).resolve().parent / "ml" / "photo_model.joblib"

# Load the model once when Django starts, not on every page request.
model = joblib.load(MODEL_PATH)


def predict_photo_count(tag_names, group_size, event_days):
    """Ask the model how many photos a story like this usually has."""
    # Build one row with the same columns the model was trained on.
    # Every tag column starts at 0 ("not ticked").
    row = {column: 0 for column in model.feature_names_in_}
    for name in tag_names:
        column = name.lower()       # the tag "Travel" is the column "travel"
        if column in row:           # a tag the model has never seen is skipped
            row[column] = 1
    row["group_size"] = group_size
    row["event_days"] = event_days

    prediction = model.predict(pd.DataFrame([row]))[0]
    return max(1, int(round(prediction)))   # a whole number of photos, at least 1


def recommend_tier(story):
    """Return (recommended package, predicted photo count).

    story is the cleaned_data of a valid StoryForm or ConfigureForm.
    """
    tag_names = [tag.name for tag in story["occasion_tags"]]
    tag_names += [tag.name for tag in story["people_tags"]]
    photos = predict_photo_count(tag_names, story["group_size"], story["event_days"])

    # Recommend the smallest active package that still fits that many photos.
    tiers = PackageTier.objects.filter(is_active=True)
    tier = tiers.filter(max_photos__gte=photos).order_by("max_photos").first()
    if tier is None:
        # More photos than any package holds: recommend the biggest package.
        tier = tiers.order_by("-max_photos").first()
    return tier, photos
