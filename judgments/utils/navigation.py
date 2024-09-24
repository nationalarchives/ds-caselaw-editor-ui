from django.urls import reverse


def get_document_url(view, document):
    return reverse(view, kwargs={"document_uri": document.uri})


def get_hold_navigation_item(view, document):
    if document.is_published:
        return {
            "id": "put-on-hold",
            "selected": view == "hold_judgment",
            "label": "Put on hold",
        }
    elif document.is_held:
        return {
            "id": "take-off-hold",
            "selected": view == "unhold_judgment",
            "label": "Take off hold",
            "url": get_document_url("unhold-document", document),
        }
    else:
        return {
            "id": "put-on-hold",
            "selected": view == "hold_judgment",
            "label": "Put on hold",
            "url": get_document_url("hold-document", document),
        }


def get_publishing_navigation_item(view, document):
    if document.is_published:
        return {
            "id": "unpublish",
            "selected": view == "unpublish_judgment",
            "label": "Unpublish",
            "url": get_document_url("unpublish-document", document),
        }
    else:
        return {
            "id": "publish",
            "selected": view == "publish_judgment",
            "label": "Publish",
            "url": get_document_url("publish-document", document),
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
        "selected": view == "judgment_text",
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


def get_navigation_items(context):
    view, document = context["view"], context["document"]

    return [
        get_review_navigation_item(view, document),
        get_hold_navigation_item(view, document),
        get_publishing_navigation_item(view, document),
        get_history_navigation_item(view, document),
        get_download_navigation_item(view, document),
    ]


def get_view_control_tabs(view, document):
    return [
        {
            "id": "html-view",
            "selected": view == "full-text-html",
            "label": "HTML view",
            "url": get_document_url("full-text-html", document),
        },
        {
            "id": "pdf-view",
            "selected": view == "full-text-pdf",
            "label": "PDF view",
            "url": get_document_url("full-text-pdf", document),
        },
    ]
