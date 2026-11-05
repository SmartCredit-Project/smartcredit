import time
from pathlib import Path

import pandas as pd
from sklearn.base import clone
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
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.class_weight import compute_sample_weight

from src.data.load_data import load_dataset
from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.preprocessing.preprocessing import create_preprocessor
from src.training.split_data import split_data

# Chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dossier des résultats
RESULTS_DIR = PROJECT_ROOT / "data" / "processed"

SUMMARY_PATH = RESULTS_DIR / "model_comparison_imbalance_cv.csv"
FOLDS_PATH = RESULTS_DIR / "model_comparison_imbalance_cv_folds.csv"


def get_experiments():
    """
    Retourne les modèles en version normale et équilibrée.

    use_sample_weight indique si nous devons transmettre
    des poids à l'entraînement du modèle.
    """

    experiments = []

    # 1. Logistic Regression
    experiments.append(
        (
            "Logistic Regression - Baseline",
            LogisticRegression(max_iter=1000, random_state=42),
            False,
        )
    )

    experiments.append(
        (
            "Logistic Regression - Balanced",
            LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced"),
            False,
        )
    )

    # 2. Decision Tree
    experiments.append(
        ("Decision Tree - Baseline", DecisionTreeClassifier(random_state=42), False)
    )

    experiments.append(
        (
            "Decision Tree - Balanced",
            DecisionTreeClassifier(random_state=42, class_weight="balanced"),
            False,
        )
    )

    # 3. Random Forest
    experiments.append(
        (
            "Random Forest - Baseline",
            RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1),
            False,
        )
    )

    experiments.append(
        (
            "Random Forest - Balanced",
            RandomForestClassifier(
                n_estimators=150, random_state=42, n_jobs=-1, class_weight="balanced"
            ),
            False,
        )
    )

    # 4. Gradient Boosting
    experiments.append(
        (
            "Gradient Boosting - Baseline",
            GradientBoostingClassifier(n_estimators=100, random_state=42),
            False,
        )
    )

    experiments.append(
        (
            "Gradient Boosting - Balanced",
            GradientBoostingClassifier(n_estimators=100, random_state=42),
            True,
        )
    )

    # 5. Extra Trees
    experiments.append(
        (
            "Extra Trees - Baseline",
            ExtraTreesClassifier(n_estimators=150, random_state=42, n_jobs=-1),
            False,
        )
    )

    experiments.append(
        (
            "Extra Trees - Balanced",
            ExtraTreesClassifier(
                n_estimators=150, random_state=42, n_jobs=-1, class_weight="balanced"
            ),
            False,
        )
    )

    return experiments


def calculate_metrics(y_true, y_pred, y_proba):
    """
    Calcule les métriques de classification.
    La classe positive est la classe 1 : défaut de remboursement.
    """

    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_true, y_proba),
        "pr_auc": average_precision_score(y_true, y_proba),
    }


def compare_imbalance():

    print("\n========== SMARTCREDIT : CLASS IMBALANCE EXPERIMENT ==========")

    # 1. Charger les données
    df = load_dataset()

    # 2. Nettoyer les données
    cleaned_df, report = clean_dataset(df)

    # 3. Séparer les variables explicatives et la cible
    X, y = split_features_target(cleaned_df)

    # 4. Séparer entraînement et test
    X_train, X_test, y_train, y_test = split_data(X, y)

    print("\nDonnées préparées.")
    print("X_train :", X_train.shape)
    print("y_train :", y_train.shape)
    print("X_test  :", X_test.shape)
    print("y_test  :", y_test.shape)

    print("\nDistribution des classes dans y_train :")
    print(y_train.value_counts(normalize=True).sort_index())

    # 5. Validation croisée stratifiée à 5 plis
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    experiments = get_experiments()

    summary_results = []
    fold_results = []

    # 6. Évaluer chaque expérience
    for experiment_name, estimator, use_sample_weight in experiments:

        print(f"\n========== {experiment_name} ==========")

        fold_metrics = []
        fit_times = []
        score_times = []

        # Chaque pli possède ses propres données d'entraînement
        for fold_number, (train_indices, valid_indices) in enumerate(
            cv.split(X_train, y_train), start=1
        ):

            X_fold_train = X_train.iloc[train_indices]
            X_fold_valid = X_train.iloc[valid_indices]

            y_fold_train = y_train.iloc[train_indices]
            y_fold_valid = y_train.iloc[valid_indices]

            # Construire un nouveau Pipeline pour ce pli
            pipeline = Pipeline(
                steps=[
                    ("preprocessor", create_preprocessor()),
                    ("model", clone(estimator)),
                ]
            )

            # 7. Préparer les poids uniquement pour Gradient Boosting équilibré
            fit_params = {}

            if use_sample_weight:
                weights = compute_sample_weight(class_weight="balanced", y=y_fold_train)

                fit_params["model__sample_weight"] = weights

            # 8. Entraîner le Pipeline
            start_time = time.perf_counter()

            pipeline.fit(X_fold_train, y_fold_train, **fit_params)

            training_time = time.perf_counter() - start_time

            # 9. Évaluer le modèle sur le pli de validation
            start_time = time.perf_counter()

            y_pred = pipeline.predict(X_fold_valid)
            y_proba = pipeline.predict_proba(X_fold_valid)[:, 1]

            scoring_time = time.perf_counter() - start_time

            metrics = calculate_metrics(y_fold_valid, y_pred, y_proba)

            metrics["fold"] = fold_number

            fold_metrics.append(metrics)
            fit_times.append(training_time)
            score_times.append(scoring_time)

            fold_results.append(
                {
                    "experiment": experiment_name,
                    "fold": fold_number,
                    **metrics,
                    "training_time_seconds": training_time,
                    "inference_time_seconds": scoring_time,
                }
            )

        # 10. Calculer moyenne et écart-type des métriques
        metrics_df = pd.DataFrame(fold_metrics)

        result = {"experiment": experiment_name}

        for metric in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc"]:
            result[f"{metric}_mean"] = metrics_df[metric].mean()
            result[f"{metric}_std"] = metrics_df[metric].std()

        result["training_time_mean"] = sum(fit_times) / len(fit_times)
        result["inference_time_mean"] = sum(score_times) / len(score_times)

        summary_results.append(result)

        print(
            f"Accuracy : {result['accuracy_mean']:.4f} "
            f"+/- {result['accuracy_std']:.4f}"
        )

        print(
            f"Precision : {result['precision_mean']:.4f} "
            f"+/- {result['precision_std']:.4f}"
        )

        print(
            f"Recall : {result['recall_mean']:.4f} " f"+/- {result['recall_std']:.4f}"
        )

        print(f"F1-score : {result['f1_mean']:.4f} " f"+/- {result['f1_std']:.4f}")

        print(
            f"ROC-AUC : {result['roc_auc_mean']:.4f} "
            f"+/- {result['roc_auc_std']:.4f}"
        )

        print(
            f"PR-AUC : {result['pr_auc_mean']:.4f} " f"+/- {result['pr_auc_std']:.4f}"
        )

    # 11. Créer les DataFrames
    summary_df = pd.DataFrame(summary_results)
    folds_df = pd.DataFrame(fold_results)

    # 12. Trier selon le F1-score moyen
    summary_df = summary_df.sort_values(by="f1_mean", ascending=False)

    # 13. Enregistrer les résultats
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summary_df.to_csv(SUMMARY_PATH, index=False)
    folds_df.to_csv(FOLDS_PATH, index=False)

    print("\n========== RÉSUMÉ FINAL ==========")

    print(summary_df.to_string(index=False, float_format=lambda value: f"{value:.4f}"))

    print("\nFichiers enregistrés :")
    print(SUMMARY_PATH)
    print(FOLDS_PATH)

    return summary_df


if __name__ == "__main__":
    compare_imbalance()
