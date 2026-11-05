from src.preprocessing.preprocessing import FEATURE_COLUMNS, TARGET_COLUMN


def split_features_target(df):
    """
    Sépare les caractéristiques (X) de la variable cible (y).
    """

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Colonnes manquantes dans le dataset : {missing_columns}")

    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    return X, y
