from django.urls import path

from .views.button_handlers import (
    assign_judgment_button,
    hold_judgment_button,
    prioritise_judgment_button,
)
from .views.delete import delete
from .views.detail import detail
from .views.detail_xml import detail_xml
from .views.edit_judgment import EditJudgmentView
from .views.index import index
from .views.results import results

urlpatterns = [
    path("edit", EditJudgmentView.as_view(), name="edit"),
    path("detail", detail, name="detail"),
    path("xml", detail_xml, name="detail_xml"),
    path("results", results, name="results"),
    # buttons that do a thing and redirect
    path("delete", delete, name="delete"),
    path("assign", assign_judgment_button, name="assign"),
    path("prioritise", prioritise_judgment_button, name="prioritise"),
    path("hold", hold_judgment_button, name="hold"),
    path("", index, name="home"),
]
