from caselawclient.Client import MarklogicResourceNotFoundError, api_client
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.template import loader
from django.utils.translation import gettext

from judgments.utils import delete_documents


def delete(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    context = {
        "judgment_uri": judgment_uri,
        "page_title": gettext("judgment.delete_a_judgment"),
    }
    try:
        api_client.delete_judgment(judgment_uri)

        delete_documents(judgment_uri)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    template = loader.get_template("judgment/deleted.html")

    messages.success(request, "Judgment deleted.")
    return HttpResponse(template.render({"context": context}, request))
