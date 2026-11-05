from pathlib import Path

import pandas as pd

# Chemin racine du projet SmartCredit
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Emplacement du dataset original
DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "credit_risk_dataset.csv"


def load_dataset(file_path=DATASET_PATH):
    """
    Charge le dataset CSV et retourne un DataFrame Pandas.

    Args:
        file_path: chemin vers le fichier CSV.

    Returns:
        pandas.DataFrame: données chargées.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset introuvable : {file_path}")

    if file_path.suffix.lower() != ".csv":
        raise ValueError("Le fichier doit être au format CSV.")

    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError("Le dataset est vide.")

    print("=" * 60)
    print("CHARGEMENT DU DATASET SMARTCREDIT")
    print("=" * 60)

    print(f"Fichier : {file_path}")
    print(f"Nombre de lignes : {df.shape[0]}")
    print(f"Nombre de colonnes : {df.shape[1]}")

    return df


if __name__ == "__main__":
    dataset = load_dataset()

    print("\nAperçu des données :")
    print(dataset.head())
