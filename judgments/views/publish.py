from caselawclient.Client import MarklogicResourceNotFoundError
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import escape

from judgments.models.judgments import Judgment
from judgments.utils.aws import invalidate_caches


def publish(request):
    judgment_uri = request.POST.get("judgment_uri", None)

    if not judgment_uri:
        return HttpResponseBadRequest("judgment_uri not provided.")

    try:
        judgment = Judgment(judgment_uri)
        judgment.publish()
        invalidate_caches(judgment.uri)
        messages.success(request, "Judgment published!")
        return HttpResponseRedirect(
            reverse("publish-judgment-success", kwargs={"judgment_uri": judgment.uri})
        )
    except MarklogicResourceNotFoundError:
        return HttpResponseBadRequest(
            escape(f"Judgment {judgment_uri} could not be found.")
        )
