"""
SMARTCREDIT : THRESHOLD TUNING

Objectif :
Trouver un seuil de décision adapté pour :
1. Random Forest optimisé
2. Gradient Boosting Balanced optimisé

Méthode :
Out-of-Fold Predictions avec StratifiedKFold à 5 plis.

Critère principal :
F1-score.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline

from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.preprocessing.preprocessing import create_preprocessor
from src.training.hyperparameter_tuning import BalancedGradientBoostingClassifier
from src.training.split_data import split_data

# ============================================================
# 1. CONFIGURATION
# ============================================================

RANDOM_STATE = 42
N_SPLITS = 5

DATA_PATH = Path("data/raw/credit_risk_dataset.csv")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Seuils à tester : de 0.10 à 0.90
THRESHOLDS = np.linspace(0.10, 0.90, 81)


# ============================================================
# 2. CHARGEMENT DES DONNÉES
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

    print("\nDistribution des classes dans y_train :")
    print(y_train.value_counts(normalize=True))

    # Nous utilisons uniquement les données d'entraînement.
    # X_test et y_test restent réservés à l'évaluation finale.

    return X_train, y_train


# ============================================================
# 3. CONSTRUCTION DES MODÈLES OPTIMISÉS
# ============================================================


def get_optimized_models():

    models = {
        # ----------------------------------------------------
        # RANDOM FOREST OPTIMISÉ
        # ----------------------------------------------------
        "Random Forest - Optimized": RandomForestClassifier(
            n_estimators=150,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features=0.8,
            max_depth=None,
            class_weight=None,
            random_state=RANDOM_STATE,
            n_jobs=1,
        ),
        # ----------------------------------------------------
        # GRADIENT BOOSTING BALANCED OPTIMISÉ
        # ----------------------------------------------------
        "Gradient Boosting - Balanced Optimized": BalancedGradientBoostingClassifier(
            subsample=0.7,
            n_estimators=150,
            min_samples_leaf=2,
            max_depth=4,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
        ),
    }

    return models


# ============================================================
# 4. CALCUL DES MÉTRIQUES POUR UN SEUIL
# ============================================================


def evaluate_threshold(y_true, probabilities, threshold):

    # Transformer les probabilités en classes
    y_pred = (probabilities >= threshold).astype(int)

    # Calcul des métriques
    accuracy = accuracy_score(y_true, y_pred)

    precision = precision_score(y_true, y_pred, zero_division=0)

    recall = recall_score(y_true, y_pred, zero_division=0)

    f1 = f1_score(y_true, y_pred, zero_division=0)

    # Matrice de confusion
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    # Capacité à reconnaître la classe 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

    return {
        "threshold": threshold,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "true_positive": tp,
    }


# ============================================================
# 5. RECHERCHE DU MEILLEUR SEUIL
# ============================================================


def find_best_threshold(model_name, estimator, X_train, y_train, cv):

    print("\n" + "=" * 60)
    print(f"THRESHOLD TUNING : {model_name}")
    print("=" * 60)

    # Pipeline complet : prétraitement + modèle
    pipeline = Pipeline(
        steps=[("preprocessor", create_preprocessor()), ("model", estimator)]
    )

    print("\nCalcul des probabilités Out-of-Fold...")

    # Chaque observation reçoit une probabilité
    # calculée par un modèle qui ne l'a pas entraînée.
    probabilities = cross_val_predict(
        estimator=pipeline,
        X=X_train,
        y=y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
        verbose=1,
    )

    # Récupérer la colonne correspondant à la classe 1
    class_index = list(np.unique(y_train)).index(1)

    probabilities_class_1 = probabilities[:, class_index]

    print("\nProbabilités calculées.")

    # --------------------------------------------------------
    # ÉVALUATION DU SEUIL PAR DÉFAUT : 0.50
    # --------------------------------------------------------

    default_result = evaluate_threshold(y_train, probabilities_class_1, 0.50)

    print("\nRésultats avec le seuil 0.50 :")

    print(f"Accuracy  : {default_result['accuracy']:.4f}")
    print(f"Precision : {default_result['precision']:.4f}")
    print(f"Recall    : {default_result['recall']:.4f}")
    print(f"F1-score  : {default_result['f1']:.4f}")

    # --------------------------------------------------------
    # TEST DE PLUSIEURS SEUILS
    # --------------------------------------------------------

    threshold_results = []

    for threshold in THRESHOLDS:

        result = evaluate_threshold(y_train, probabilities_class_1, threshold)

        threshold_results.append(result)

    results_df = pd.DataFrame(threshold_results)

    # --------------------------------------------------------
    # SÉLECTION DU MEILLEUR SEUIL SELON F1
    # --------------------------------------------------------

    max_f1 = results_df["f1"].max()

    best_candidates = results_df[np.isclose(results_df["f1"], max_f1)].copy()

    # En cas d'égalité, choisir le seuil le plus proche de 0.50.
    best_row = best_candidates.loc[(best_candidates["threshold"] - 0.50).abs().idxmin()]

    best_threshold = best_row["threshold"]

    print("\nMeilleur seuil trouvé :")

    print(f"Threshold  : {best_threshold:.2f}")
    print(f"Accuracy   : {best_row['accuracy']:.4f}")
    print(f"Precision  : {best_row['precision']:.4f}")
    print(f"Recall     : {best_row['recall']:.4f}")
    print(f"F1-score   : {best_row['f1']:.4f}")
    print(f"Specificity: {best_row['specificity']:.4f}")

    print("\nMatrice de confusion :")

    print(f"True Negative  : {int(best_row['true_negative'])}")

    print(f"False Positive : {int(best_row['false_positive'])}")

    print(f"False Negative : {int(best_row['false_negative'])}")

    print(f"True Positive  : {int(best_row['true_positive'])}")

    # --------------------------------------------------------
    # RÉSULTATS DU MODÈLE
    # --------------------------------------------------------

    summary = {
        "model": model_name,
        "default_threshold": 0.50,
        "default_f1": default_result["f1"],
        "default_precision": default_result["precision"],
        "default_recall": default_result["recall"],
        "best_threshold": best_threshold,
        "best_accuracy": best_row["accuracy"],
        "best_precision": best_row["precision"],
        "best_recall": best_row["recall"],
        "best_f1": best_row["f1"],
        "best_specificity": best_row["specificity"],
    }

    # Ajouter le nom du modèle aux résultats détaillés
    results_df.insert(0, "model", model_name)

    # Sauvegarder les probabilités Out-of-Fold
    oof_df = pd.DataFrame(
        {
            "model": model_name,
            "y_true": np.asarray(y_train),
            "probability_class_1": probabilities_class_1,
        }
    )

    return summary, results_df, oof_df


# ============================================================
# 6. EXÉCUTION PRINCIPALE
# ============================================================


def main():

    print("\n")
    print("=" * 60)
    print("SMARTCREDIT : THRESHOLD TUNING")
    print("=" * 60)

    X_train, y_train = prepare_data()

    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)

    models = get_optimized_models()

    all_summaries = []

    all_details = []

    all_oof_predictions = []

    for model_name, estimator in models.items():

        summary, details, oof_predictions = find_best_threshold(
            model_name=model_name,
            estimator=estimator,
            X_train=X_train,
            y_train=y_train,
            cv=cv,
        )

        all_summaries.append(summary)

        all_details.append(details)

        all_oof_predictions.append(oof_predictions)

    # --------------------------------------------------------
    # ENREGISTREMENT DES RÉSULTATS
    # --------------------------------------------------------

    summary_df = pd.DataFrame(all_summaries)

    details_df = pd.concat(all_details, ignore_index=True)

    oof_df = pd.concat(all_oof_predictions, ignore_index=True)

    summary_path = OUTPUT_DIR / "threshold_tuning_summary.csv"

    details_path = OUTPUT_DIR / "threshold_tuning_details.csv"

    oof_path = OUTPUT_DIR / "threshold_tuning_oof_predictions.csv"

    summary_df.to_csv(summary_path, index=False)

    details_df.to_csv(details_path, index=False)

    oof_df.to_csv(oof_path, index=False)

    # --------------------------------------------------------
    # RÉSUMÉ FINAL
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("RÉSUMÉ FINAL : THRESHOLD TUNING")
    print("=" * 60)

    print(
        summary_df[
            [
                "model",
                "default_threshold",
                "default_f1",
                "default_precision",
                "default_recall",
                "best_threshold",
                "best_precision",
                "best_recall",
                "best_f1",
            ]
        ].to_string(index=False)
    )

    print("\nFichiers enregistrés :")

    print(summary_path)

    print(details_path)

    print(oof_path)

    print("\nThreshold tuning terminé avec succès !")


# ============================================================
# 7. POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":

    main()
