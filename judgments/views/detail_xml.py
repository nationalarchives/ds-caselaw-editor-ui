from django.http import Http404, HttpResponse

from caselawclient.Client import (
    MarklogicResourceNotFoundError,
    api_client,
)

def detail_xml(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    response = HttpResponse(judgment_xml, content_type="application/xml")
    response["Content-Disposition"] = f"attachment; filename={judgment_uri}.xml"
    return response
