from caselawclient.Client import (
    MarklogicResourceNotFoundError,
    MarklogicResourceUnmanagedError,
    api_client,
)
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext
from django.views.decorators.http import require_http_methods

from judgments.models.judgments import Judgment


@require_http_methods(["POST", "GET", "HEAD"])
def unlock(request):
    """Unlock a judgment"""
    if request.method == "POST":
        return unlock_post(request)
    else:
        return unlock_get(request)


def unlock_get(request):
    """Confirmation screen for unlocking"""
    judgment_uri = request.GET["judgment_uri"]
    context = {
        "judgment_uri": judgment_uri,
        "page_title": gettext("judgment.unlock_judgment_title"),
    }
    template = loader.get_template("judgment/confirm-unlock.html")
    return HttpResponse(template.render(context, request))


def unlock_post(request):
    """Unlock the judgment in Marklogic and return to edit judgment"""

    judgment_uri = request.POST.get("judgment_uri")
    try:
        judgment = Judgment(judgment_uri)
        api_client.break_checkout(judgment.uri)
    except MarklogicResourceUnmanagedError as exc:
        raise Http404(
            f"Resource Unmanaged: Judgment '{judgment_uri}' might not exist."
        ) from exc
    except MarklogicResourceNotFoundError as exc:
        raise Http404(
            f"Resource Not Found: Judgment '{judgment_uri}' was not found."
        ) from exc
    else:
        messages.success(request, "Judgment unlocked.")
        return redirect(reverse("edit-judgment", kwargs={"judgment_uri": judgment.uri}))
