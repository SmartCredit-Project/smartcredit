import pandas as pd

from pathlib import Path

from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_validate

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier
)

from src.data.load_data import load_dataset
from src.preprocessing.cleaning import clean_dataset
from src.features.feature_selection import split_features_target
from src.training.split_data import split_data
from src.preprocessing.preprocessing import create_preprocessor


# Chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dossier où seront enregistrés les résultats
RESULTS_DIR = PROJECT_ROOT / "data" / "processed"

# Fichiers de résultats
SUMMARY_PATH = RESULTS_DIR / "model_comparison_cv.csv"
FOLDS_PATH = RESULTS_DIR / "model_comparison_cv_folds.csv"


def get_models():
    """
    Retourne les cinq modèles que nous voulons comparer.
    """

    return {
        "Logistic Regression": LogisticRegression(
            max_iter=1000,
            random_state=42
        ),

        "Decision Tree": DecisionTreeClassifier(
            random_state=42
        ),

        "Random Forest": RandomForestClassifier(
            n_estimators=150,
            random_state=42,
            n_jobs=-1
        ),

        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100,
            random_state=42
        ),

        "Extra Trees": ExtraTreesClassifier(
            n_estimators=150,
            random_state=42,
            n_jobs=-1
        )
    }


def compare_models_cv():

    print("\n========== SMARTCREDIT : 5-FOLD CROSS-VALIDATION ==========")

    # 1. Charger les données
    df = load_dataset()

    # 2. Nettoyer les données
    cleaned_df, report = clean_dataset(df)

    # 3. Séparer les variables explicatives et la cible
    X, y = split_features_target(cleaned_df)

    # 4. Séparer les données en entraînement et test
    X_train, X_test, y_train, y_test = split_data(X, y)

    print("\nDonnées préparées.")
    print("X_train :", X_train.shape)
    print("y_train :", y_train.shape)
    print("X_test  :", X_test.shape)
    print("y_test  :", y_test.shape)

    # 5. Définir la validation croisée stratifiée à 5 plis
    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=42
    )

    # 6. Définir les métriques d'évaluation
    scoring = {
        "accuracy": "accuracy",
        "precision": "precision",
        "recall": "recall",
        "f1": "f1",
        "roc_auc": "roc_auc",
        "pr_auc": "average_precision"
    }

    # 7. Récupérer les modèles
    models = get_models()

    summary_results = []
    fold_results = []

    # 8. Évaluer chaque modèle
    for model_name, estimator in models.items():

        print(f"\n========== {model_name} ==========")

        # Le prétraitement est intégré au modèle
        pipeline = Pipeline(steps=[
            ("preprocessor", create_preprocessor()),
            ("model", estimator)
        ])

        # Validation croisée sur les données d'entraînement uniquement
        scores = cross_validate(
            estimator=pipeline,
            X=X_train,
            y=y_train,
            cv=cv,
            scoring=scoring,
            return_train_score=False,
            n_jobs=1,
            error_score="raise"
        )

        # 9. Calculer les moyennes et écarts-types
        result = {
            "model": model_name,

            "accuracy_mean": scores["test_accuracy"].mean(),
            "accuracy_std": scores["test_accuracy"].std(),

            "precision_mean": scores["test_precision"].mean(),
            "precision_std": scores["test_precision"].std(),

            "recall_mean": scores["test_recall"].mean(),
            "recall_std": scores["test_recall"].std(),

            "f1_mean": scores["test_f1"].mean(),
            "f1_std": scores["test_f1"].std(),

            "roc_auc_mean": scores["test_roc_auc"].mean(),
            "roc_auc_std": scores["test_roc_auc"].std(),

            "pr_auc_mean": scores["test_pr_auc"].mean(),
            "pr_auc_std": scores["test_pr_auc"].std(),

            "fit_time_mean": scores["fit_time"].mean(),
            "score_time_mean": scores["score_time"].mean()
        }

        summary_results.append(result)

        # 10. Conserver les résultats de chaque pli
        for fold_index in range(5):

            fold_results.append({
                "model": model_name,
                "fold": fold_index + 1,
                "accuracy": scores["test_accuracy"][fold_index],
                "precision": scores["test_precision"][fold_index],
                "recall": scores["test_recall"][fold_index],
                "f1": scores["test_f1"][fold_index],
                "roc_auc": scores["test_roc_auc"][fold_index],
                "pr_auc": scores["test_pr_auc"][fold_index],
                "fit_time": scores["fit_time"][fold_index],
                "score_time": scores["score_time"][fold_index]
            })

        print(
            f"Accuracy : "
            f"{result['accuracy_mean']:.4f} "
            f"+/- {result['accuracy_std']:.4f}"
        )

        print(
            f"Precision : "
            f"{result['precision_mean']:.4f} "
            f"+/- {result['precision_std']:.4f}"
        )

        print(
            f"Recall : "
            f"{result['recall_mean']:.4f} "
            f"+/- {result['recall_std']:.4f}"
        )

        print(
            f"F1-score : "
            f"{result['f1_mean']:.4f} "
            f"+/- {result['f1_std']:.4f}"
        )

        print(
            f"ROC-AUC : "
            f"{result['roc_auc_mean']:.4f} "
            f"+/- {result['roc_auc_std']:.4f}"
        )

        print(
            f"PR-AUC : "
            f"{result['pr_auc_mean']:.4f} "
            f"+/- {result['pr_auc_std']:.4f}"
        )

        print(
            f"Temps moyen d'entraînement : "
            f"{result['fit_time_mean']:.4f} secondes"
        )

        print(
            f"Temps moyen de scoring : "
            f"{result['score_time_mean']:.4f} secondes"
        )

    # 11. Transformer les résultats en DataFrames
    summary_df = pd.DataFrame(summary_results)
    folds_df = pd.DataFrame(fold_results)

    # 12. Trier les modèles par ROC-AUC moyen
    summary_df = summary_df.sort_values(
        by="roc_auc_mean",
        ascending=False
    )

    # 13. Créer le dossier des résultats s'il n'existe pas
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 14. Enregistrer les résultats dans des fichiers CSV
    summary_df.to_csv(SUMMARY_PATH, index=False)
    folds_df.to_csv(FOLDS_PATH, index=False)

    print("\n========== RÉSUMÉ FINAL ==========")

    print(
        summary_df.to_string(
            index=False,
            float_format=lambda value: f"{value:.4f}"
        )
    )

    print("\nFichiers enregistrés :")
    print(SUMMARY_PATH)
    print(FOLDS_PATH)

    return summary_df


if __name__ == "__main__":
    compare_models_cv()
