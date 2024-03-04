import json

from django import template

register = template.Library()


@register.filter
def get_title_to_display_in_html(document_title, document_type):
    if document_type == "press_summary":
        return document_title.removeprefix("Press Summary of ")
    return document_title


@register.filter
def display_datetime(dt):
    return dt.strftime("%d %b %Y %H:%M")


VERSION_TYPE_LABELS = {
    "submission": "Submitted",
    "enrichment": "Enriched",
    "edit": "Edited",
}


@register.filter
def render_json(json_string):
    return json.dumps(json_string, indent=2)


@register.filter
def display_annotation_type(annotation):
    try:
        annotation_data = json.loads(annotation)
        version_type = annotation_data.get("type")
        return VERSION_TYPE_LABELS.get(version_type, version_type)
    except (TypeError, json.JSONDecodeError):
        return annotation


@register.filter
def can_enrich(document):
    return document.can_enrich()


@register.filter
def can_reparse(document):
    return document.can_reparse()
