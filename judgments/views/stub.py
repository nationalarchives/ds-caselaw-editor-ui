import datetime
from uuid import uuid4

from caselawclient.models.documents.stub import EditorStubData, PartyData, render_stub_xml
from caselawclient.models.documents.versions import VersionAnnotation, VersionType
from caselawclient.models.judgments import Judgment
from caselawclient.types import DocumentURIString
from defusedxml import ElementTree
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView

from judgments.utils import api_client
from judgments.utils.view_helpers import (
    user_is_editor,
    user_is_superuser,
)

ANNOTATION = VersionAnnotation(
    VersionType.SUBMISSION,
    automated=False,
    message="Stub document created",
    payload={},
)


class StubForm(forms.Form):
    # Django form for display
    decision_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label="Decision date",
    )
    # transform_datetime is dynamically generated
    court_code = forms.CharField(label="Court code", max_length=100)
    title = forms.CharField(label="Title", max_length=100)
    year = forms.IntegerField(label="Year", min_value=1001)
    case_numbers = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Case numbers",
        max_length=100,
        required=False,
    )
    claimants = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Claimants", max_length=100)
    appellants = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Appellants", max_length=100)
    respondents = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Respondents", max_length=100)


class CreateStubView(TemplateView):
    template_name = "judgment/stub.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "create_stub"
        context["form"] = StubForm()
        return context


def list_from_string(s):
    return [line.strip() for line in s.split("\n") if line.strip()]


def create_stub(request):
    if not (user_is_superuser(request.user) or user_is_editor(request.user)):
        msg = "Only superusers and editors can create documents"
        raise PermissionDenied(msg)

    stub_form = StubForm(request.POST)
    if not stub_form.is_valid():
        msg = "Invalid form data"
        raise RuntimeError(msg)

    case_numbers = list_from_string(stub_form["case_numbers"].value())
    claimants = list_from_string(stub_form["claimants"].value())
    respondents = list_from_string(stub_form["respondents"].value())
    appellants = list_from_string(stub_form["appellants"].value())
    parties = (
        [PartyData(role="Claimant", name=claimant) for claimant in claimants]
        + [PartyData(role="Respondent", name=respondent) for respondent in respondents]
        + [PartyData(role="Appellant", name=appellant) for appellant in appellants]
    )

    stub_data = EditorStubData(
        {
            "decision_date": stub_form["decision_date"].value(),
            "transform_datetime": datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%dT%H:%M:%S"),
            "court_code": stub_form["court_code"].value().upper(),
            "title": stub_form["title"].value(),
            "year": str(stub_form["year"].value()),
            "case_numbers": case_numbers,
            "parties": parties,
            # "appellants": appellants,
        },
    )

    rendered_stub = render_stub_xml(stub_data)

    document_uri = DocumentURIString("d-" + str(uuid4()))
    element = ElementTree.fromstring(rendered_stub)

    # create document in Marklogic
    api_client.insert_document_xml(
        document_uri=document_uri,
        document_xml=element,
        document_type=Judgment,
        annotation=ANNOTATION,
    )

    messages.success(
        request,
        f"Added stub to {document_uri}",
    )

    # TODO redirect to document_uri
    return HttpResponseRedirect(f"/{document_uri}")
