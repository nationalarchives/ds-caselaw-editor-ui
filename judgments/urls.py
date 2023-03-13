from django.urls import path

from .views.button_handlers import (
    assign_judgment_button,
    hold_judgment_button,
    prioritise_judgment_button,
)
from .views.delete import delete
from .views.edit_judgment import (
    EditJudgmentView,
    PublishJudgmentSuccessView,
    PublishJudgmentView,
    edit_view_redirect,
)
from .views.full_text import (
    html_view,
    html_view_redirect,
    pdf_view,
    xml_view,
    xml_view_redirect,
)
from .views.index import index
from .views.labs import Labs
from .views.publish import publish
from .views.results import results
from .views.signed_asset import redirect_to_signed_asset
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
    path("delete", delete, name="delete"),
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
    # Different views on judgments
    path("<path:judgment_uri>/edit", EditJudgmentView.as_view(), name="edit-judgment"),
    path(
        "<path:judgment_uri>/publish",
        PublishJudgmentView.as_view(),
        name="publish-judgment",
    ),
    path(
        "<path:judgment_uri>/publish-success",
        PublishJudgmentSuccessView.as_view(),
        name="publish-judgment-success",
    ),
    path("<path:judgment_uri>/pdf", pdf_view, name="full-text-pdf"),
    path("<path:judgment_uri>/xml", xml_view, name="full-text-xml"),
    # This 'bare judgment' URL must always go last
    path("<path:judgment_uri>", html_view, name="full-text-html"),
]
