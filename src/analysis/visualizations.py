from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns


def create_output_directory(output_dir):
    """Crée le dossier de destination des graphiques."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def plot_target_distribution(df, output_dir):
    """Visualise la distribution de la variable cible loan_status."""

    output_dir = create_output_directory(output_dir)

    plt.figure(figsize=(8, 5))

    sns.countplot(data=df, x="loan_status")

    plt.title("Distribution des statuts de remboursement")
    plt.xlabel("Statut (0 = pas de défaut, 1 = défaut)")
    plt.ylabel("Nombre de demandes")

    plt.tight_layout()

    plt.savefig(output_dir / "target_distribution.png")
    plt.close()


def plot_numeric_distributions(df, output_dir):
    """Visualise les distributions des principales variables numériques."""

    output_dir = create_output_directory(output_dir)

    columns = [
        "person_age",
        "person_income",
        "loan_amnt",
        "loan_int_rate",
        "loan_percent_income",
    ]

    for column in columns:

        if column not in df.columns:
            continue

        plt.figure(figsize=(8, 5))

        sns.histplot(data=df, x=column, kde=True)

        plt.title(f"Distribution de {column}")
        plt.xlabel(column)
        plt.ylabel("Fréquence")

        plt.tight_layout()

        plt.savefig(output_dir / f"{column}_distribution.png")
        plt.close()


def plot_loan_amount_by_status(df, output_dir):
    """Compare les montants de crédit selon le statut de remboursement."""

    output_dir = create_output_directory(output_dir)

    plt.figure(figsize=(8, 5))

    sns.boxplot(data=df, x="loan_status", y="loan_amnt")

    plt.title("Montant du crédit selon le statut")
    plt.xlabel("Statut (0 = pas de défaut, 1 = défaut)")
    plt.ylabel("Montant du crédit")

    plt.tight_layout()

    plt.savefig(output_dir / "loan_amount_by_status.png")
    plt.close()


def plot_correlation_heatmap(df, output_dir):
    """Visualise les corrélations entre les variables numériques."""

    output_dir = create_output_directory(output_dir)

    numeric_df = df.select_dtypes(include="number")

    correlation = numeric_df.corr()

    plt.figure(figsize=(12, 9))

    sns.heatmap(correlation, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)

    plt.title("Matrice de corrélation des variables numériques")

    plt.tight_layout()

    plt.savefig(output_dir / "correlation_heatmap.png")
    plt.close()


def generate_all_visualizations(df, output_dir):
    """Génère tous les graphiques de l'analyse exploratoire."""

    plot_target_distribution(df, output_dir)

    plot_numeric_distributions(df, output_dir)

    plot_loan_amount_by_status(df, output_dir)

    plot_correlation_heatmap(df, output_dir)

    print("\nTous les graphiques ont été générés.")
    print(f"Emplacement : {output_dir}")
