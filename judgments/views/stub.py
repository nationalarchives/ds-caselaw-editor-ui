from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from judgments.utils.view_helpers import (
    user_is_editor,
    user_is_superuser,
)


class CreateStubView(TemplateView):
    template_name = "judgment/stub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "create_stub"
        return context


def create_stub(request):
    if not (user_is_superuser(request.user) or user_is_editor(request.user)):
        msg = "Only superusers and editors can delete documents"
        raise PermissionDenied(msg)

    name = request.POST.get("name", None)

    messages.success(
        request,
        f"The {name} at URI X was successfully X.",
    )
    return HttpResponseRedirect(reverse("home"))
