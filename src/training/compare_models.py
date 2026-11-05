import time
from pathlib import Path

import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from src.data.load_data import load_dataset
from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.preprocessing.preprocessing import create_preprocessor
from src.training.split_data import split_data

# Chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dossier contenant les résultats
RESULTS_DIR = PROJECT_ROOT / "data" / "processed"

# Fichier de comparaison
RESULTS_PATH = RESULTS_DIR / "model_comparison.csv"


def get_models():
    """
    Retourne les cinq algorithmes à comparer.
    """

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=150, random_state=42, n_jobs=-1
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100, random_state=42
        ),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=150, random_state=42, n_jobs=-1
        ),
    }

    return models


def compare_models():
    """
    Entraîne et compare les cinq algorithmes
    sur les mêmes données d'entraînement et de test.
    """

    print("\n========== SMARTCREDIT : MODEL COMPARISON ==========")

    # 1. Charger les données
    df = load_dataset()

    # 2. Nettoyer les données
    cleaned_df, report = clean_dataset(df)

    # 3. Séparer X et y
    X, y = split_features_target(cleaned_df)

    # 4. Séparer les données
    X_train, X_test, y_train, y_test = split_data(X, y)

    print("\nDonnées préparées.")
    print("X_train :", X_train.shape)
    print("X_test :", X_test.shape)

    # 5. Récupérer les algorithmes
    models = get_models()

    results = []

    # 6. Entraîner et évaluer chaque algorithme
    for model_name, estimator in models.items():

        print(f"\n========== {model_name} ==========")

        # Construire un pipeline indépendant pour chaque algorithme
        pipeline = Pipeline(
            steps=[("preprocessor", create_preprocessor()), ("model", estimator)]
        )

        # Entraînement
        start_time = time.perf_counter()

        pipeline.fit(X_train, y_train)

        training_time = time.perf_counter() - start_time

        # Prédictions
        start_time = time.perf_counter()

        y_pred = pipeline.predict(X_test)
        y_proba = pipeline.predict_proba(X_test)[:, 1]

        inference_time = time.perf_counter() - start_time

        # Calcul des métriques
        accuracy = accuracy_score(y_test, y_pred)

        precision = precision_score(y_test, y_pred, zero_division=0)

        recall = recall_score(y_test, y_pred, zero_division=0)

        f1 = f1_score(y_test, y_pred, zero_division=0)

        roc_auc = roc_auc_score(y_test, y_proba)

        pr_auc = average_precision_score(y_test, y_proba)

        # Affichage des résultats
        print(f"Accuracy  : {accuracy:.4f}")
        print(f"Precision : {precision:.4f}")
        print(f"Recall    : {recall:.4f}")
        print(f"F1-score  : {f1:.4f}")
        print(f"ROC-AUC   : {roc_auc:.4f}")
        print(f"PR-AUC    : {pr_auc:.4f}")
        print(f"Training time : {training_time:.4f} secondes")
        print(f"Inference time : {inference_time:.4f} secondes")

        # Enregistrer les résultats
        results.append(
            {
                "model": model_name,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "roc_auc": roc_auc,
                "pr_auc": pr_auc,
                "training_time_seconds": training_time,
                "inference_time_seconds": inference_time,
            }
        )

    # 7. Transformer les résultats en DataFrame
    results_df = pd.DataFrame(results)

    # 8. Trier par ROC-AUC décroissant
    results_df = results_df.sort_values(by="roc_auc", ascending=False)

    # 9. Créer le dossier de destination
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 10. Sauvegarder les résultats en CSV
    results_df.to_csv(RESULTS_PATH, index=False)

    # 11. Afficher le classement
    print("\n========== CLASSEMENT DES MODÈLES ==========")

    print(results_df.to_string(index=False, float_format=lambda value: f"{value:.4f}"))

    print("\nRésultats sauvegardés dans :")
    print(RESULTS_PATH)

    print("\n========== COMPARAISON TERMINÉE ==========")

    return results_df


if __name__ == "__main__":
    compare_models()
