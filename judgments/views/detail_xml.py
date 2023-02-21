from caselawclient.Client import MarklogicResourceNotFoundError
from django.http import Http404, HttpResponse

from judgments.models import Judgment


def detail_xml(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    try:
        judgment = Judgment(judgment_uri)
        judgment_xml = judgment.content_as_xml()
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    response = HttpResponse(judgment_xml, content_type="application/xml")
    response["Content-Disposition"] = f"attachment; filename={judgment_uri}.xml"
    return response
