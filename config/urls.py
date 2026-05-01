from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from django.views.generic.base import TemplateView

from judgments.accounts.views import (
    LoginView,
    PasswordResetDoneView,
    PasswordResetFromKeyDoneView,
    PasswordResetFromKeyView,
    PasswordResetView,
)

from . import views

urlpatterns = [
    path(
        "check",
        views.CheckView.as_view(),
        name="check",
    ),
    path("accounts/login/", LoginView.as_view(), name="account_login"),
    path(
        "accounts/password/reset/",
        PasswordResetView.as_view(),
        name="account_reset_password",
    ),
    path(
        "accounts/password/reset/done/",
        PasswordResetDoneView.as_view(),
        name="account_reset_password_done",
    ),
    path(
        "accounts/password/reset/key/<uidb36>/<key>/",
        PasswordResetFromKeyView.as_view(),
        name="account_reset_password_from_key",
    ),
    path(
        "accounts/password/reset/key/done/",
        PasswordResetFromKeyDoneView.as_view(),
        name="account_reset_password_from_key_done",
    ),
    path("accounts/", include("allauth.urls")),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # Your stuff: custom urls includes go here
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    path("favicon.ico", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
    path("", include("judgments.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
