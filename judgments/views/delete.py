from caselawclient.Client import api_client
from django.contrib import messages
from django.http import HttpResponse
from django.template import loader
from django.utils.translation import gettext

from judgments.utils.aws import delete_documents
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


def delete(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    context = {
        "judgment_uri": judgment_uri,
        "page_title": gettext("judgment.delete_a_judgment"),
    }

    judgment = get_judgment_by_uri_or_404(judgment_uri)
    api_client.delete_judgment(judgment.uri)
    delete_documents(judgment.uri)

    template = loader.get_template("judgment/deleted.html")

    messages.success(request, "Document deleted.")
    return HttpResponse(template.render(context, request))
