import time

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.data.load_data import load_dataset
from src.features.feature_selection import split_features_target
from src.preprocessing.cleaning import clean_dataset
from src.training.model_pipeline import create_logistic_regression_pipeline
from src.training.split_data import split_data

# 1. Charger les données
df = load_dataset()

# 2. Nettoyer les données
cleaned_df, report = clean_dataset(df)

# 3. Séparer les caractéristiques et la cible
X, y = split_features_target(cleaned_df)

# 4. Séparer les données en entraînement et test
X_train, X_test, y_train, y_test = split_data(X, y)


# 5. Construire le pipeline
model = create_logistic_regression_pipeline()


# 6. Entraîner le modèle
print("\n========== ENTRAÎNEMENT DU MODÈLE ==========")

start_time = time.time()

model.fit(X_train, y_train)

training_time = time.time() - start_time

print("Entraînement terminé !")
print(f"Temps d'entraînement : {training_time:.4f} secondes")


# 7. Effectuer les prédictions
print("\n========== PRÉDICTIONS ==========")

start_time = time.time()

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

inference_time = time.time() - start_time

print("Prédictions terminées !")
print(f"Temps de prédiction : {inference_time:.4f} secondes")


# 8. Évaluer le modèle
print("\n========== ÉVALUATION DU MODÈLE ==========")

print(f"Accuracy  : {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision : {precision_score(y_test, y_pred, zero_division=0):.4f}")
print(f"Recall    : {recall_score(y_test, y_pred, zero_division=0):.4f}")
print(f"F1-score  : {f1_score(y_test, y_pred, zero_division=0):.4f}")
print(f"ROC-AUC   : {roc_auc_score(y_test, y_proba):.4f}")

print("\nMatrice de confusion :")
print(confusion_matrix(y_test, y_pred))

print("\nRapport de classification :")
print(classification_report(y_test, y_pred, zero_division=0))

print("\n========== TEST TERMINÉ ==========")
