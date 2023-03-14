from django import template
from django.template.defaultfilters import stringfilter

from judgments.models.judgments import (
    JUDGMENT_STATUS_HOLD,
    JUDGMENT_STATUS_IN_PROGRESS,
    JUDGMENT_STATUS_PUBLISHED,
)

register = template.Library()


@register.filter
@stringfilter
def status_tag_colour(status):
    if status == JUDGMENT_STATUS_IN_PROGRESS:
        return "light-blue"
    if status == JUDGMENT_STATUS_HOLD:
        return "red"
    if status == JUDGMENT_STATUS_PUBLISHED:
        return "green"
    return "grey"
