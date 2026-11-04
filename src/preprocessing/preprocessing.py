from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# -------------------------------------------------
# 1. Définition des variables utilisées par le modèle
# -------------------------------------------------

NUMERIC_FEATURES = [
    "person_age",
    "person_income",
    "person_emp_length",
    "loan_amnt",
    "loan_percent_income",
]

CATEGORICAL_FEATURES = [
    "person_home_ownership",
    "loan_intent",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

TARGET_COLUMN = "loan_status"


# -------------------------------------------------
# 2. Pipeline de traitement des données numériques
# -------------------------------------------------

def create_numeric_pipeline():

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median")
            ),
            (
                "scaler",
                StandardScaler()
            ),
        ]
    )

    return numeric_pipeline


# -------------------------------------------------
# 3. Pipeline de traitement des données catégorielles
# -------------------------------------------------

def create_categorical_pipeline():

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent")
            ),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore")
            ),
        ]
    )

    return categorical_pipeline


# -------------------------------------------------
# 4. Combinaison des deux pipelines
# -------------------------------------------------

def create_preprocessor():

    numeric_pipeline = create_numeric_pipeline()

    categorical_pipeline = create_categorical_pipeline()

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES
            ),
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES
            ),
        ],
        remainder="drop"
    )

    return preprocessor