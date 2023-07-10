from caselawclient.models.documents import (
    DOCUMENT_STATUS_HOLD,
    DOCUMENT_STATUS_IN_PROGRESS,
    DOCUMENT_STATUS_PUBLISHED,
)
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def status_tag_colour(status):
    if status == DOCUMENT_STATUS_IN_PROGRESS:
        return "light-blue"
    if status == DOCUMENT_STATUS_HOLD:
        return "red"
    if status == DOCUMENT_STATUS_PUBLISHED:
        return "green"
    return "grey"
