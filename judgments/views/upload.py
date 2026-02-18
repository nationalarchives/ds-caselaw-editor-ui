from caselawclient.models.utilities.aws import upload_asset_to_private_bucket
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse

from judgments.utils.view_helpers import DocumentView, get_document_by_uri_or_404

MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20 MB


def is_pdf(file):
    header = file.read(4)
    file.seek(0)

    if header != b"%PDF":
        msg = "Uploaded file is not a valid PDF."
        raise ValidationError(msg)


def is_reasonable_size(file):
    if file.size > MAX_UPLOAD_SIZE:
        msg = f"Uploaded file is too large. Maximum size is {int(MAX_UPLOAD_SIZE / (1024 * 1024))} MB."
        raise ValidationError(msg)


class UploadFileForm(forms.Form):
    file = forms.FileField(validators=[is_pdf, is_reasonable_size])


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
        context["view"] = "upload_document_success"
        return context


def upload(request):
    judgment_uri = request.POST.get("judgment_uri", None)
    judgment = get_document_by_uri_or_404(judgment_uri)
    s3_key = get_pdf_upload_key(judgment_uri)
    form = UploadFileForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, str(form.errors))
        return HttpResponseRedirect(
            reverse("document-upload", kwargs={"document_uri": judgment.uri}),
        )

    file = request.FILES["file"]
    upload_data = file.read()  # the bytes of the file
    upload_asset_to_private_bucket(body=upload_data, s3_key=s3_key)
    messages.success(request, "Asset successfully uploaded to {s3_key}")
    return HttpResponseRedirect(
        reverse("upload-document-success", kwargs={"document_uri": judgment.uri}),
    )
