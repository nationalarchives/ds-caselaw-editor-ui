from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import (
    ChoiceLoader,
    Environment,
    PackageLoader,
    PrefixLoader,
    select_autoescape,
)

from judgments.templatetags.user_permissions import is_superuser


def environment(**options):
    base_loader = options.get("loader")
    govuk_loader = PrefixLoader(
        {
            "govuk_frontend_jinja": PackageLoader("govuk_frontend_jinja"),
        },
    )

    combined_loader = ChoiceLoader([base_loader, govuk_loader]) if base_loader else govuk_loader

    options["loader"] = combined_loader

    options.pop("autoescape", None)

    env = Environment(
        autoescape=select_autoescape(
            enabled_extensions=("jinja"),
            default_for_string=True,
            default=True,
        ),
        **options,
    )
    env.globals.update(
        {
            "static": staticfiles_storage.url,
            "url": reverse,
        },
    )

    env.filters["is_superuser"] = is_superuser
    return env
