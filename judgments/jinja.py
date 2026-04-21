from caselawclient.models.documents import (
    DOCUMENT_STATUS_HOLD,
    DOCUMENT_STATUS_IN_PROGRESS,
    DOCUMENT_STATUS_PUBLISHED,
)
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import (
    ChoiceLoader,
    Environment,
    PackageLoader,
    PrefixLoader,
    pass_context,
    select_autoescape,
)

from judgments.templatetags.document_utils import get_title_to_display_in_html
from judgments.templatetags.navigation_tags import get_navigation_items
from judgments.templatetags.user_permissions import is_editor, is_superuser


def get_badge_variant_from_status(status):
    if status.lower() in (DOCUMENT_STATUS_IN_PROGRESS.lower(), "in progress"):
        return "info"
    if status.lower() in (DOCUMENT_STATUS_HOLD.lower(), "hold"):
        return "failure"
    if status.lower() == DOCUMENT_STATUS_PUBLISHED.lower():
        return "success"

    return "info"


def format_date(value, fmt="%-d %b %Y"):
    return value.strftime(fmt) if value else ""


@pass_context
def get_document_navigation_items(context):
    return get_navigation_items(context)


def jinja_url(name, *args, **kwargs):
    return reverse(name, args=args or None, kwargs=kwargs or None)


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
            "url": jinja_url,
            "get_badge_variant_from_status": get_badge_variant_from_status,
            "get_navigation_items": get_document_navigation_items,
        },
    )

    env.filters["is_superuser"] = is_superuser
    env.filters["is_editor"] = is_editor
    env.filters["date"] = format_date
    env.filters["get_title_to_display_in_html"] = get_title_to_display_in_html
    return env
