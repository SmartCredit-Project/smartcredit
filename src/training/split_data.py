from sklearn.model_selection import train_test_split


def split_data(X, y, test_size=0.2, random_state=42):
    """
    Divise les données en deux ensembles :
    - Entraînement : 80 %
    - Test : 20 %

    X : caractéristiques
    y : variable cible
    test_size : proportion réservée au test
    random_state : garantit la reproductibilité
    """

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    return X_train, X_test, y_train, y_test
