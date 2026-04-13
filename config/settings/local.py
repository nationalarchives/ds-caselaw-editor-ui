import os
from pathlib import Path

from .base import *  # noqa: F403
from .base import MIDDLEWARE, ROOT_DIR, TEMPLATES, env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["*"]

if env("TEMPLATE_DEBUG", default=None):
    TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = "{{ %s }}"

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    },
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa: F405

SECRET_KEY = "not-secret-whatsoever"  # noqa: S105


# django-debug-toolbar
# ------------------------------------------------------------------------------
def show_debug_toolbar(request):
    return False


MIDDLEWARE += [
    "config.vcr_middleware.VCRMiddleware",
]

VCR_ENABLED = os.getenv("VCR_ENABLED", "true").lower() == "true"
VCR_MODE = os.getenv("VCR_MODE", "playback")
VCR_CASSETTE_DIR = str(ROOT_DIR / "vcr_cassettes")

if VCR_ENABLED:
    Path(VCR_CASSETTE_DIR).mkdir(parents=True, exist_ok=True)

# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]  # F405
    # https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    # https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
    DEBUG_TOOLBAR_CONFIG = {
        "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
        "SHOW_TEMPLATE_CONTEXT": True,
        "SHOW_TOOLBAR_CALLBACK": show_debug_toolbar,
    }

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # F405

# Your stuff...
# ------------------------------------------------------------------------------
