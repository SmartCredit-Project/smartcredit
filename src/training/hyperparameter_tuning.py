
"""
SMARTCREDIT : HYPERPARAMETER TUNING

Objectif :
Rechercher les meilleures configurations pour :
1. Random Forest - Baseline
2. Gradient Boosting - Balanced
3. Decision Tree - Balanced

Méthode :
RandomizedSearchCV avec StratifiedKFold (5 plis).

Critère principal :
F1-score.
"""

import time
from pathlib import Path

import pandas as pd

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier
)
from sklearn.tree import DecisionTreeClassifier

from sklearn.pipeline import Pipeline
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold
)
from sklearn.metrics import make_scorer
from sklearn.utils.class_weight import compute_sample_weight

from src.preprocessing.cleaning import clean_dataset
from src.features.feature_selection import split_features_target
from src.training.split_data import split_data
from src.preprocessing.preprocessing import create_preprocessor


# ============================================================
# 1. CONFIGURATION
# ============================================================

RANDOM_STATE = 42
N_SPLITS = 5
N_ITER = 10

DATA_PATH = Path("data/raw/credit_risk_dataset.csv")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. GRADIENT BOOSTING AVEC GESTION DU DÉSÉQUILIBRE
# ============================================================

class BalancedGradientBoostingClassifier(
    ClassifierMixin,
    BaseEstimator
):
    """
    Gradient Boosting qui calcule automatiquement
    les poids des classes pendant chaque entraînement.

    Ainsi, pendant la validation croisée, les poids
    sont calculés uniquement avec les données du pli
    d'entraînement concerné.
    """

    def __init__(
        self,
        n_estimators=100,
        learning_rate=0.1,
        max_depth=3,
        min_samples_leaf=1,
        subsample=1.0,
        random_state=42
    ):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.subsample = subsample
        self.random_state = random_state

    def fit(self, X, y):

        sample_weights = compute_sample_weight(
            class_weight="balanced",
            y=y
        )

        self.model_ = GradientBoostingClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            subsample=self.subsample,
            random_state=self.random_state
        )

        self.model_.fit(
            X,
            y,
            sample_weight=sample_weights
        )

        self.classes_ = self.model_.classes_

        return self

    def predict(self, X):
        return self.model_.predict(X)

    def predict_proba(self, X):
        return self.model_.predict_proba(X)


# ============================================================
# 3. CHARGEMENT ET PRÉPARATION DES DONNÉES
# ============================================================

def prepare_data():

    print("\n" + "=" * 60)
    print("CHARGEMENT DES DONNÉES SMARTCREDIT")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)

    print(f"Dataset initial : {df.shape}")

    cleaned_df, report = clean_dataset(df)

    print(f"Dataset nettoyé : {cleaned_df.shape}")

    X, y = split_features_target(cleaned_df)

    X_train, X_test, y_train, y_test = split_data(X, y)

    print(f"X_train : {X_train.shape}")
    print(f"y_train : {y_train.shape}")
    print(f"X_test  : {X_test.shape}")
    print(f"y_test  : {y_test.shape}")

    print("\nDistribution des classes dans y_train :")
    print(y_train.value_counts(normalize=True))

    return X_train, y_train


# ============================================================
# 4. DÉFINITION DES MODÈLES ET HYPERPARAMÈTRES
# ============================================================

def get_search_configurations():

    configurations = {

        # ----------------------------------------------------
        # RANDOM FOREST - BASELINE
        # ----------------------------------------------------

        "Random Forest - Baseline": {

            "model": RandomForestClassifier(
                random_state=RANDOM_STATE,
                n_jobs=1
            ),

            "params": {

                "model__n_estimators": [
                    100, 150, 200, 300
                ],

                "model__max_depth": [
                    None, 10, 15, 20, 30
                ],

                "model__min_samples_split": [
                    2, 5, 10
                ],

                "model__min_samples_leaf": [
                    1, 2, 4
                ],

                "model__max_features": [
                    "sqrt", "log2", 0.8
                ],

                "model__class_weight": [
                    None
                ]
            }
        },

        # ----------------------------------------------------
        # GRADIENT BOOSTING - BALANCED
        # ----------------------------------------------------

        "Gradient Boosting - Balanced": {

            "model": BalancedGradientBoostingClassifier(
                random_state=RANDOM_STATE
            ),

            "params": {

                "model__n_estimators": [
                    50, 100, 150, 200
                ],

                "model__learning_rate": [
                    0.03, 0.05, 0.1, 0.15
                ],

                "model__max_depth": [
                    2, 3, 4
                ],

                "model__min_samples_leaf": [
                    1, 2, 4, 8
                ],

                "model__subsample": [
                    0.7, 0.85, 1.0
                ]
            }
        },

        # ----------------------------------------------------
        # DECISION TREE - BALANCED
        # ----------------------------------------------------

        "Decision Tree - Balanced": {

            "model": DecisionTreeClassifier(
                class_weight="balanced",
                random_state=RANDOM_STATE
            ),

            "params": {

                "model__max_depth": [
                    None, 5, 10, 15, 20, 30
                ],

                "model__min_samples_split": [
                    2, 5, 10, 20
                ],

                "model__min_samples_leaf": [
                    1, 2, 4, 8
                ],

                "model__criterion": [
                    "gini", "entropy", "log_loss"
                ]
            }
        }
    }

    return configurations


# ============================================================
# 5. OPTIMISATION D'UN MODÈLE
# ============================================================

def tune_model(
    model_name,
    estimator,
    param_distributions,
    X_train,
    y_train,
    cv
):

    print("\n" + "=" * 60)
    print(f"OPTIMISATION : {model_name}")
    print("=" * 60)

    # Création du pipeline complet
    pipeline = Pipeline(
        steps=[
            ("preprocessor", create_preprocessor()),
            ("model", estimator)
        ]
    )

    # Plusieurs métriques pour analyser le modèle
    scoring = {

        "accuracy": "accuracy",
        "precision": "precision",
        "recall": "recall",
        "f1": "f1",
        "roc_auc": "roc_auc",
        "pr_auc": "average_precision"
    }

    # Recherche des meilleures combinaisons
    search = RandomizedSearchCV(

        estimator=pipeline,

        param_distributions=param_distributions,

        n_iter=N_ITER,

        scoring=scoring,

        refit="f1",

        cv=cv,

        random_state=RANDOM_STATE,

        n_jobs=1,

        verbose=1,

        return_train_score=False
    )

    start_time = time.perf_counter()

    search.fit(X_train, y_train)

    elapsed_time = time.perf_counter() - start_time

    # Meilleurs résultats
    best_index = search.best_index_

    results = search.cv_results_

    print("\nMeilleurs hyperparamètres :")
    print(search.best_params_)

    print("\nMeilleurs résultats :")

    print(f"F1-score       : {results['mean_test_f1'][best_index]:.4f}")
    print(f"Precision      : {results['mean_test_precision'][best_index]:.4f}")
    print(f"Recall         : {results['mean_test_recall'][best_index]:.4f}")
    print(f"Accuracy       : {results['mean_test_accuracy'][best_index]:.4f}")
    print(f"ROC-AUC        : {results['mean_test_roc_auc'][best_index]:.4f}")
    print(f"PR-AUC         : {results['mean_test_pr_auc'][best_index]:.4f}")

    print(f"\nTemps total : {elapsed_time:.2f} secondes")

    # Résumé du meilleur modèle
    summary = {

        "model": model_name,

        "best_f1": results["mean_test_f1"][best_index],

        "best_f1_std": results["std_test_f1"][best_index],

        "precision": results["mean_test_precision"][best_index],

        "recall": results["mean_test_recall"][best_index],

        "accuracy": results["mean_test_accuracy"][best_index],

        "roc_auc": results["mean_test_roc_auc"][best_index],

        "pr_auc": results["mean_test_pr_auc"][best_index],

        "search_time_seconds": elapsed_time,

        "best_params": str(search.best_params_)
    }

    # Détails de toutes les combinaisons testées
    details = pd.DataFrame(results)

    details.insert(0, "model", model_name)

    return summary, details


# ============================================================
# 6. EXÉCUTION DE L'OPTIMISATION
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("SMARTCREDIT : HYPERPARAMETER TUNING")
    print("=" * 60)

    X_train, y_train = prepare_data()

    cv = StratifiedKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_STATE
    )

    configurations = get_search_configurations()

    all_summaries = []

    all_details = []

    for model_name, config in configurations.items():

        summary, details = tune_model(

            model_name=model_name,

            estimator=config["model"],

            param_distributions=config["params"],

            X_train=X_train,

            y_train=y_train,

            cv=cv
        )

        all_summaries.append(summary)

        all_details.append(details)

    # --------------------------------------------------------
    # ENREGISTREMENT DES RÉSULTATS
    # --------------------------------------------------------

    summary_df = pd.DataFrame(all_summaries)

    details_df = pd.concat(
        all_details,
        ignore_index=True
    )

    summary_df = summary_df.sort_values(
        by="best_f1",
        ascending=False
    )

    summary_path = (
        OUTPUT_DIR / "hyperparameter_tuning_summary.csv"
    )

    details_path = (
        OUTPUT_DIR / "hyperparameter_tuning_details.csv"
    )

    summary_df.to_csv(summary_path, index=False)

    details_df.to_csv(details_path, index=False)

    # --------------------------------------------------------
    # RÉSUMÉ FINAL
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("RÉSUMÉ FINAL DE L'OPTIMISATION")
    print("=" * 60)

    print(
        summary_df[
            [
                "model",
                "accuracy",
                "precision",
                "recall",
                "best_f1",
                "roc_auc",
                "pr_auc",
                "search_time_seconds"
            ]
        ].to_string(index=False)
    )

    print("\nFichiers enregistrés :")

    print(summary_path)

    print(details_path)

    print("\nOptimisation terminée avec succès !")


# ============================================================
# 7. POINT D'ENTRÉE DU PROGRAMME
# ============================================================

if __name__ == "__main__":

    main()
