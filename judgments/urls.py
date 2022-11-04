from django.urls import path, re_path

from . import views

urlpatterns = [
    path("edit", views.edit_old, name="edit_old"),
    re_path(r"(?P<judgment_uri>.*/\d{4}/\d+|failures/TDR-\d{4}-\w*)/edit", views.EditJudgmentView.as_view(), name="edit"),
    path("detail", views.detail_old, name="detail_old"),
    re_path(r"(?P<judgment_uri>.*/\d{4}/\d+|failures/TDR-\d{4}-\w*)", views.detail, name="detail"),
    path("xml", views.detail_xml, name="detail_xml"),
    path("results", views.results, name="results"),
    # buttons that do a thing and redirect
    path("delete", views.delete, name="delete"),
    path("assign", views.assign_judgment_button, name="assign"),
    path("prioritise", views.prioritise_judgment_button, name="prioritise"),
    path("hold", views.hold_judgment_button, name="hold"),
    path("", views.index, name="home"),
]
