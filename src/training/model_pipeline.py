from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.preprocessing.preprocessing import create_preprocessor


def create_logistic_regression_pipeline():
    """
    Construit un pipeline complet composé de :
    1. Prétraitement des données.
    2. Régression logistique.
    """

    pipeline = Pipeline(
        steps=[
            ("preprocessor", create_preprocessor()),
            ("model", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )

    return pipeline
