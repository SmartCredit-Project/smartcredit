from pathlib import Path
from typing import Literal

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# ============================================================
# 1. CONFIGURATION
# ============================================================

# Racine du projet SmartCredit
BASE_DIR = Path(__file__).resolve().parent.parent

# Emplacement du modèle sauvegardé
MODEL_PATH = BASE_DIR / "models" / "gradient_boosting_final.joblib"


# ============================================================
# 2. CHARGEMENT DU MODÈLE
# ============================================================

def load_model():

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modèle introuvable : {MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    pipeline = artifact["pipeline"]

    threshold = artifact["decision_threshold"]

    features = artifact["features"]

    return artifact, pipeline, threshold, features


artifact, pipeline, threshold, model_features = load_model()


# ============================================================
# 3. CRÉATION DE L'APPLICATION FASTAPI
# ============================================================

app = FastAPI(
    title="SmartCredit API",
    description=(
        "API d'analyse des demandes de crédit "
        "et de prédiction du risque de défaut."
    ),
    version="1.0.0",
)


# ============================================================
# 4. MODÈLE DE DONNÉES REÇUES
# ============================================================

class CreditApplication(BaseModel):

    person_age: int = Field(
        gt=0,
        description="Âge du demandeur",
        examples=[25],
    )

    person_income: float = Field(
        gt=0,
        description="Revenu annuel du demandeur",
        examples=[12000],
    )

    person_home_ownership: Literal[
        "RENT",
        "OWN",
        "MORTGAGE",
        "OTHER",
    ] = Field(
        description="Type de logement",
        examples=["RENT"],
    )

    person_emp_length: float | None = Field(
        default=None,
        ge=0,
        description="Ancienneté professionnelle en années",
        examples=[3],
    )

    loan_intent: Literal[
        "PERSONAL",
        "EDUCATION",
        "MEDICAL",
        "VENTURE",
        "HOMEIMPROVEMENT",
        "DEBTCONSOLIDATION",
    ] = Field(
        description="Objectif du crédit",
        examples=["PERSONAL"],
    )

    loan_amnt: float = Field(
        gt=0,
        description="Montant du crédit demandé",
        examples=[3000],
    )


# ============================================================
# 5. ENDPOINT D'ACCUEIL
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Bienvenue dans SmartCredit API",
        "version": "1.0.0",
        "documentation": "/docs",
    }


# ============================================================
# 6. ENDPOINT DE VÉRIFICATION
# ============================================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "model_loaded": pipeline is not None,
        "model_name": artifact["model_name"],
    }


# ============================================================
# 7. INFORMATIONS SUR LE MODÈLE
# ============================================================

@app.get("/model-info")
def model_info():

    return {
        "model_name": artifact["model_name"],
        "decision_threshold": threshold,
        "features": model_features,
        "target": artifact["target"],
        "class_mapping": artifact["class_mapping"],
        "parameters": artifact["parameters"],
    }


# ============================================================
# 8. ENDPOINT DE PRÉDICTION
# ============================================================

@app.post("/predict")
def predict_credit(application: CreditApplication):

    try:

        # ----------------------------------------------------
        # A. Calcul du rapport crédit / revenu
        # ----------------------------------------------------

        loan_percent_income = (
            application.loan_amnt / application.person_income
        )

        # ----------------------------------------------------
        # B. Construction des données d'entrée
        # ----------------------------------------------------

        input_data = pd.DataFrame([{
            "person_age": application.person_age,
            "person_income": application.person_income,
            "person_home_ownership": application.person_home_ownership,
            "person_emp_length": application.person_emp_length,
            "loan_intent": application.loan_intent,
            "loan_amnt": application.loan_amnt,
            "loan_percent_income": loan_percent_income,
        }])

        # Respect de l'ordre des variables utilisé à l'entraînement
        input_data = input_data[model_features]

        # ----------------------------------------------------
        # C. Calcul de la probabilité
        # ----------------------------------------------------

        probabilities = pipeline.predict_proba(input_data)[0]

        class_index = list(pipeline.classes_).index(1)

        default_probability = float(probabilities[class_index])

        # ----------------------------------------------------
        # D. Application du seuil de décision
        # ----------------------------------------------------

        prediction = int(default_probability >= threshold)

        # ----------------------------------------------------
        # E. Interprétation du résultat
        # ----------------------------------------------------

        if prediction == 1:

            result = "DEFAULT_RISK_DETECTED"

            message = (
                "Le modèle détecte un risque de défaut "
                "de remboursement."
            )

        else:

            result = "NO_DEFAULT_RISK_DETECTED"

            message = (
                "Le modèle ne détecte pas de risque de défaut "
                "selon le seuil configuré."
            )

        # ----------------------------------------------------
        # F. Réponse JSON
        # ----------------------------------------------------

        return {
            "model": artifact["model_name"],
            "prediction": prediction,
            "result": result,
            "message": message,
            "default_probability": round(default_probability, 4),
            "default_probability_percentage": round(
                default_probability * 100,
                2,
            ),
            "decision_threshold": threshold,
            "loan_percent_income": round(
                loan_percent_income,
                4,
            ),
            "disclaimer": (
                "Cette prédiction est une estimation statistique. "
                "Elle ne constitue pas une décision automatique "
                "d'acceptation ou de refus du crédit."
            ),
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Erreur pendant la prédiction : {str(error)}",
        )
