from django.urls import path

from . import views

urlpatterns = [
    path("edit", views.EditJudgmentView.as_view(), name="edit"),
    path("detail", views.detail, name="detail"),
    path("xml", views.detail_xml, name="detail_xml"),
    path("results", views.results, name="results"),
    path("delete", views.delete, name="delete"),
    path("assign", views.assign_judgment_button, name="assign"),
    path("", views.index, name="home"),
]
