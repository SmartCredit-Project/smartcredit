from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from src.analysis.visualizations import generate_all_visualizations
from src.data.load_data import load_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

FIGURES_DIR = PROCESSED_DIR / "figures"


def analyze_dataset(df):
    """Effectue les principales analyses exploratoires."""

    report = []

    report.append("=" * 70)
    report.append("SMARTCREDIT - EXPLORATORY DATA ANALYSIS")
    report.append("=" * 70)

    # 1. Dimensions
    report.append("\n1. DIMENSIONS DU DATASET")
    report.append(f"Nombre de lignes : {df.shape[0]}")
    report.append(f"Nombre de colonnes : {df.shape[1]}")

    # 2. Aperçu
    report.append("\n2. APERÇU DU DATASET")
    report.append(str(df.head()))

    # 3. Types des variables
    report.append("\n3. TYPES DES VARIABLES")
    report.append(str(df.dtypes))

    # 4. Informations générales
    report.append("\n4. INFORMATIONS GÉNÉRALES")

    info_buffer = StringIO()

    with redirect_stdout(info_buffer):
        df.info()

    report.append(info_buffer.getvalue())

    # 5. Valeurs manquantes
    report.append("\n5. VALEURS MANQUANTES")

    missing_values = df.isnull().sum()

    report.append(str(missing_values))

    report.append(f"\nTotal des valeurs manquantes : {df.isnull().sum().sum()}")

    # 6. Doublons
    report.append("\n6. DOUBLONS")

    duplicates = df.duplicated().sum()

    report.append(f"Nombre de doublons : {duplicates}")

    # 7. Statistiques descriptives
    report.append("\n7. STATISTIQUES DESCRIPTIVES")

    report.append(str(df.describe().T))

    # 8. Variables catégorielles
    report.append("\n8. VARIABLES CATÉGORIELLES")

    categorical_columns = df.select_dtypes(include=["object", "category"]).columns

    for column in categorical_columns:

        report.append(f"\nVariable : {column}")

        report.append(str(df[column].value_counts(dropna=False)))

    # 9. Variable cible
    report.append("\n9. DISTRIBUTION DE LA VARIABLE CIBLE")

    if "loan_status" in df.columns:

        target_counts = df["loan_status"].value_counts(dropna=False)

        target_percentages = (
            df["loan_status"].value_counts(normalize=True, dropna=False) * 100
        )

        report.append("Effectifs :")
        report.append(str(target_counts))

        report.append("\nPourcentages :")
        report.append(str(target_percentages.round(2)))

    else:
        report.append("ERREUR : loan_status est absent du dataset.")

    return "\n".join(report)


def main():

    print("\nDÉMARRAGE DE L'ANALYSE EXPLORATOIRE SMARTCREDIT")

    # Création des dossiers
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Chargement
    df = load_dataset()

    # Vérification de la variable cible
    if "loan_status" not in df.columns:
        raise ValueError("La variable cible loan_status est absente.")

    # Analyse
    report = analyze_dataset(df)

    # Sauvegarde du rapport
    report_path = PROCESSED_DIR / "eda_report.txt"

    report_path.write_text(report, encoding="utf-8")

    print("\nRapport enregistré :", report_path)

    # Visualisations
    generate_all_visualizations(df, FIGURES_DIR)

    print("\nANALYSE EXPLORATOIRE TERMINÉE.")
    print("Consulte data/processed/ pour les résultats.")


if __name__ == "__main__":
    main()
