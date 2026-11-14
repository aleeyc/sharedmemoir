"""Step 2 of the ML part: train the model and save it with joblib.

The model is a regression model. It learns from past_orders.csv to predict
photo_count (how many photos a memory book will have) from the customer's
tags, group size and number of days.

The website (shop/recommender.py) loads the saved model and uses the
predicted photo count to recommend a photo package.

Run it from the folder that contains manage.py:

    python shop/ml/train_model.py
"""
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

ML_FOLDER = Path(__file__).resolve().parent

# 1. Load the data.
orders = pd.read_csv(ML_FOLDER / "past_orders.csv")
X = orders.drop(columns=["photo_count"])   # the 11 input columns (features)
y = orders["photo_count"]                  # the answer we want to predict (target)

# 2. Keep 20% of the orders aside. The model never sees them during training,
#    so we can use them to check how well it predicts new customers.
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Train three different algorithms on the same data, so we can compare them.
linear = LinearRegression()
linear.fit(X_train, y_train)

forest = RandomForestRegressor(n_estimators=200, min_samples_leaf=5, random_state=42)
forest.fit(X_train, y_train)

boosting = GradientBoostingRegressor(random_state=42)
boosting.fit(X_train, y_train)


# 4. Check each model on the 20% test orders.
def same_package(actual, predicted):
    """Share of orders where the prediction lands in the correct 10-photo package."""
    actual_package = (actual - 1) // 10
    predicted_package = (predicted.round() - 1) // 10
    return (actual_package == predicted_package).mean()


for name, candidate in [("Linear regression", linear), ("Random forest", forest), ("Gradient boosting", boosting)]:
    predicted = candidate.predict(X_test)
    print(name)
    print(f"  Mean absolute error: {mean_absolute_error(y_test, predicted):.2f} photos")
    print(f"  R-squared:           {r2_score(y_test, predicted):.2f}")
    print(f"  Correct package:     {same_package(y_test, predicted):.0%}")

# 5. Gradient boosting has the lowest error, so that is the model we keep.
#    Save it in joblib format for the website to load.
model_path = ML_FOLDER / "photo_model.joblib"
joblib.dump(boosting, model_path)
print(f"Saved the model to {model_path}")
