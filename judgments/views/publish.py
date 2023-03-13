from caselawclient.Client import MarklogicResourceNotFoundError
from django.contrib import messages
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse

from judgments.models.judgments import Judgment


def publish(request):
    judgment_uri = request.POST.get("judgment_uri", None)

    try:
        judgment = Judgment(judgment_uri)
        judgment.publish()
        messages.success(request, "Judgment published!")
        return HttpResponseRedirect(
            reverse("edit-judgment", kwargs={"judgment_uri": judgment.uri})
        )
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")
