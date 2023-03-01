from urllib.parse import urlencode

from caselawclient.Client import MarklogicResourceNotFoundError
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse

from judgments.models import Judgment
from judgments.utils import extract_version


def html_view(request, judgment_uri):
    params = request.GET
    version_uri = params.get("version_uri", None)

    try:
        judgment = Judgment(judgment_uri)
        context = {"judgment_uri": judgment_uri, "judgment": judgment}

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
    template = loader.get_template("judgment/full_text_html.html")
    return HttpResponse(template.render({"context": context}, request))


def xml_view(request, judgment_uri):
    try:
        judgment = Judgment(judgment_uri)
        judgment_xml = judgment.content_as_xml()
    except MarklogicResourceNotFoundError as e:
        raise Http404(f"Judgment was not found at uri {judgment_uri}, {e}")

    response = HttpResponse(judgment_xml, content_type="application/xml")
    response["Content-Disposition"] = f"attachment; filename={judgment_uri}.xml"
    return response


def html_view_redirect(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    version_uri = params.get("version_uri", None)

    redirect_path = reverse("full-text-html", kwargs={"judgment_uri": judgment_uri})

    if version_uri:
        redirect_path = (
            redirect_path
            + "?"
            + urlencode(
                {
                    "version_uri": version_uri,
                }
            )
        )

    return HttpResponseRedirect(redirect_path)


def xml_view_redirect(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    return HttpResponseRedirect(
        reverse("full-text-xml", kwargs={"judgment_uri": judgment_uri})
    )
