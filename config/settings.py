"""Configure the Kindelise Django project from environment-owned settings."""

# KEYWORD: environment variable — a private setting supplied outside the saved code, such as a password or web address.
# KEYWORD: middleware — a shared check that runs around each page request.
# KEYWORD: static file — a design or browser file, such as CSS or JavaScript, that is the same for every visitor.
# KEYWORD: media file — an uploaded image that belongs to saved profile or plan information.
# KEYWORD: CSRF — a private form check that stops another website submitting as the signed-in visitor.


import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

# WHY: Gives every local folder setting one dependable starting point at the repository root.
BASE_DIR = Path(__file__).resolve().parent.parent


# WHY: Keeps the environment flag steps in one named place so they can be understood, checked, and reused.
def _environment_flag(name, default=False):
    """Return one strict boolean environment setting."""
    # WHY: Reads the requested deployment value without assuming it was supplied.
    value = os.environ.get(name)

    # WHY: Uses the stated fallback only when the setting is genuinely absent.
    if value is None:
        return default

    # WHY: Ignores harmless capital letters and spaces before checking the intended meaning.
    normalized = value.strip().lower()

    # WHY: Accepts only a short, clear list of words that mean enabled.
    if normalized in {"1", "true", "yes", "on"}:
        return True

    # WHY: Accepts only a short, clear list of words that mean disabled.
    if normalized in {"0", "false", "no", "off"}:
        return False

    # WHY: Refuses a spelling mistake instead of silently choosing an unsafe value.
    raise ImproperlyConfigured(f"{name} must be true or false")


# WHY: Shows detailed errors during local work but must be false on the public website.
DEBUG = _environment_flag("DJANGO_DEBUG")

# WHY: Signs private Django values so visitors cannot alter cookies, form tokens, or password-reset links.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

# WHY: Stops the site starting without its private signing key instead of silently using an unsafe default.
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set")

# WHY: Accepts requests only for the website names explicitly supplied by the environment.
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]

# WHY: Allows secure forms to arrive from the exact public website addresses configured for this deployment.
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# WHY: Lists the Django features, upload service, and Kindelise application that must be prepared at startup.
INSTALLED_APPS = [
    # WHY: Provides the private staff pages used for verification and moderation.
    "django.contrib.admin",
    # WHY: Provides accounts, passwords, sign-in sessions, and permissions.
    "django.contrib.auth",
    # WHY: Lets Django identify the saved information used by permissions and staff pages.
    "django.contrib.contenttypes",
    # WHY: Remembers which signed-in account owns each browser session.
    "django.contrib.sessions",
    # WHY: Carries short success or error notices to the visitor's next page.
    "django.contrib.messages",
    # WHY: Finds and serves the site's CSS, JavaScript, and fixed images.
    "django.contrib.staticfiles",
    # WHY: Connects uploaded profile and plan images to Cloudinary on the live website.
    "cloudinary_storage",
    # WHY: Supplies the Cloudinary image service used by the storage connection above.
    "cloudinary",
    # WHY: Loads the Kindelise models, pages, forms, and other application code.
    "kindlelise.apps.KindleliseConfig",
]

# WHY: Runs these shared request checks in this exact order around every page visit.
MIDDLEWARE = [
    # WHY: Adds Django's common browser security protections to every response.
    "django.middleware.security.SecurityMiddleware",
    # WHY: Lets the live app serve versioned CSS and JavaScript without a separate file server.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # WHY: Finds the visitor's signed-in session before page code needs it.
    "django.contrib.sessions.middleware.SessionMiddleware",
    # WHY: Applies normal address and response handling shared by Django pages.
    "django.middleware.common.CommonMiddleware",
    # WHY: Rejects unsafe form submissions that do not carry this site's private form token.
    "django.middleware.csrf.CsrfViewMiddleware",
    # WHY: Turns the saved session into request.user for permission checks.
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # WHY: Makes temporary success and error notices available to page templates.
    "django.contrib.messages.middleware.MessageMiddleware",
    # WHY: Stops another website placing Kindelise inside a frame to disguise clicks.
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# WHY: Points Django to the top-level address list that chooses which page handles each URL.
ROOT_URLCONF = "config.urls"

# WHY: Defines where Django finds page templates and which shared values every template receives.
TEMPLATES = [
    {
        # WHY: Uses Django's safe template reader and automatic HTML escaping.
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # WHY: Adds the repository's templates folder to Django's page search locations.
        "DIRS": [BASE_DIR / "templates"],
        # WHY: Also allows an installed application to provide its own templates folder.
        "APP_DIRS": True,
        "OPTIONS": {
            # WHY: Makes the request, account, temporary notices, and notification count available across pages.
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "kindlelise.context_processors.notification_badge",
            ],
        },
    },
]

# WHY: Exposes the same Django site through the two standard server doorways supported by hosting tools.
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# WHY: Prefers Heroku's single database address while retaining clear local PostgreSQL settings below.
database_url = os.environ.get("DATABASE_URL")

# WHY: Uses hosted database details only when the environment supplied a database address.
if database_url:
    # WHY: Separates the address into the individual connection details Django needs.
    parsed_database_url = urlparse(database_url)

    # WHY: Refuses another database type because the models rely on PostgreSQL behaviour.
    if parsed_database_url.scheme not in {"postgres", "postgresql"}:
        raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL")
    database_name = unquote(parsed_database_url.path.lstrip("/"))

    # WHY: Refuses an incomplete address before Django attempts a confusing connection.
    if not database_name:
        raise ImproperlyConfigured("DATABASE_URL must include a database name")
    database_options = dict(parse_qsl(parsed_database_url.query))

    # WHY: Builds Django's named default connection from the checked hosted address.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": database_name,
            "USER": unquote(parsed_database_url.username or ""),
            "PASSWORD": unquote(parsed_database_url.password or ""),
            "HOST": parsed_database_url.hostname or "",
            "PORT": str(parsed_database_url.port or ""),
            "OPTIONS": database_options,
            # WHY: Reuses a healthy connection briefly instead of reconnecting for every page.
            "CONN_MAX_AGE": 60,
            # WHY: Checks a reused connection before trusting it after a server interruption.
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    # WHY: Uses separate, readable PostgreSQL values when running locally without Heroku's address.
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "kindlelise"),
            "USER": os.environ.get("POSTGRES_USER", "kindlelise"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            # WHY: Uses the same short connection reuse and health checks during local work.
            "CONN_MAX_AGE": 60,
            "CONN_HEALTH_CHECKS": True,
        }
}

# WHY: Applies Django's standard password checks when a visitor creates or changes a password.
AUTH_PASSWORD_VALIDATORS = [
    # WHY: Discourages passwords that closely repeat the person's account details.
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    # WHY: Rejects passwords that are too short to provide reasonable protection.
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    # WHY: Rejects widely used passwords that are easy to guess.
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    # WHY: Rejects passwords made only from numbers because they are commonly weak.
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# WHY: Uses British wording and London time while storing moments consistently with time-zone information.
LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

# WHY: Defines the public address and collected deployment folder for fixed CSS and JavaScript.
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# WHY: Includes the source static folder during local work when that folder exists.
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# WHY: Defines the local upload folder and address used when Cloudinary is not configured.
MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "media/"

# WHY: Stores uploads in Cloudinary on configured deployments and on disk for simple local work.
media_storage_backend = (
    "cloudinary_storage.storage.MediaCloudinaryStorage"
    if os.environ.get("CLOUDINARY_URL")
    else "django.core.files.storage.FileSystemStorage"
)

# WHY: Uses separate storage rules because visitor uploads and fixed site files have different jobs.
STORAGES = {
    # WHY: Sends profile and plan uploads through the selected media storage above.
    "default": {"BACKEND": media_storage_backend},
    # WHY: Compresses fixed files and renames changed files so browsers do not show stale designs.
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

# WHY: Gives new saved rows large automatic numeric identifiers without repeating this in every model.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# WHY: Gives protected pages one shared sign-in destination and a safe landing page afterwards.
LOGIN_URL = "sign_in"
LOGIN_REDIRECT_URL = "home"

# WHY: Prevents browser scripts from reading the signed-in session cookie.
SESSION_COOKIE_HTTPONLY = True

# WHY: Allows normal same-site navigation while limiting cookies on visits begun by another website.
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# WHY: Requires encrypted cookies and HTTPS on the live site but keeps local HTTP development usable.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG

# WHY: Lets Django recognise the original HTTPS visit after Heroku passes it through its front server.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# WHY: Stops browsers guessing a different file type from the one the site declared.
SECURE_CONTENT_TYPE_NOSNIFF = True

# WHY: Sends only this site's origin when following links so full private page addresses are not disclosed.
SECURE_REFERRER_POLICY = "same-origin"

# KEYWORD: HSTS — tells a browser to use HTTPS for future visits without trying insecure HTTP first.
# WHY: Keeps long-term HTTPS protection on in production and off during local development.
SECURE_HSTS_SECONDS = 31_536_000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# WHY: Prevents every Kindelise page from being displayed inside another website's frame.
X_FRAME_OPTIONS = "DENY"

# WHY: Keeps the permitted broad-area keys and their visitor-facing labels in one shared list.
KINDLELISE_AREAS = {
    "central": "Central",
    "north": "North",
    "south": "South",
    "east": "East",
    "west": "West",
}

# WHY: Defines which nearby areas Premium may add without using an exact location or distance.
KINDLELISE_NEARBY_AREAS = {
    "central": ["north", "south", "east", "west"],
    "north": ["central"],
    "south": ["central"],
    "east": ["central"],
    "west": ["central"],
}

# WHY: Reads private Stripe credentials and the approved yearly price from deployment settings.
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")

# WHY: Reads the wording-service address, private key, chosen model, and time limit from deployment settings.
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "")

# WHY: Converts the written time limit into seconds and rejects a value Django cannot use.
try:
    OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "10"))
except ValueError as error:
    raise ImproperlyConfigured("OLLAMA_TIMEOUT_SECONDS must be an integer") from error

# WHY: Prevents a zero or negative value from disabling the intended outside-request timeout.
if OLLAMA_TIMEOUT_SECONDS <= 0:
    raise ImproperlyConfigured("OLLAMA_TIMEOUT_SECONDS must be positive")
