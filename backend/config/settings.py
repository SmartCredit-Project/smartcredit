"""
Django settings for SmartCredit project.
"""

import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

# ============================================================
# 1. CONFIGURATION GENERALE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-smartcredit-development-key-change-me",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,smartcredit-backend,testserver",
    ).split(",")
    if host.strip()
]

RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")

if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# ============================================================
# 2. APPLICATIONS INSTALLEES
# ============================================================

INSTALLED_APPS = [
    # Applications natives Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Django REST Framework et authentification JWT
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    # Applications SmartCredit
    "accounts",
    "applicants",
    "credit_applications",
    "predictions",
    "dashboard",
]


# ============================================================
# 3. MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# 4. CONFIGURATION DES URLS
# ============================================================

ROOT_URLCONF = "config.urls"


# ============================================================
# 5. CONFIGURATION DES TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# 6. SERVEUR WSGI
# ============================================================

WSGI_APPLICATION = "config.wsgi.application"


# ============================================================
# 7. BASE DE DONNEES POSTGRESQL
# ============================================================


def parse_database_url(database_url):
    """Convertit une URL PostgreSQL Render en configuration Django."""

    parsed = urlparse(database_url)

    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL doit utiliser le protocole PostgreSQL.")

    options = dict(parse_qsl(parsed.query))

    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parsed.path.lstrip("/")),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "600")),
        "CONN_HEALTH_CHECKS": True,
    }

    if options:
        config["OPTIONS"] = options

    return config


DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASES = {"default": parse_database_url(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get(
                "DB_NAME",
                "smartcredit_db",
            ),
            "USER": os.environ.get(
                "DB_USER",
                "smartcredit_user",
            ),
            "PASSWORD": os.environ.get(
                "DB_PASSWORD",
                "",
            ),
            "HOST": os.environ.get(
                "DB_HOST",
                "localhost",
            ),
            "PORT": os.environ.get(
                "DB_PORT",
                "5432",
            ),
        }
    }


# ============================================================
# 8. MODELE UTILISATEUR PERSONNALISE
# ============================================================

AUTH_USER_MODEL = "accounts.User"


# ============================================================
# 9. DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    # Réponses JSON
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Réception des données JSON
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    # Authentification par JWT
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # Tous les endpoints sont protégés par défaut
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Documentation OpenAPI
    "DEFAULT_SCHEMA_CLASS": ("drf_spectacular.openapi.AutoSchema"),
    # Pagination des listes
    "DEFAULT_PAGINATION_CLASS": ("rest_framework.pagination.PageNumberPagination"),
    "PAGE_SIZE": 20,
}


# ============================================================
# 10. CONFIGURATION JWT
# ============================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "60"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.environ.get("JWT_REFRESH_DAYS", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ============================================================
# 11. DOCUMENTATION OPENAPI / SWAGGER
# ============================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "SmartCredit API",
    "DESCRIPTION": (
        "API REST de gestion des demandes de crédit et de "
        "prédiction du risque de non-remboursement."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ============================================================
# 12. CORS (APPLICATION FRONTEND SEPAREE)
# ============================================================

CORS_ALLOW_ALL_ORIGINS = (
    os.environ.get(
        "CORS_ALLOW_ALL_ORIGINS",
        "True" if DEBUG else "False",
    ).lower()
    == "true"
)

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "",
    ).split(",")
    if origin.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in (
        os.environ.get("CSRF_TRUSTED_ORIGINS") or ",".join(CORS_ALLOWED_ORIGINS)
    ).split(",")
    if origin.strip()
]

if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"

    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


# ============================================================
# 13. INTEGRATION DU MODELE MACHINE LEARNING
# ============================================================

MODEL_PATH = Path(
    os.environ.get(
        "MODEL_PATH",
        BASE_DIR.parent / "models" / "gradient_boosting_final.joblib",
    )
)

# Seuils de classification du niveau de risque.
# LOW    : probabilité < RISK_THRESHOLDS["MEDIUM"]
# MEDIUM : probabilité < RISK_THRESHOLDS["HIGH"]
# HIGH   : probabilité >= RISK_THRESHOLDS["HIGH"]
RISK_THRESHOLDS = {
    "MEDIUM": float(os.environ.get("RISK_THRESHOLD_MEDIUM", "0.30")),
    "HIGH": float(os.environ.get("RISK_THRESHOLD_HIGH", "0.59")),
}


# ============================================================
# 14. VALIDATION DES MOTS DE PASSE
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation." "NumericPasswordValidator"),
    },
]


# ============================================================
# 15. INTERNATIONALISATION
# ============================================================

LANGUAGE_CODE = "fr-fr"

TIME_ZONE = "Africa/Bujumbura"

USE_I18N = True

USE_TZ = True


# ============================================================
# 16. FICHIERS STATIQUES ET MEDIA
# ============================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# 17. MODELES DJANGO
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# 18. JOURNALISATION
# ============================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
}


# ============================================================
# 19. SECURITE EN PRODUCTION
# ============================================================

if not DEBUG:
    SECURE_SSL_REDIRECT = (
        os.environ.get("SECURE_SSL_REDIRECT", "True").lower() == "true"
    )

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
