
from pathlib import Path
import time
import joblib
import pandas as pd

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_sample_weight

from src.preprocessing.cleaning import clean_dataset
from src.features.feature_selection import split_features_target
from src.preprocessing.preprocessing import create_preprocessor
from src.training.split_data import split_data


# ============================================================
# 1. CONFIGURATION
# ============================================================

DATA_PATH = Path("data/raw/credit_risk_dataset.csv")
MODEL_DIR = Path("models")

MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "gradient_boosting_final.joblib"

RANDOM_STATE = 42

# Seuil sélectionné précédemment avec les données d'entraînement
DECISION_THRESHOLD = 0.59


# ============================================================
# 2. CHARGEMENT ET PRÉPARATION DES DONNÉES
# ============================================================

def prepare_training_data():

    print("\nChargement du dataset...")

    df = pd.read_csv(DATA_PATH)

    print("Nettoyage des données...")

    cleaned_df, cleaning_report = clean_dataset(df)

    print("Séparation des variables...")

    X, y = split_features_target(cleaned_df)

    print("Séparation entraînement/test...")

    X_train, X_test, y_train, y_test = split_data(X, y)

    print(f"\nNombre de lignes d'entraînement : {len(X_train)}")
    print(f"Nombre de variables : {X_train.shape[1]}")

    return X_train, y_train


# ============================================================
# 3. CRÉATION DU PIPELINE FINAL
# ============================================================

def create_final_pipeline():

    model = GradientBoostingClassifier(
        subsample=0.7,
        n_estimators=150,
        min_samples_leaf=2,
        max_depth=4,
        learning_rate=0.1,
        random_state=RANDOM_STATE,
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", create_preprocessor()),
        ("model", model),
    ])

    return pipeline


# ============================================================
# 4. ENTRAÎNEMENT DU MODÈLE
# ============================================================

def train_final_model(X_train, y_train):

    print("\nCréation du pipeline final...")

    pipeline = create_final_pipeline()

    print("Calcul des poids des classes...")

    sample_weights = compute_sample_weight(
        class_weight="balanced",
        y=y_train,
    )

    print("\nEntraînement du Gradient Boosting...")

    start_time = time.perf_counter()

    pipeline.fit(
        X_train,
        y_train,
        model__sample_weight=sample_weights,
    )

    training_time = time.perf_counter() - start_time

    print(f"\nEntraînement terminé en {training_time:.2f} secondes.")

    return pipeline


# ============================================================
# 5. CONSTRUCTION DE L'ARTIFACT
# ============================================================

def create_model_artifact(pipeline, X_train):

    artifact = {
        "model_name": "Gradient Boosting équilibré optimisé",
        "pipeline": pipeline,
        "decision_threshold": DECISION_THRESHOLD,
        "features": list(X_train.columns),
        "target": "loan_status",
        "class_mapping": {
            0: "Pas de défaut enregistré",
            1: "Défaut de remboursement enregistré",
        },
        "parameters": {
            "subsample": 0.7,
            "n_estimators": 150,
            "min_samples_leaf": 2,
            "max_depth": 4,
            "learning_rate": 0.1,
            "random_state": RANDOM_STATE,
            "class_weight": "balanced via sample_weight",
        },
    }

    return artifact


# ============================================================
# 6. SAUVEGARDE AVEC JOBLIB
# ============================================================

def save_model(artifact):

    print("\nSauvegarde du modèle...")

    joblib.dump(artifact, MODEL_PATH)

    print("\nModèle sauvegardé avec succès !")
    print(f"Chemin : {MODEL_PATH}")

    print(f"Taille : {MODEL_PATH.stat().st_size / 1024:.2f} Ko")


# ============================================================
# 7. VÉRIFICATION DU FICHIER SAUVEGARDÉ
# ============================================================

def verify_saved_model():

    print("\nVérification du modèle sauvegardé...")

    loaded_artifact = joblib.load(MODEL_PATH)

    print(f"Nom du modèle : {loaded_artifact['model_name']}")
    print(f"Seuil : {loaded_artifact['decision_threshold']}")
    print(f"Variables : {loaded_artifact['features']}")

    print("\nLe modèle peut être chargé correctement.")


# ============================================================
# 8. POINT D'ENTRÉE DU PROGRAMME
# ============================================================

def main():

    X_train, y_train = prepare_training_data()

    pipeline = train_final_model(X_train, y_train)

    artifact = create_model_artifact(pipeline, X_train)

    save_model(artifact)

    verify_saved_model()


if __name__ == "__main__":
    main()
