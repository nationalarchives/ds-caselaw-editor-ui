from caselawclient.Client import MarklogicResourceNotFoundError
from django.http import Http404, HttpResponse
from django.template import loader

from judgments.models import Judgment
from judgments.utils import extract_version


def detail(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    version_uri = params.get("version_uri", None)
    judgment = Judgment(judgment_uri)
    context = {"judgment_uri": judgment_uri, "judgment": judgment}

    try:
        if not judgment.is_editable:
            judgment_content = judgment.content_as_xml()
            metadata_name = judgment_uri
        else:
            judgment_content = judgment.content_as_html(version_uri=version_uri)
            metadata_name = judgment.name

        context["judgment_content"] = judgment_content
        context["page_title"] = metadata_name

        if version_uri:
            context["version"] = extract_version(version_uri)
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")
    template = loader.get_template("judgment/detail.html")
    return HttpResponse(template.render({"context": context}, request))
