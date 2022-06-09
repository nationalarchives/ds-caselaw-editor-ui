from django.urls import path

from . import views

urlpatterns = [
    path("edit", views.EditJudgmentView.as_view(), name="edit"),
    path("detail", views.detail, name="detail"),
    path("results", views.results, name="results"),
    path("delete", views.delete, name="delete"),
    path("", views.index, name="home"),
]
