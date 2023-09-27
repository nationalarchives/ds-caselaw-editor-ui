from django import template

register = template.Library()


@register.filter
def get_title_to_display_in_html(document_title, document_type):
    if document_type == "press_summary":
        return document_title.removeprefix("Press Summary of ")
    return document_title


@register.filter
def display_datetime_date(datetime):
    return datetime.strftime("%d %b %Y")


@register.filter
def display_datetime_time(datetime):
    return datetime.strftime("%H:%M")


@register.filter
def display_friendly_version_type(string):
    if string == "transform":
        return "Submission"
    elif string == "tna-enriched":
        return "Enrichment"
    else:
        return ""
