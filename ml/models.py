"""
models.py — Model creation for race outcome prediction.

Baseline: RandomForestRegressor predicting finishing position.
"""
from sklearn.ensemble import RandomForestRegressor


def create_model() -> RandomForestRegressor:
    """
    Create and return the baseline RandomForestRegressor.

    Hyperparameters are intentionally conservative for the v1 baseline.
    """
    return RandomForestRegressor(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
