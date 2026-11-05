from functools import lru_cache

import joblib
import pandas as pd

from django.conf import settings
from django.db import transaction

from ..models import ModelVersion, Prediction


# ============================================================
# 1. CONFIGURATION
# ============================================================

MODEL_PATH = settings.MODEL_PATH

MODEL_VERSION = "1.0.0"

REQUIRED_FEATURES = [
    "person_age",
    "person_income",
    "person_home_ownership",
    "person_emp_length",
    "loan_intent",
    "loan_amnt",
]


# ============================================================
# 2. CHARGEMENT DU MODELE
# ============================================================

@lru_cache(maxsize=1)
def load_model():
    """Charge le modèle une seule fois puis le conserve en cache."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modèle introuvable : {MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    pipeline = artifact["pipeline"]
    threshold = artifact["decision_threshold"]
    features = artifact["features"]

    return artifact, pipeline, threshold, features


# ============================================================
# 3. INFORMATIONS SUR LE MODELE
# ============================================================

def get_model_info():
    artifact, pipeline, threshold, features = load_model()

    return {
        "model_name": artifact["model_name"],
        "model_version": MODEL_VERSION,
        "decision_threshold": threshold,
        "features": features,
        "target": artifact["target"],
        "class_mapping": artifact["class_mapping"],
        "parameters": artifact["parameters"],
        "risk_thresholds": settings.RISK_THRESHOLDS,
    }


def get_model_health():
    artifact, pipeline, threshold, features = load_model()

    return {
        "status": "healthy",
        "model_loaded": pipeline is not None,
        "model_name": artifact["model_name"],
        "model_version": MODEL_VERSION,
    }


def get_algorithm_name(pipeline):
    model = pipeline.named_steps.get("model")

    if model is None:
        return ""

    return model.__class__.__name__


def get_active_model_version():
    """Récupère ou crée la version active du modèle."""

    artifact, pipeline, threshold, features = load_model()

    metrics = artifact.get("metrics", {})

    defaults = {
        "algorithm": get_algorithm_name(pipeline),
        "accuracy": metrics.get("accuracy"),
        "precision": metrics.get("precision"),
        "recall": metrics.get("recall"),
        "roc_auc": metrics.get("roc_auc"),
        "is_active": True,
    }

    with transaction.atomic():
        model_version, created = (
            ModelVersion.objects.get_or_create(
                name=artifact["model_name"],
                version=MODEL_VERSION,
                defaults=defaults,
            )
        )

        if created or not model_version.is_active:
            ModelVersion.objects.exclude(
                pk=model_version.pk
            ).update(is_active=False)

            if not model_version.is_active:
                model_version.is_active = True
                model_version.save(
                    update_fields=["is_active"]
                )

        if not created and metrics:
            updated_fields = []

            for field in [
                "accuracy",
                "precision",
                "recall",
                "roc_auc",
            ]:
                value = metrics.get(field)

                if (
                    value is not None
                    and getattr(model_version, field) is None
                ):
                    setattr(model_version, field, value)
                    updated_fields.append(field)

            if updated_fields:
                model_version.save(
                    update_fields=updated_fields
                )

    return model_version


# ============================================================
# 4. NIVEAU DE RISQUE
# ============================================================

def get_risk_level(default_probability):
    medium_threshold = settings.RISK_THRESHOLDS["MEDIUM"]
    high_threshold = settings.RISK_THRESHOLDS["HIGH"]

    if default_probability < medium_threshold:
        return Prediction.RiskLevel.LOW

    if default_probability < high_threshold:
        return Prediction.RiskLevel.MEDIUM

    return Prediction.RiskLevel.HIGH


def get_risk_message(risk_level):
    messages = {
        Prediction.RiskLevel.LOW: (
            "Risque faible de défaut de remboursement."
        ),
        Prediction.RiskLevel.MEDIUM: (
            "Risque modéré de défaut de remboursement."
        ),
        Prediction.RiskLevel.HIGH: (
            "Risque élevé de défaut de remboursement."
        ),
    }

    return messages.get(
        risk_level,
        "Risque non déterminé.",
    )


# ============================================================
# 5. PREPARATION DES DONNEES
# ============================================================

def prepare_input_data(application_data):
    """Construit le DataFrame attendu par le pipeline final."""

    missing = [
        feature
        for feature in REQUIRED_FEATURES
        if feature not in application_data
    ]

    if missing:
        raise ValueError(
            "Caractéristiques manquantes pour la prédiction : "
            f"{missing}"
        )

    loan_percent_income = (
        application_data["loan_amnt"]
        / application_data["person_income"]
    )

    input_data = pd.DataFrame([{
        "person_age": application_data["person_age"],
        "person_income": application_data["person_income"],
        "person_home_ownership": (
            application_data["person_home_ownership"]
        ),
        "person_emp_length": (
            application_data["person_emp_length"]
        ),
        "loan_intent": application_data["loan_intent"],
        "loan_amnt": application_data["loan_amnt"],
        "loan_percent_income": loan_percent_income,
    }])

    return input_data, loan_percent_income


# ============================================================
# 6. PREDICTION
# ============================================================

def predict_credit(application_data):
    """Exécute le modèle et retourne le résultat interprété."""

    (
        artifact,
        pipeline,
        threshold,
        model_features,
    ) = load_model()

    input_data, loan_percent_income = prepare_input_data(
        application_data
    )

    input_data = input_data[model_features]

    probabilities = pipeline.predict_proba(input_data)[0]

    class_index = list(pipeline.classes_).index(1)

    default_probability = float(probabilities[class_index])

    predicted_class = int(
        default_probability >= threshold
    )

    risk_level = get_risk_level(default_probability)

    return {
        "model_name": artifact["model_name"],
        "prediction": predicted_class,
        "predicted_class": predicted_class,
        "default_probability": round(
            default_probability,
            6,
        ),
        "no_default_probability": round(
            1 - default_probability,
            6,
        ),
        "risk_level": risk_level,
        "message": get_risk_message(risk_level),
        "decision_threshold": threshold,
        "loan_percent_income": round(
            loan_percent_income,
            6,
        ),
        "features": {
            "person_age": application_data["person_age"],
            "person_income": application_data["person_income"],
            "person_home_ownership": (
                application_data["person_home_ownership"]
            ),
            "person_emp_length": (
                application_data["person_emp_length"]
            ),
            "loan_intent": application_data["loan_intent"],
            "loan_amnt": application_data["loan_amnt"],
            "loan_percent_income": round(
                loan_percent_income,
                6,
            ),
        },
        "disclaimer": (
            "Cette prédiction est une estimation statistique. "
            "Elle ne constitue pas une décision automatique "
            "d'acceptation ou de refus du crédit."
        ),
    }


def predict_and_save(
    application_data,
    credit_application=None,
    created_by=None,
    institution=None,
):
    """Exécute la prédiction et enregistre l'historique."""

    result = predict_credit(application_data)

    model_version = get_active_model_version()

    if institution is None:
        if credit_application is not None:
            institution = credit_application.institution

        elif created_by is not None:
            institution = getattr(created_by, "institution", None)

    prediction = Prediction.objects.create(
        credit_application=credit_application,
        institution=institution,
        predicted_class=result["predicted_class"],
        default_probability=result["default_probability"],
        no_default_probability=(
            result["no_default_probability"]
        ),
        risk_level=result["risk_level"],
        model_version=model_version,
        features=result["features"],
        created_by=created_by,
    )

    if credit_application is not None and (
        credit_application.status
        in [
            credit_application.Status.PENDING,
            credit_application.Status.IN_ANALYSIS,
        ]
    ):
        credit_application.status = (
            credit_application.Status.ANALYZED
        )
        credit_application.save(
            update_fields=["status", "updated_at"]
        )

    return prediction, result
