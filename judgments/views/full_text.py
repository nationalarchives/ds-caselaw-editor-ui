from urllib.parse import urlencode

import ds_caselaw_utils as caselawutils
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse

from judgments.utils import extract_version
from judgments.utils.view_helpers import get_judgment_by_uri_or_404


def html_view(request, judgment_uri):
    params = request.GET
    version_uri = params.get("version_uri", None)

    judgment = get_judgment_by_uri_or_404(judgment_uri)
    context = {
        "judgment_uri": judgment_uri,
        "judgment": judgment,
        "courts": caselawutils.courts.get_all(),
    }

    press_summary_suffix = "/press-summary/1"
    if judgment_uri.endswith(press_summary_suffix):
        context["document_type"] = "press_summary"
        context["linked_document_uri"] = judgment_uri.removesuffix(press_summary_suffix)

    else:
        context["document_type"] = "judgment"
        context["linked_document_uri"] = judgment_uri + press_summary_suffix

    if not judgment.is_editable:
        judgment_content = judgment.content_as_xml()
        metadata_name = judgment_uri
    else:
        judgment_content = judgment.content_as_html(version_uri=version_uri)
        metadata_name = judgment.name

    context["judgment_content"] = judgment_content
    context["page_title"] = metadata_name
    context["view"] = "judgment_text"

    if version_uri:
        context["version"] = extract_version(version_uri)

    template = loader.get_template("judgment/full_text_html.html")
    return HttpResponse(template.render(context, request))


def pdf_view(request, judgment_uri):
    params = request.GET
    version_uri = params.get("version_uri", None)

    judgment = get_judgment_by_uri_or_404(judgment_uri)
    if not judgment.pdf_url:
        raise Http404(f'Document "{judgment.name}" does not have a PDF.')

    context = {
        "judgment_uri": judgment_uri,
        "judgment": judgment,
        "page_title": judgment.name,
        "view": "judgment_text",
    }

    press_summary_suffix = "/press-summary/1"
    if judgment_uri.endswith(press_summary_suffix):
        context["document_type"] = "press_summary"
        context["linked_document_uri"] = judgment_uri.removesuffix(press_summary_suffix)

    else:
        context["document_type"] = "judgment"
        context["linked_document_uri"] = judgment_uri + press_summary_suffix

    if version_uri:
        context["version"] = extract_version(version_uri)

    template = loader.get_template("judgment/full_text_pdf.html")
    return HttpResponse(
        template.render(
            context,
            request,
        )
    )


def xml_view(request, judgment_uri):
    judgment = get_judgment_by_uri_or_404(judgment_uri)
    judgment_xml = judgment.content_as_xml()

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
