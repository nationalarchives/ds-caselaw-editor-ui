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
def status_tag(status):
    if status.lower() == DOCUMENT_STATUS_IN_PROGRESS.lower():
        return "in-progress"
    if status.lower() == DOCUMENT_STATUS_HOLD.lower():
        return "on-hold"
    if status.lower() == DOCUMENT_STATUS_PUBLISHED.lower():
        return "published"

    return "new"
