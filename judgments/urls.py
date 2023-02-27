from django.urls import path

from .views.button_handlers import (
    assign_judgment_button,
    hold_judgment_button,
    prioritise_judgment_button,
)
from .views.delete import delete
from .views.detail_xml import detail_xml
from .views.edit_judgment import EditJudgmentView
from .views.full_text import html_view
from .views.index import index
from .views.results import results
from .views.signed_asset import redirect_to_signed_asset
from .views.unlock import unlock

urlpatterns = [
    path("edit", EditJudgmentView.as_view(), name="edit"),
    path("detail", html_view, name="full-text-html"),
    path("xml", detail_xml, name="detail_xml"),
    path("results", results, name="results"),
    # buttons that do a thing and redirect
    path("delete", delete, name="delete"),
    path("unlock", unlock, name="unlock"),
    path("assign", assign_judgment_button, name="assign"),
    path("prioritise", prioritise_judgment_button, name="prioritise"),
    path("hold", hold_judgment_button, name="hold"),
    # redirect to signed asset URLs
    path("signed-asset/<path:key>", redirect_to_signed_asset, name="signed-asset"),
    path("", index, name="home"),
]
