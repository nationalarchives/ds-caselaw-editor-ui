from django import template

from judgments.utils.view_helpers import (
    user_is_developer,
    user_is_editor,
    user_is_superuser,
)

register = template.Library()


@register.filter(name="is_superuser")
def is_superuser(user):
    return user_is_superuser(user)


@register.filter(name="is_editor")
def is_editor(user):
    return user_is_editor(user)


@register.filter(name="is_developer")
def is_developer(user):
    return user_is_developer(user)
