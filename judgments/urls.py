from django.urls import path

from .views.button_handlers import (
    assign_judgment_button,
    hold_judgment_button,
    prioritise_judgment_button,
)
from .views.document_history import DocumentHistoryView
from .views.full_text import (
    html_view,
    html_view_redirect,
    pdf_view,
    xml_view,
    xml_view_redirect,
)
from .views.index import index
from .views.judgment_edit import EditJudgmentView, edit_view_redirect
from .views.judgment_hold import (
    HoldJudgmentSuccessView,
    HoldJudgmentView,
    UnholdJudgmentSuccessView,
    UnholdJudgmentView,
    hold,
    unhold,
)
from .views.judgment_publish import (
    PublishDocumentSuccessView,
    PublishDocumentView,
    UnpublishDocumentSuccessView,
    UnpublishDocumentView,
    publish,
    unpublish,
)
from .views.labs import Labs
from .views.results import results
from .views.signed_asset import redirect_to_signed_asset
from .views.style_guide import (
    StyleGuideBranding,
    StyleGuideComponents,
    style_guide_redirect,
)
from .views.unlock import unlock

urlpatterns = [
    # Home
    path("", index, name="home"),
    # Search
    path("results", results, name="results"),
    # redirect to signed asset URLs
    path("signed-asset/<path:key>", redirect_to_signed_asset, name="signed-asset"),
    # Judgment verbs
    path("publish", publish, name="publish"),
    path("unpublish", unpublish, name="unpublish"),
    path("hold", hold, name="hold"),
    path("unhold", unhold, name="unhold"),
    path("unlock", unlock, name="unlock"),
    path("assign", assign_judgment_button, name="assign"),
    path("prioritise", prioritise_judgment_button, name="prioritise"),
    path("hold", hold_judgment_button, name="hold"),
    # Redirects for legacy judgment URIs
    path("edit", edit_view_redirect),
    path("detail", html_view_redirect),
    path("xml", xml_view_redirect),
    # Labs
    path("labs", Labs.as_view(), name="labs"),
    path("style_guide", style_guide_redirect, name="style_guide"),
    path(
        "style_guide/components",
        StyleGuideComponents.as_view(),
        name="style_guide_components",
    ),
    path(
        "style_guide/branding",
        StyleGuideBranding.as_view(),
        name="style_guide_branding",
    ),
    # Different views on judgments
    path("<path:judgment_uri>/edit", EditJudgmentView.as_view(), name="edit-judgment"),
    path(
        "<path:document_uri>/history",
        DocumentHistoryView.as_view(),
        name="document-history",
    ),
    path(
        "<path:document_uri>/publish",
        PublishDocumentView.as_view(),
        name="publish-document",
    ),
    path(
        "<path:document_uri>/published",
        PublishDocumentSuccessView.as_view(),
        name="publish-document-success",
    ),
    path(
        "<path:document_uri>/unpublish",
        UnpublishDocumentView.as_view(),
        name="unpublish-document",
    ),
    path(
        "<path:document_uri>/unpublished",
        UnpublishDocumentSuccessView.as_view(),
        name="unpublish-document-success",
    ),
    path(
        "<path:judgment_uri>/hold",
        HoldJudgmentView.as_view(),
        name="hold-judgment",
    ),
    path(
        "<path:judgment_uri>/onhold",
        HoldJudgmentSuccessView.as_view(),
        name="hold-judgment-success",
    ),
    path(
        "<path:judgment_uri>/unhold",
        UnholdJudgmentView.as_view(),
        name="unhold-judgment",
    ),
    path(
        "<path:judgment_uri>/unheld",
        UnholdJudgmentSuccessView.as_view(),
        name="unhold-judgment-success",
    ),
    path("<path:judgment_uri>/pdf", pdf_view, name="full-text-pdf"),
    path("<path:judgment_uri>/xml", xml_view, name="full-text-xml"),
    # This 'bare judgment' URL must always go last
    path("<path:judgment_uri>", html_view, name="full-text-html"),
]
