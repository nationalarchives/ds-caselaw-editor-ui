from django.urls import path

from . import views

urlpatterns = [
    path("edit", views.edit, name="edit"),
    path("detail", views.detail, name="detail"),
    path("update", views.update, name="update"),
    path("results", views.results, name="results"),
    path("", views.index, name="home"),
]
