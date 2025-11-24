from caselawclient.models.utilities.aws import upload_asset_to_private_bucket
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.link_generators import build_raise_issue_email_link
from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404


class UploadFileForm(forms.Form):
    # title = forms.CharField(max_length=50)
    file = forms.FileField()


def get_pdf_upload_key(uri):
    """Return the path to the PDF file on S3"""
    return f"{uri}/{uri.replace('/', '_')}.pdf"


class UploadDocumentView(DocumentView):
    template_name = "judgment/upload.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "upload_document"
        context["upload_path"] = get_pdf_upload_key(context["judgment"].uri)
        context["upload_input"] = UploadFileForm()

        return context


class UploadDocumentSuccessView(DocumentView):
    template_name = "judgment/upload-success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email_issue_link"] = build_raise_issue_email_link(
            document=context["document"],
            signature=(self.request.user.get_full_name() if self.request.user.is_authenticated else None),
        )
        context["view"] = "upload_document_success"
        return context


def upload(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    judgment = get_document_by_uri_or_404(judgment_uri)
    s3_key = get_pdf_upload_key(judgment_uri)
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.failure(request, form.errors)
        msg = f"Invalid upload form, {form.errors}"
        raise RuntimeError(msg)
    file = request.FILES["file"]
    upload_data = file.read()  # the bytes of the file
    upload_asset_to_private_bucket(body=upload_data, s3_key=s3_key)
    messages.success(request, "Asset successfully uploaded to {s3_key}")
    return HttpResponseRedirect(
        reverse("upload-document-success", kwargs={"document_uri": judgment.uri}),
    )
