from caselawclient.Client import MarklogicResourceNotFoundError, api_client
from django.http import Http404, HttpResponse
from django.template import loader
from requests_toolbelt.multipart import decoder

from judgments.utils import extract_version, get_judgment_root
from judgments.utils.aws import generate_docx_url, generate_pdf_url, uri_for_s3


def detail(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    version_uri = params.get("version_uri", None)
    context = {"judgment_uri": judgment_uri, "is_failure": False}

    try:
        judgment_xml = api_client.get_judgment_xml(judgment_uri, show_unpublished=True)
        judgment_root = get_judgment_root(judgment_xml)
        context["published"] = api_client.get_published(judgment_uri)
        context["is_editable"] = True
        if "failures" in judgment_uri:
            context["is_failure"] = True

        if "error" in judgment_root:
            context["is_editable"] = False
            judgment = judgment_xml
            metadata_name = judgment_uri
        else:
            results = api_client.eval_xslt(
                judgment_uri, version_uri, show_unpublished=True
            )
            metadata_name = api_client.get_judgment_name(judgment_uri)

            multipart_data = decoder.MultipartDecoder.from_response(results)
            judgment = multipart_data.parts[0].text
        context["judgment"] = judgment
        context["page_title"] = metadata_name
        context["docx_url"] = generate_docx_url(uri_for_s3(judgment_uri))
        context["pdf_url"] = generate_pdf_url(uri_for_s3(judgment_uri))

        if version_uri:
            context["version"] = extract_version(version_uri)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")
    template = loader.get_template("judgment/detail.html")
    return HttpResponse(template.render({"context": context}, request))
