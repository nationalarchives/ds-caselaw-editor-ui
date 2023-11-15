"""
With these settings, tests run faster.
"""

from .base import *  # noqa
from .base import TEMPLATES

# GENERAL
# ------------------------------------------------------------------------------
SECRET_KEY = "not-secret-whatsoever"  # noqa: S105

# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Your stuff...
# ------------------------------------------------------------------------------

TEMPLATES[0]["OPTIONS"]["debug"] = True  # type: ignore[index]
