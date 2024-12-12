from django import template
from django.urls import reverse

register = template.Library()


def get_document_url(view, document):
    if view:
        return reverse(view, kwargs={"document_uri": document.uri})
    else:
        return None


def get_hold_navigation_item(view, document):
    if document.is_published:
        return None

    identifier = "take-off-hold" if document.is_held else "put-on-hold"
    label = "Take off hold" if document.is_held else "Put on hold"
    selected = view in ("hold_judgment", "unhold_judgment")
    path = "unhold-document" if document.is_held else "hold-document"

    return {
        "id": identifier,
        "selected": selected,
        "label": label,
        "url": get_document_url(path, document),
    }


def get_publishing_navigation_item(view, document):
    selected = view in ("unpublish_judgment", "publish_judgment")
    label = "Unpublish" if document.is_published else "Publish"
    identifier = "unpublished" if document.is_published else "publish"
    path = "unpublish-document" if document.is_published else "publish-document"

    return {
        "id": identifier,
        "selected": selected,
        "label": label,
        "url": get_document_url(path, document),
    }


def get_download_navigation_item(view, document):
    return {
        "id": "downloads",
        "selected": view == "document_downloads",
        "label": "Downloads",
        "url": get_document_url("document-downloads", document),
    }


def get_review_navigation_item(view, document):
    return {
        "id": "review",
        "selected": view in ("judgment_html", "judgment_pdf"),
        "label": "Review",
        "url": get_document_url("full-text-html", document),
    }


def get_history_navigation_item(view, document):
    return {
        "id": "history",
        "selected": view == "document_history",
        "label": "History",
        "url": get_document_url("document-history", document),
    }


def get_associated_documents_navigation_item(view, document):
    return {
        "id": "associated_documents",
        "selected": view == "associated_documents",
        "label": "Associated documents",
        "url": get_document_url("associated-documents", document),
    }


def get_identifiers_navigation_item(view, document):
    return {
        "id": "identifiers",
        "selected": view == "document_identifiers",
        "label": "Identifiers",
        "url": get_document_url("document-identifiers", document),
    }


@register.simple_tag(takes_context=True)
def get_navigation_items(context):
    view, document, linked_document_uri = (
        context.get("view"),
        context.get("document"),
        context.get("linked_document_uri"),
    )

    base_navigation = [
        get_review_navigation_item(view, document),
        get_hold_navigation_item(view, document),
        get_publishing_navigation_item(view, document),
        get_identifiers_navigation_item(view, document),
        get_history_navigation_item(view, document),
        get_download_navigation_item(view, document),
    ]

    filtered_navigation = [item for item in base_navigation if item is not None]

    if linked_document_uri:
        return [*filtered_navigation, get_associated_documents_navigation_item(view, document)]

    return filtered_navigation


@register.simple_tag(takes_context=True)
def get_view_control_tabs(context):
    view, document = context["view"], context["document"]

    return [
        {
            "id": "html-view",
            "selected": view == "judgment_html",
            "label": "HTML view",
            "url": get_document_url("full-text-html", document),
        },
        {
            "id": "pdf-view",
            "selected": view == "judgment_pdf",
            "label": "PDF view",
            "url": get_document_url("full-text-pdf", document),
        },
    ]
