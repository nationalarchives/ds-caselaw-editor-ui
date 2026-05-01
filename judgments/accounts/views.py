from allauth.account import views


class JinjaTemplateEngineMixin:
    template_engine = "jinja"


class LoginView(JinjaTemplateEngineMixin, views.LoginView):
    pass


class PasswordResetView(JinjaTemplateEngineMixin, views.PasswordResetView):
    pass


class PasswordResetDoneView(JinjaTemplateEngineMixin, views.PasswordResetDoneView):
    pass


class PasswordResetFromKeyView(JinjaTemplateEngineMixin, views.PasswordResetFromKeyView):
    pass


class PasswordResetFromKeyDoneView(JinjaTemplateEngineMixin, views.PasswordResetFromKeyDoneView):
    pass
