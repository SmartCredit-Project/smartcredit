from src.data.load_data import load_dataset
from src.preprocessing.cleaning import clean_dataset
from src.preprocessing.preprocessing import (
    create_preprocessor,
    FEATURE_COLUMNS,
)

# 1. Charger le dataset original
df = load_dataset()

# 2. Nettoyer les données
df, report = clean_dataset(df)

# 3. Sélectionner les variables explicatives
X = df[FEATURE_COLUMNS].copy()

print("\n========== AVANT PRÉTRAITEMENT ==========")

print("Dimensions :", X.shape)

print("\nValeurs manquantes :")
print(X.isnull().sum())

print("\nAperçu :")
print(X.head())

# 4. Créer le préprocesseur
preprocessor = create_preprocessor()

# 5. Apprendre et appliquer les transformations
X_transformed = preprocessor.fit_transform(X)

print("\n========== APRÈS PRÉTRAITEMENT ==========")

print("Dimensions :", X_transformed.shape)

print("Type :", type(X_transformed))

print("\nPremières lignes transformées :")
print(X_transformed[:5])

print("\n========== TEST TERMINÉ ==========")