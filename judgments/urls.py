from django.urls import path

from judgments.views.associated_documents import AssociatedDocumentsView
from judgments.views.delete import DeleteDocumentView, delete
from judgments.views.enrich import enrich

from .views import reports
from .views.components import ComponentsView
from .views.document_downloads import DocumentDownloadsView
from .views.document_full_text import (
    DocumentReviewHTMLView,
    DocumentReviewPDFView,
    html_view_redirect,
    xml_view,
    xml_view_redirect,
)
from .views.document_history import DocumentHistoryView
from .views.document_identifiers import AddDocumentIdentifierView, DocumentIdentifiersView
from .views.document_reparse import reparse
from .views.index import index
from .views.judgment_edit import EditJudgmentView, edit_view_redirect
from .views.judgment_hold import (
    HoldDocumentSuccessView,
    HoldDocumentView,
    UnholdDocumentSuccessView,
    UnholdDocumentView,
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
from .views.stats import Stats, stream_combined_stats_table_as_csv
from .views.style_guide import (
    StyleGuide,
)
from .views.unlock import unlock

urlpatterns = [
    # Home
    path("", index, name="home"),
    # Components
    path(
        "components",
        ComponentsView.as_view(),
        name="components",
    ),
    # Search
    path("results", results, name="results"),
    # redirect to signed asset URLs
    path("signed-asset/<path:key>", redirect_to_signed_asset, name="signed-asset"),
    # Judgment verbs
    path("publish", publish, name="publish"),
    path("unpublish", unpublish, name="unpublish"),
    path("hold", hold, name="hold"),
    path("unhold", unhold, name="unhold"),
    path("delete", delete, name="delete"),
    path("enrich", enrich, name="enrich"),
    path("reparse", reparse, name="reparse"),
    path("unlock", unlock, name="unlock"),
    # Redirects for legacy judgment URIs
    path("edit", edit_view_redirect),
    path("detail", html_view_redirect),
    path("xml", xml_view_redirect),
    # Labs
    path("labs", Labs.as_view(), name="labs"),
    # Reports
    path("reports", reports.Index.as_view(), name="reports"),
    path(
        "reports/awaiting-parse",
        reports.AwaitingParse.as_view(),
        name="report_awaiting_parse",
    ),
    path(
        "reports/awaiting-enrichment",
        reports.AwaitingEnrichment.as_view(),
        name="report_awaiting_enrichment",
    ),
    # Stats
    path("stats", Stats.as_view(), name="stats"),
    path(
        "stats/combined-csv",
        stream_combined_stats_table_as_csv,
        name="stats_combined_csv",
    ),
    # Style guide
    path("style-guide", StyleGuide.as_view(), name="style_guide"),
    # Different views on judgments
    path("<path:document_uri>/delete", DeleteDocumentView.as_view(), name="delete-document"),
    path("<path:document_uri>/associated-documents", AssociatedDocumentsView.as_view(), name="associated-documents"),
    path("<path:document_uri>/edit", EditJudgmentView.as_view(), name="edit-document"),
    path(
        "<path:document_uri>/history",
        DocumentHistoryView.as_view(),
        name="document-history",
    ),
    path(
        "<path:document_uri>/identifiers",
        DocumentIdentifiersView.as_view(),
        name="document-identifiers",
    ),
    path(
        "<path:document_uri>/identifiers/add",
        AddDocumentIdentifierView.as_view(),
        name="document-identifiers-add",
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
        "<path:document_uri>/hold",
        HoldDocumentView.as_view(),
        name="hold-document",
    ),
    path(
        "<path:document_uri>/onhold",
        HoldDocumentSuccessView.as_view(),
        name="hold-document-success",
    ),
    path(
        "<path:document_uri>/unhold",
        UnholdDocumentView.as_view(),
        name="unhold-document",
    ),
    path(
        "<path:document_uri>/unheld",
        UnholdDocumentSuccessView.as_view(),
        name="unhold-document-success",
    ),
    path(
        "<path:document_uri>/pdf",
        DocumentReviewPDFView.as_view(),
        name="full-text-pdf",
    ),
    path(
        "<path:document_uri>/downloads",
        DocumentDownloadsView.as_view(),
        name="document-downloads",
    ),
    path("<path:document_uri>/xml", xml_view, name="full-text-xml"),
    # This 'bare document' URL must always go last
    path(
        "<path:document_uri>",
        DocumentReviewHTMLView.as_view(),
        name="full-text-html",
    ),
]
