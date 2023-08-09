from urllib.parse import urlencode

from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.urls import reverse

from judgments.utils import extract_version
from judgments.utils.view_helpers import get_document_by_uri_or_404

from ..utils.view_helpers import DocumentView


class DocumentReviewHTMLView(DocumentView):
    template_name = "judgment/full_text_html.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        version_uri = self.request.GET.get("version_uri", None)

        if not context["document"].failed_to_parse:
            context["document_html_content"] = context["document"].content_as_html(
                version_uri=version_uri
            )

        if version_uri:
            context["version"] = extract_version(version_uri)

        context["view"] = "judgment_text"

        return context


class DocumentReviewPDFView(DocumentView):
    template_name = "judgment/full_text_pdf.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if not context["document"].pdf_url:
            raise Http404(
                f"Document \"{context['document'].name}\" does not have a PDF."
            )

        version_uri = self.request.GET.get("version_uri", None)

        if version_uri:
            context["version"] = extract_version(version_uri)

        context["view"] = "judgment_text"

        return context


def xml_view(request, document_uri):
    document = get_document_by_uri_or_404(document_uri)
    document_xml = document.content_as_xml

    response = HttpResponse(document_xml, content_type="application/xml")
    response["Content-Disposition"] = f"attachment; filename={document.uri}.xml"
    return response


def html_view_redirect(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    version_uri = params.get("version_uri", None)

    redirect_path = reverse("full-text-html", kwargs={"document_uri": judgment_uri})

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
        reverse("full-text-xml", kwargs={"document_uri": judgment_uri})
    )
