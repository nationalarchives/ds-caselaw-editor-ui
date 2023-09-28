from django import template

from judgments.utils.view_helpers import user_is_superuser_or_editor

register = template.Library()


@register.filter(name="is_superuser_or_editor")
def is_superuser_or_editor(user):
    return user_is_superuser_or_editor(user)
