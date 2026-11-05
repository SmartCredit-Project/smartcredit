from src.data.load_data import load_dataset
from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.training.split_data import split_data

# 1. Charger les données
df = load_dataset()

# 2. Nettoyer les données
cleaned_df, report = clean_dataset(df)

# 3. Séparer les caractéristiques et la cible
X, y = split_features_target(cleaned_df)

# 4. Séparer les données en entraînement et test
X_train, X_test, y_train, y_test = split_data(X, y)


# 5. Afficher les résultats
print("\n========== TEST TRAIN-TEST SPLIT ==========")

print("\nDimensions initiales :")
print("X :", X.shape)
print("y :", y.shape)

print("\nDimensions après séparation :")
print("X_train :", X_train.shape)
print("X_test  :", X_test.shape)
print("y_train :", y_train.shape)
print("y_test  :", y_test.shape)

print("\nDistribution de y_train :")
print((y_train.value_counts(normalize=True) * 100).round(2))

print("\nDistribution de y_test :")
print((y_test.value_counts(normalize=True) * 100).round(2))

print("\nNombre total d'observations :")
print(len(X_train) + len(X_test))

print("\nVérification des index communs :")
common_indexes = set(X_train.index) & set(X_test.index)
print("Index communs :", len(common_indexes))

print("\n========== TEST TERMINÉ ==========")
