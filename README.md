# SmartCredit

Backend de gestion des demandes de crédit et de prédiction du risque de
non-remboursement.

Le projet est développé **exclusivement avec Django REST Framework**. Aucune
API FastAPI n'est utilisée. Le modèle de Machine Learning est entraîné et
sauvegardé séparément, puis consommé par Django pour produire les prédictions.

## 1. Architecture

```text
Frontend
   |
   | HTTP / JSON + JWT
   v
Django REST Framework
   |--- Authentification email + mot de passe (SimpleJWT)
   |--- Gestion des utilisateurs, rôles et institutions
   |--- Gestion des demandeurs et affectation aux agents
   |--- Gestion des demandes de crédit
   |--- Prédictions et historique
   |--- Journal d'activité et drapeaux de fonctionnalité
   |--- Statistiques du tableau de bord
   |
   v
Service de prédiction (Scikit-Learn)
   |
   v
PostgreSQL
```

Le modèle entraîné est stocké dans
`models/gradient_boosting_final.joblib`. Il est chargé une seule fois en
mémoire grâce à un cache (`functools.lru_cache`).

## 2. Technologies

- Python
- Django
- Django REST Framework
- djangorestframework-simplejwt (authentification JWT)
- drf-spectacular (OpenAPI / Swagger)
- django-cors-headers
- PostgreSQL
- Scikit-Learn, Pandas, NumPy, Joblib
- Docker et Docker Compose

## 3. Structure du projet

```text
backend/
  config/                 Configuration Django
  accounts/               Utilisateurs, rôles, institutions, journaux,
                          drapeaux, authentification
  applicants/             Demandeurs de crédit
  credit_applications/    Demandes de crédit
  predictions/            Modèles, service ML, API de prédiction
  dashboard/              Statistiques et tableaux de bord
  manage.py
models/
  gradient_boosting_final.joblib
src/                      Entraînement et évaluation du modèle
data/                     Données brutes et traitées
Dockerfile
docker-compose.yml
requirements.txt
```

## 4. Configuration

Copier le fichier d'exemple :

```bash
cp .env.example .env
```

Variables principales :

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django |
| `DJANGO_DEBUG` | Mode debug (`True` / `False`) |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL |
| `MODEL_PATH` | Chemin de l'artefact Machine Learning |
| `RISK_THRESHOLD_MEDIUM` | Seuil bas du risque modéré (0.30) |
| `RISK_THRESHOLD_HIGH` | Seuil du risque élevé (0.59) |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | Durées des tokens |
| `CORS_ALLOWED_ORIGINS` | Origines autorisées du frontend |

## 5. Démarrage avec Docker

```bash
docker compose up --build -d
```

L'API est disponible sur `http://localhost:8000/api/`.

Création d'un administrateur :

```bash
docker compose exec smartcredit-backend python manage.py createsuperuser
```

L'administration Django (`/admin/`) se connecte avec **l'adresse
électronique et le mot de passe** du compte (le nom d'utilisateur interne
n'est pas demandé).

Appliquer les migrations manuellement si nécessaire :

```bash
docker compose exec smartcredit-backend python manage.py migrate
```

## 6. Démarrage local sans Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd backend
python manage.py migrate
python manage.py runserver
```

PostgreSQL doit être disponible et les variables d'environnement de connexion
doivent être définies.

## 7. Rôles et permissions

| Rôle | Accès |
|---|---|
| `SUPERADMIN` | Accès global : utilisateurs, institutions, journaux, drapeaux, demandes et prédictions |
| `ADMIN` | Limité à son institution : agents, demandeurs, demandes, prédictions, affectations et statistiques |
| `CREDIT_AGENT` | Limité à son institution : demandeurs, demandes et prédictions |
| `APPLICANT` | Fiche et demandes personnelles ; création et prédiction sur ses propres demandes |

Règles principales :

- L'authentification se fait avec **email + mot de passe**.
- L'inscription publique crée toujours un compte `APPLICANT`.
- Un `SUPERADMIN` gère les `ADMIN` et les institutions.
- Un `ADMIN` crée, modifie et désactive uniquement les `CREDIT_AGENT` de son
  institution.
- Un `CREDIT_AGENT` enregistre les demandeurs et traite les demandes de son
  institution.
- Un demandeur créé par un agent peut s'inscrire plus tard avec le même email :
  son compte est automatiquement rattaché au dossier existant.
- Les données sont systématiquement filtrées par institution, sauf pour le
  `SUPERADMIN`.
- Les suppressions d'utilisateurs sont réalisées par désactivation.

Toutes les routes sont protégées par JWT sauf l'inscription, la connexion, le
renouvellement du token et le contrôle de santé.

## 8. Endpoints API

### Authentification

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Inscription |
| POST | `/api/auth/login/` | Connexion par email (retourne `access` et `refresh`) |
| POST | `/api/auth/refresh/` | Renouvellement du token |
| POST | `/api/auth/logout/` | Déconnexion (blacklist du refresh) |
| GET | `/api/auth/me/` | Utilisateur courant |

Le token doit être envoyé dans l'en-tête :

```http
Authorization: Bearer <access_token>
```

Exemple de connexion :

```json
{
  "email": "admin@example.com",
  "password": "MotDePasse!2026"
}
```

### Utilisateurs

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/users/` | Liste des utilisateurs (filtrée par institution) |
| POST | `/api/users/` | Création d'un utilisateur |
| GET | `/api/users/{id}/` | Détail |
| PUT/PATCH | `/api/users/{id}/` | Modification |
| DELETE | `/api/users/{id}/` | Désactivation |

### Institutions, journaux et drapeaux

| Méthode | Endpoint | Description |
|---|---|---|
| GET/POST | `/api/institutions/` | Institutions financières |
| GET/PUT/PATCH/DELETE | `/api/institutions/{id}/` | Détail d'une institution |
| GET | `/api/activity-logs/` | Journal d'activité |
| GET/POST | `/api/feature-flags/` | Drapeaux de fonctionnalité |
| GET/PUT/PATCH/DELETE | `/api/feature-flags/{id}/` | Détail d'un drapeau |

Les écritures sur les institutions et les drapeaux sont réservées au
`SUPERADMIN`. Le drapeau `predictions` permet de désactiver les prédictions.

### Demandeurs

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/applicants/` | Créer un demandeur |
| GET | `/api/applicants/` | Liste des demandeurs |
| GET | `/api/applicants/{id}/` | Détail |
| PUT/PATCH | `/api/applicants/{id}/` | Modifier |
| DELETE | `/api/applicants/{id}/` | Supprimer |

Filtre disponible : `?search=`.

### Demandes de crédit

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/credit-applications/` | Créer une demande |
| GET | `/api/credit-applications/` | Lister les demandes |
| GET | `/api/credit-applications/{id}/` | Consulter |
| PUT/PATCH | `/api/credit-applications/{id}/` | Modifier |
| PATCH | `/api/credit-applications/{id}/status/` | Modifier l'état |
| PATCH | `/api/credit-applications/{id}/assign/` | Affecter un agent |
| GET | `/api/credit-applications/{id}/prediction/` | Dernière prédiction |

Filtres disponibles : `?status=`, `?applicant=`, `?loan_intent=`,
`?assigned_agent=`.

L'affectation est réservée au `SUPERADMIN` et aux `ADMIN` et doit cibler un
agent de la même institution que la demande.

États : `PENDING`, `IN_ANALYSIS`, `ANALYZED`, `ACCEPTED`, `REJECTED`.

Les transitions d'état sont contrôlées par le serveur.

### Prédictions

| Méthode | Endpoint | Description |
|---|---|---|
| POST | `/api/predictions/` | Effectuer une prédiction |
| GET | `/api/predictions/` | Historique des prédictions |
| GET | `/api/predictions/{id}/` | Détail d'une prédiction |
| GET | `/api/model-info/` | Informations sur le modèle actif |
| GET | `/api/health/` | État du service et du modèle |

La prédiction se base uniquement sur une demande de crédit déjà
enregistrée. Les caractéristiques sont lues côté serveur, ce qui évite de
les transmettre une seconde fois :

```json
{
  "credit_application": 1
}
```

La demande doit exister, avoir un revenu strictement positif et être
accessible par l'utilisateur connecté. Un demandeur ne peut analyser que ses
propres demandes, un `ADMIN` ou un `CREDIT_AGENT` uniquement celles de son
institution, et un `SUPERADMIN` toutes les demandes.

Une seule prédiction est autorisée par demande. Une nouvelle tentative
renvoie `409 Conflict` avec l'identifiant de la prédiction existante.

Exemple de réponse :

```json
{
  "id": 12,
  "credit_application": 1,
  "prediction": 1,
  "predicted_class": 1,
  "result": "DEFAULT_RISK_DETECTED",
  "default_probability": 0.82,
  "default_probability_percentage": 82.0,
  "no_default_probability": 0.18,
  "risk_level": "HIGH",
  "risk_level_display": "Risque élevé",
  "message": "Risque élevé de défaut de remboursement.",
  "model_name": "Gradient Boosting équilibré optimisé",
  "model_version": {
    "id": 1,
    "name": "Gradient Boosting équilibré optimisé",
    "version": "1.0.0",
    "algorithm": "GradientBoostingClassifier",
    "is_active": true
  },
  "decision_threshold": 0.59,
  "disclaimer": "Cette prédiction est une estimation statistique..."
}
```

Le résultat est enregistré dans PostgreSQL avec la version du modèle utilisée.

### Tableau de bord

| Méthode | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/` | Statistiques générales |
| GET | `/api/dashboard/predictions/` | Statistiques des prédictions |
| GET | `/api/dashboard/applications/` | Statistiques des demandes |

Ces endpoints sont réservés au personnel (super administrateur,
administrateur d'institution et agent de crédit) et filtrés par institution.

### Documentation OpenAPI

- Schéma OpenAPI : `/api/schema/`
- Swagger UI : `/api/docs/`

## 9. Intégration du modèle

Le pipeline final utilise sept variables :

1. `person_age`
2. `person_income`
3. `person_home_ownership`
4. `person_emp_length`
5. `loan_intent`
6. `loan_amnt`
7. `loan_percent_income`

`loan_percent_income` est calculé automatiquement par le backend à partir de
`loan_amnt / person_income`, afin de rester cohérent avec le prétraitement
utilisé à l'entraînement.

Le seuil de décision du modèle est de `0.59`. Les niveaux de risque sont
définis ainsi :

| Probabilité de défaut | Niveau |
|---|---|
| `< 0.30` | `LOW` |
| `0.30` à `< 0.59` | `MEDIUM` |
| `>= 0.59` | `HIGH` |

La prédiction est une aide à la décision. La décision finale d'acceptation ou
de refus reste sous la responsabilité de l'institution financière.

## 10. Tests

```bash
cd backend
python manage.py test
```

Les tests couvrent l'authentification par email, les quatre rôles, le cloisonnement
par institution, l'affectation des demandes, les drapeaux de fonctionnalité,
les demandeurs, les demandes de crédit, les prédictions et les statistiques.

Avec Docker :

```bash
docker compose exec smartcredit-backend python manage.py test
```

## 11. Migrations

```bash
cd backend
python manage.py makemigrations
python manage.py migrate
```

Les migrations des applications `accounts`, `applicants`,
`credit_applications` et `predictions` sont versionnées dans le dépôt.

## 12. Qualité du code et pre-commit

Le projet utilise `pre-commit` avec les hooks suivants :

1. `trailing-whitespace` : suppression des espaces en fin de ligne.
2. `end-of-file-fixer` : fichier terminé par un saut de ligne.
3. `check-yaml` : validation des fichiers YAML.
4. `check-json` : validation des fichiers JSON.
5. `check-added-large-files` : blocage des fichiers trop volumineux.
6. `check-merge-conflict` : détection des marqueurs de conflit Git.
7. `detect-private-key` : détection de clés privées.
8. `black` : formatage du code Python.
9. `isort` : tri des imports Python.
10. `flake8` : contrôle de la qualité et du style du code.

Installation des outils de développement :

```bash
pip install -r requirements-dev.txt
pre-commit install
```

Exécution manuelle sur tous les fichiers :

```bash
pre-commit run --all-files
```

La configuration se trouve dans `.pre-commit-config.yaml`, `.flake8` et
`pyproject.toml`. Les hooks s'exécutent automatiquement avant chaque commit
après `pre-commit install`.
