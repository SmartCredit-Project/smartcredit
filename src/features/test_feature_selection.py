from src.data.load_data import load_dataset
from src.preprocessing.cleaning import clean_dataset
from src.features.feature_selection import split_features_target

# 1. Charger les données
df = load_dataset()

# 2. Nettoyer les données
cleaned_df, report = clean_dataset(df)

# 3. Séparer X et y
X, y = split_features_target(cleaned_df)

# 4. Afficher les résultats
print("\n========== TEST FEATURE SELECTION ==========")

print("\nDimensions de X :", X.shape)
print("Dimensions de y :", y.shape)

print("\nColonnes de X :")
print(X.columns.tolist())

print("\nNom de la variable cible :", y.name)

print("\nDistribution de y :")
print(y.value_counts())

print("\nValeurs manquantes dans X :")
print(X.isnull().sum())

print("\n========== TEST TERMINÉ ==========")