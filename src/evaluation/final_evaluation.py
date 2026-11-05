import time
from pathlib import Path

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.preprocessing.preprocessing import create_preprocessor
from src.training.split_data import split_data

# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_PATH = Path("data/raw/credit_risk_dataset.csv")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

# Seuils choisis précédemment avec les prédictions OOF
THRESHOLDS = {
    "Random Forest optimisé": 0.38,
    "Gradient Boosting équilibré optimisé": 0.59,
}


# ============================================================
# 2. CHARGEMENT ET PRÉPARATION DES DONNÉES
# ============================================================


def prepare_data():

    print("\n" + "=" * 60)
    print("PRÉPARATION DES DONNÉES SMARTCREDIT")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)

    cleaned_df, cleaning_report = clean_dataset(df)

    X, y = split_features_target(cleaned_df)

    X_train, X_test, y_train, y_test = split_data(X, y)

    print(f"\nDataset nettoyé : {cleaned_df.shape}")
    print(f"X_train : {X_train.shape}")
    print(f"X_test  : {X_test.shape}")
    print(f"y_train : {y_train.shape}")
    print(f"y_test  : {y_test.shape}")

    print("\nDistribution des classes dans y_test :")
    print(y_test.value_counts(normalize=True).sort_index())

    return X_train, X_test, y_train, y_test


# ============================================================
# 3. CRÉATION DES MODÈLES OPTIMISÉS
# ============================================================


def create_models():

    random_forest = RandomForestClassifier(
        n_estimators=150,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features=0.8,
        max_depth=None,
        class_weight=None,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )

    gradient_boosting = GradientBoostingClassifier(
        subsample=0.7,
        n_estimators=150,
        min_samples_leaf=2,
        max_depth=4,
        learning_rate=0.1,
        random_state=RANDOM_STATE,
    )

    models = {
        "Random Forest optimisé": random_forest,
        "Gradient Boosting équilibré optimisé": gradient_boosting,
    }

    return models


# ============================================================
# 4. ENTRAÎNEMENT ET ÉVALUATION
# ============================================================


def evaluate_models(X_train, X_test, y_train, y_test):

    models = create_models()

    results = []
    predictions_data = pd.DataFrame({"true_class": y_test.to_numpy()})

    for model_name, estimator in models.items():

        print("\n" + "=" * 60)
        print(f"ÉVALUATION : {model_name}")
        print("=" * 60)

        pipeline = Pipeline(
            steps=[
                ("preprocessor", create_preprocessor()),
                ("model", estimator),
            ]
        )

        # ----------------------------------------------------
        # Entraînement
        # ----------------------------------------------------

        start_train = time.perf_counter()

        if model_name == "Gradient Boosting équilibré optimisé":

            # Calcule le poids de chaque observation
            # pour compenser le déséquilibre des classes.
            sample_weights = compute_sample_weight(
                class_weight="balanced",
                y=y_train,
            )

            pipeline.fit(
                X_train,
                y_train,
                model__sample_weight=sample_weights,
            )

        else:
            pipeline.fit(X_train, y_train)

        train_time = time.perf_counter() - start_train

        # ----------------------------------------------------
        # Prédiction des probabilités
        # ----------------------------------------------------

        start_inference = time.perf_counter()

        probabilities = pipeline.predict_proba(X_test)[:, 1]

        inference_time = time.perf_counter() - start_inference

        # ----------------------------------------------------
        # Application du seuil choisi
        # ----------------------------------------------------

        threshold = THRESHOLDS[model_name]

        y_pred = (probabilities >= threshold).astype(int)

        # ----------------------------------------------------
        # Calcul des métriques
        # ----------------------------------------------------

        accuracy = accuracy_score(y_test, y_pred)

        precision = precision_score(
            y_test,
            y_pred,
            zero_division=0,
        )

        recall = recall_score(
            y_test,
            y_pred,
            zero_division=0,
        )

        f1 = f1_score(
            y_test,
            y_pred,
            zero_division=0,
        )

        # Ces deux métriques utilisent les probabilités,
        # et non les classes prédites après application du seuil.
        roc_auc = roc_auc_score(y_test, probabilities)

        pr_auc = average_precision_score(y_test, probabilities)

        # ----------------------------------------------------
        # Matrice de confusion
        # ----------------------------------------------------

        tn, fp, fn, tp = confusion_matrix(
            y_test,
            y_pred,
            labels=[0, 1],
        ).ravel()

        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0

        # ----------------------------------------------------
        # Affichage des résultats
        # ----------------------------------------------------

        print(f"\nSeuil utilisé : {threshold}")

        print(f"\nAccuracy  : {accuracy:.4f}")
        print(f"Precision : {precision:.4f}")
        print(f"Recall    : {recall:.4f}")
        print(f"F1-score  : {f1:.4f}")
        print(f"ROC-AUC   : {roc_auc:.4f}")
        print(f"PR-AUC    : {pr_auc:.4f}")
        print(f"Specificity : {specificity:.4f}")

        print(f"\nTemps d'entraînement : {train_time:.4f} secondes")
        print(f"Temps de prédiction  : {inference_time:.4f} secondes")

        print("\nMatrice de confusion :")
        print(
            pd.DataFrame(
                [[tn, fp], [fn, tp]],
                index=["Réel 0", "Réel 1"],
                columns=["Prédit 0", "Prédit 1"],
            )
        )

        print("\nRapport de classification :")
        print(
            classification_report(
                y_test,
                y_pred,
                zero_division=0,
            )
        )

        # ----------------------------------------------------
        # Enregistrement des résultats
        # ----------------------------------------------------

        results.append(
            {
                "Model": model_name,
                "Threshold": threshold,
                "Accuracy": accuracy,
                "Precision": precision,
                "Recall": recall,
                "F1": f1,
                "ROC_AUC": roc_auc,
                "PR_AUC": pr_auc,
                "Specificity": specificity,
                "TN": tn,
                "FP": fp,
                "FN": fn,
                "TP": tp,
                "Train_Time_s": train_time,
                "Inference_Time_s": inference_time,
            }
        )

        predictions_data[f"{model_name}_probability"] = probabilities
        predictions_data[f"{model_name}_prediction"] = y_pred

    # ========================================================
    # 5. SAUVEGARDE DES RÉSULTATS
    # ========================================================

    results_df = pd.DataFrame(results)

    results_path = OUTPUT_DIR / "final_test_evaluation.csv"

    predictions_path = OUTPUT_DIR / "final_test_predictions.csv"

    results_df.to_csv(results_path, index=False)

    predictions_data.to_csv(predictions_path, index=False)

    print("\n" + "=" * 60)
    print("COMPARAISON FINALE SUR LE JEU DE TEST")
    print("=" * 60)

    print(
        results_df[
            [
                "Model",
                "Accuracy",
                "Precision",
                "Recall",
                "F1",
                "ROC_AUC",
                "PR_AUC",
            ]
        ].to_string(index=False)
    )

    print(f"\nRésultats sauvegardés : {results_path}")
    print(f"Prédictions sauvegardées : {predictions_path}")


# ============================================================
# 6. POINT D'ENTRÉE DU PROGRAMME
# ============================================================


def main():

    X_train, X_test, y_train, y_test = prepare_data()

    evaluate_models(
        X_train,
        X_test,
        y_train,
        y_test,
    )


if __name__ == "__main__":
    main()
