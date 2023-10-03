from django import template

register = template.Library()


@register.filter
def get_title_to_display_in_html(document_title, document_type):
    if document_type == "press_summary":
        return document_title.removeprefix("Press Summary of ")
    return document_title


@register.filter
def display_datetime(dt):
    if dt is not None:
        return dt.strftime("%d %b %Y %H:%M")
    else:
        return None
