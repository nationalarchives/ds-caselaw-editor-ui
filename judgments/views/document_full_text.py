from urllib.parse import urlencode

from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404


class DocumentReviewHTMLView(DocumentView):
    template_name = "judgment/full_text_html.html"

    def dispatch(self, request, *args, **kwargs):
        if self.document.failed_to_parse:
            return super().dispatch(request, args, kwargs)

        if not self.document.content_as_html():
            redirect_path = reverse("full-text-pdf", kwargs={"document_uri": self.document.uri})
            return HttpResponseRedirect(redirect_path)

        return super().dispatch(request, args, kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "judgment_html"

        return context


class DocumentReviewPDFView(DocumentView):
    template_name = "judgment/full_text_pdf.html"

    def dispatch(self, request, *args, **kwargs):
        if not self.document.pdf_url:
            redirect_path = reverse("full-text-html", kwargs={"document_uri": self.document.uri})
            return HttpResponseRedirect(redirect_path)

        return super().dispatch(request, args, kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "judgment_pdf"

        return context


def xml_view(request, document_uri):
    document = get_document_by_uri_or_404(document_uri)
    document_xml = document.body.content_as_xml

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
                },
            )
        )

    return HttpResponseRedirect(redirect_path)


def xml_view_redirect(request):
    params = request.GET
    judgment_uri = params.get("judgment_uri", None)
    return HttpResponseRedirect(
        reverse("full-text-xml", kwargs={"document_uri": judgment_uri}),
    )
