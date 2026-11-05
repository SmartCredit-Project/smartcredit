import time
from pathlib import Path

import joblib

from src.data.load_data import load_dataset
from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.training.model_pipeline import create_logistic_regression_pipeline
from src.training.split_data import split_data

# Chemin racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dossier de sauvegarde des modèles
MODELS_DIR = PROJECT_ROOT / "models"

# Fichier du modèle entraîné
MODEL_PATH = MODELS_DIR / "logistic_regression.joblib"


def train_model():
    """
    Charge les données, prépare les caractéristiques,
    entraîne la régression logistique et sauvegarde le modèle.
    """

    print("\n========== SMARTCREDIT : MODEL TRAINING ==========")

    # 1. Charger les données
    df = load_dataset()

    # 2. Nettoyer les données
    cleaned_df, report = clean_dataset(df)

    # 3. Séparer X et y
    X, y = split_features_target(cleaned_df)

    # 4. Séparer les données d'entraînement et de test
    X_train, X_test, y_train, y_test = split_data(X, y)

    print("\nDimensions d'entraînement :", X_train.shape)
    print("Dimensions de test :", X_test.shape)

    # 5. Construire le pipeline
    model = create_logistic_regression_pipeline()

    # 6. Entraîner le modèle
    print("\nEntraînement de Logistic Regression...")

    start_time = time.perf_counter()

    model.fit(X_train, y_train)

    training_time = time.perf_counter() - start_time

    print("Entraînement terminé !")
    print(f"Temps d'entraînement : {training_time:.4f} secondes")

    # 7. Évaluer rapidement le modèle sur le jeu de test
    accuracy = model.score(X_test, y_test)

    print(f"Accuracy sur les données de test : {accuracy:.4f}")

    # 8. Créer le dossier models s'il n'existe pas
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # 9. Sauvegarder le modèle complet
    joblib.dump(model, MODEL_PATH)

    print("\nModèle sauvegardé avec succès !")
    print(f"Emplacement : {MODEL_PATH}")

    print("\n========== TRAINING TERMINÉ ==========")

    return model


if __name__ == "__main__":
    train_model()
