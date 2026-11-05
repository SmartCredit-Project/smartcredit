from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.training.split_data import split_data

# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_PATH = Path("data/raw/credit_risk_dataset.csv")

MODEL_PATH = Path("models/gradient_boosting_final.joblib")

OUTPUT_DIR = Path("data/processed/shap")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42

# Nombre maximum de demandes utilisées pour les graphiques
MAX_SAMPLES = 1000


# ============================================================
# 2. CHARGEMENT DU MODÈLE
# ============================================================


def load_model():

    print("\nChargement du modèle final...")

    artifact = joblib.load(MODEL_PATH)

    pipeline = artifact["pipeline"]

    print(f"Modèle : {artifact['model_name']}")
    print(f"Seuil : {artifact['decision_threshold']}")

    return pipeline


# ============================================================
# 3. PRÉPARATION DES DONNÉES
# ============================================================


def prepare_data():

    print("\nChargement du dataset...")

    df = pd.read_csv(DATA_PATH)

    cleaned_df, cleaning_report = clean_dataset(df)

    X, y = split_features_target(cleaned_df)

    X_train, X_test, y_train, y_test = split_data(X, y)

    print(f"X_train : {X_train.shape}")
    print(f"X_test  : {X_test.shape}")

    return X_train, X_test, y_train, y_test


# ============================================================
# 4. TRANSFORMATION DES DONNÉES
# ============================================================


def transform_data(pipeline, X_test):

    print("\nTransformation des données...")

    preprocessor = pipeline.named_steps["preprocessor"]

    model = pipeline.named_steps["model"]

    # On applique uniquement le prétraitement déjà appris
    # pendant l'entraînement du modèle final.
    X_transformed = preprocessor.transform(X_test)

    # Conversion en tableau NumPy dense si nécessaire
    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()

    # Récupération des noms des variables après encodage
    feature_names = preprocessor.get_feature_names_out()

    X_transformed_df = pd.DataFrame(
        X_transformed,
        columns=feature_names,
        index=X_test.index,
    )

    print(f"Variables après transformation : {X_transformed_df.shape[1]}")

    return model, X_transformed_df


# ============================================================
# 5. CALCUL DES VALEURS SHAP
# ============================================================


def calculate_shap_values(model, X_transformed):

    print("\nCréation de l'explicateur SHAP...")

    explainer = shap.TreeExplainer(model)

    print("Calcul des valeurs SHAP...")

    shap_values = explainer.shap_values(X_transformed)

    # Selon la version de SHAP, les résultats peuvent être
    # retournés sous forme de liste ou de tableau NumPy.

    if isinstance(shap_values, list):

        # Pour la classification binaire, la classe 1
        # représente le défaut de remboursement.
        shap_values = shap_values[1]

    shap_values = np.asarray(shap_values)

    # Certaines versions retournent trois dimensions.
    if shap_values.ndim == 3:

        if shap_values.shape[1] == X_transformed.shape[1]:

            shap_values = shap_values[:, :, 1]

        else:

            shap_values = shap_values[1, :, :]

    if shap_values.ndim != 2:

        raise ValueError(f"Format SHAP inattendu : {shap_values.shape}")

    if shap_values.shape != X_transformed.shape:

        raise ValueError(
            "Les dimensions des valeurs SHAP et des variables " "ne correspondent pas."
        )

    print("Calcul SHAP terminé.")

    return explainer, shap_values


# ============================================================
# 6. ANALYSE GLOBALE : IMPORTANCE DES VARIABLES
# ============================================================


def global_analysis(shap_values, X_transformed):

    print("\nCréation des graphiques globaux...")

    # Graphique 1 : importance globale des variables
    plt.figure()

    shap.summary_plot(
        shap_values,
        X_transformed,
        plot_type="bar",
        show=False,
    )

    plt.title("Importance globale des variables - SmartCredit")

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "shap_global_importance.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    # Graphique 2 : distribution des influences SHAP
    plt.figure()

    shap.summary_plot(
        shap_values,
        X_transformed,
        show=False,
    )

    plt.title("Distribution des valeurs SHAP - SmartCredit")

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "shap_summary.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    # Calcul de l'importance moyenne absolue
    importance = np.abs(shap_values).mean(axis=0)

    importance_df = pd.DataFrame(
        {
            "Feature": X_transformed.columns,
            "Mean_Absolute_SHAP": importance,
        }
    )

    importance_df = importance_df.sort_values(
        by="Mean_Absolute_SHAP",
        ascending=False,
    )

    importance_df.to_csv(
        OUTPUT_DIR / "shap_feature_importance.csv",
        index=False,
    )

    print("\nImportance globale des variables :")

    print(importance_df.to_string(index=False))

    print("\nGraphiques globaux enregistrés.")


# ============================================================
# 7. ANALYSE INDIVIDUELLE : UN DEMANDEUR
# ============================================================


def individual_analysis(explainer, shap_values, X_transformed):

    print("\nAnalyse individuelle d'une demande...")

    # On prend la première demande du jeu de test
    sample_index = 0

    sample = X_transformed.iloc[[sample_index]]

    sample_shap_values = shap_values[sample_index]

    base_value = np.asarray(explainer.expected_value)

    if base_value.ndim > 0 and base_value.size > 1:
        base_value = base_value.reshape(-1)[1]
    else:
        base_value = base_value.reshape(-1)[0]

    explanation = shap.Explanation(
        values=sample_shap_values,
        base_values=base_value,
        data=sample.iloc[0].values,
        feature_names=sample.columns.tolist(),
    )

    plt.figure()

    shap.plots.waterfall(
        explanation,
        max_display=10,
        show=False,
    )

    plt.title("Explication individuelle - SmartCredit")

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "shap_individual_explanation.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close()

    print("Explication individuelle enregistrée.")


# ============================================================
# 8. POINT D'ENTRÉE DU PROGRAMME
# ============================================================


def main():

    print("=" * 60)
    print("ANALYSE SHAP - SMARTCREDIT")
    print("=" * 60)

    pipeline = load_model()

    X_train, X_test, y_train, y_test = prepare_data()

    # Limitation du nombre de demandes pour économiser
    # la mémoire et accélérer l'analyse.
    X_explain = X_test.sample(
        n=min(MAX_SAMPLES, len(X_test)),
        random_state=RANDOM_STATE,
    )

    model, X_transformed = transform_data(
        pipeline,
        X_explain,
    )

    explainer, shap_values = calculate_shap_values(
        model,
        X_transformed,
    )

    global_analysis(
        shap_values,
        X_transformed,
    )

    individual_analysis(
        explainer,
        shap_values,
        X_transformed,
    )

    print("\n" + "=" * 60)
    print("ANALYSE SHAP TERMINÉE")
    print("=" * 60)

    print(f"\nRésultats disponibles dans : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
