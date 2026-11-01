from django import template

from judgments.utils.permissions import editors_only_hint
from judgments.utils.view_helpers import (
    user_can_edit,
    user_is_developer,
    user_is_editor,
    user_is_editor_or_developer,
    user_is_superuser,
)

register = template.Library()

DOCUMENT_RESTORE_PUBLISHED_DISABLED_REASON = "Unpublish this document first to restore to this version"


@register.simple_tag
def is_document_restore_disabled(document, user):
    return document.is_published or not user_can_edit(user)


@register.simple_tag
def get_document_restore_disabled_reason(document, user):
    if document.is_published:
        return DOCUMENT_RESTORE_PUBLISHED_DISABLED_REASON
    if not user_can_edit(user):
        return editors_only_hint()
    return None


@register.filter(name="is_superuser")
def is_superuser(user):
    return user_is_superuser(user)


@register.filter(name="is_editor")
def is_editor(user):
    return user_is_editor(user)


@register.filter(name="is_developer")
def is_developer(user):
    return user_is_developer(user)


@register.filter(name="can_edit")
def can_edit(user):
    return user_can_edit(user)


@register.filter(name="is_editor_or_developer")
def is_editor_or_developer(user):
    return user_is_editor_or_developer(user)
