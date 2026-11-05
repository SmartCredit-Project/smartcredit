from pathlib import Path

from src.data.load_data import load_dataset

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Dossier de sauvegarde
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Fichier de sortie
CLEANED_DATA_PATH = PROCESSED_DIR / "credit_risk_cleaned.csv"


def clean_dataset(df):
    """
    Nettoie le dataset SmartCredit.

    Opérations :
    - Suppression des doublons exacts.
    - Suppression des âges invalides.
    - Correction des anciennetés professionnelles incohérentes.
    - Recalcul du ratio montant du crédit / revenu annuel.
    """

    df = df.copy()

    report = {}

    # -------------------------------------------------
    # 1. Vérification des colonnes indispensables
    # -------------------------------------------------

    required_columns = [
        "person_age",
        "person_income",
        "person_emp_length",
        "loan_amnt",
        "loan_status",
    ]

    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(f"Colonnes indispensables absentes : {missing_columns}")

    # -------------------------------------------------
    # 2. Vérification de la variable cible
    # -------------------------------------------------

    if df["loan_status"].isnull().any():
        raise ValueError(
            "La variable cible loan_status contient des valeurs manquantes."
        )

    if not df["loan_status"].isin([0, 1]).all():
        raise ValueError("loan_status doit contenir uniquement 0 ou 1.")

    # -------------------------------------------------
    # 3. Suppression des doublons exacts
    # -------------------------------------------------

    initial_rows = len(df)

    df = df.drop_duplicates().copy()

    report["duplicates_removed"] = initial_rows - len(df)

    # -------------------------------------------------
    # 4. Traitement des âges invalides
    # -------------------------------------------------

    invalid_age = (df["person_age"] < 18) | (df["person_age"] > 100)

    report["invalid_ages_removed"] = int(invalid_age.sum())

    df = df.loc[~invalid_age].copy()

    # -------------------------------------------------
    # 5. Traitement de l'ancienneté professionnelle
    # -------------------------------------------------

    invalid_employment = (df["person_emp_length"] < 0) | (
        df["person_emp_length"] > (df["person_age"] - 14)
    )

    report["invalid_employment_lengths"] = int(invalid_employment.sum())

    # Nous remplaçons les valeurs incohérentes par NaN.
    # L'imputation sera réalisée plus tard dans le pipeline.
    df.loc[invalid_employment, "person_emp_length"] = float("nan")

    # -------------------------------------------------
    # 6. Vérification des revenus et montants
    # -------------------------------------------------

    invalid_income = df["person_income"] <= 0

    invalid_loan_amount = df["loan_amnt"] <= 0

    report["invalid_income_rows"] = int(invalid_income.sum())

    report["invalid_loan_amount_rows"] = int(invalid_loan_amount.sum())

    if invalid_income.any() or invalid_loan_amount.any():
        raise ValueError(
            "Des revenus ou montants de crédit non positifs "
            "ont été détectés. Ils nécessitent une inspection."
        )

    # -------------------------------------------------
    # 7. Recalcul du ratio montant / revenu
    # -------------------------------------------------

    df["loan_percent_income"] = df["loan_amnt"] / df["person_income"]

    # -------------------------------------------------
    # 8. Rapport de nettoyage
    # -------------------------------------------------

    report["initial_rows"] = initial_rows
    report["final_rows"] = len(df)
    report["rows_removed"] = initial_rows - len(df)

    report["remaining_missing_values"] = df.isnull().sum().to_dict()

    report["target_distribution"] = df["loan_status"].value_counts().to_dict()

    return df, report


def save_cleaned_dataset(df, report):
    """Enregistre les données nettoyées et le rapport."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Sauvegarde du dataset nettoyé
    df.to_csv(CLEANED_DATA_PATH, index=False)

    # Sauvegarde du rapport
    report_path = PROCESSED_DIR / "cleaning_report.txt"

    with open(report_path, "w", encoding="utf-8") as file:

        file.write("SMARTCREDIT - CLEANING REPORT\n")
        file.write("=" * 60 + "\n\n")

        for key, value in report.items():

            file.write(f"{key}:\n")
            file.write(f"{value}\n\n")

    print("\nDATASET NETTOYÉ AVEC SUCCÈS")

    print(f"Fichier : {CLEANED_DATA_PATH}")

    print(f"Rapport : {report_path}")

    print(f"Lignes initiales : {report['initial_rows']}")

    print(f"Lignes finales : {report['final_rows']}")

    print(f"Doublons supprimés : {report['duplicates_removed']}")

    print("Âges invalides supprimés : " f"{report['invalid_ages_removed']}")

    print(
        "Anciennetés incohérentes transformées en valeurs manquantes : "
        f"{report['invalid_employment_lengths']}"
    )


def main():

    print("\nSMARTCREDIT - DATA CLEANING")

    # Charger les données originales
    df = load_dataset()

    # Nettoyer
    cleaned_df, report = clean_dataset(df)

    # Sauvegarder
    save_cleaned_dataset(cleaned_df, report)


if __name__ == "__main__":
    main()
