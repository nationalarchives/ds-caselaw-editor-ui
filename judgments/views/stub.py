import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from uuid import uuid4

from caselawclient.models.documents.stub import EditorStubData, PartyData, render_stub_xml
from caselawclient.models.documents.versions import VersionAnnotation, VersionType
from caselawclient.models.judgments import Judgment
from caselawclient.types import DocumentURIString
from caselawclient.xml_helpers import DEFAULT_NAMESPACES
from defusedxml import ElementTree
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import validate_email
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView
from ds_caselaw_utils.courts import CourtNotFoundException, courts
from ds_caselaw_utils.types import CourtCode

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

# avoid "<ns0:...>" appearing in XML output
for namespace_name, namespace_uri in DEFAULT_NAMESPACES.items():
    actual_namespace_name = "" if namespace_name == "akn" else namespace_name
    # register namespace does not exist on defusedxml, unhelpfully.
    ET.register_namespace(actual_namespace_name, namespace_uri)


def is_valid_court(court_code):
    try:
        _court = courts.get_court_by_code(CourtCode(court_code.upper()))
    except CourtNotFoundException as error:
        msg = f"Court code {court_code} not recognised"
        raise ValidationError(msg) from error


class GovukDateInputWidgetBase(forms.Widget):
    def decompress(self, value):
        if isinstance(value, (date, datetime)):
            return value.day, value.month, value.year
        if isinstance(value, str) and value:
            try:
                d = datetime.strptime(value[:10], "%Y-%m-%d")
            except ValueError:
                pass
            else:
                return d.day, d.month, d.year
        return None, None, None

    def render(self, name, value, attrs=None, renderer=None):
        return ""


class GovukDateInputWidget(GovukDateInputWidgetBase):
    def value_from_datadict(self, data, files, name):
        day = data.get(f"{name}-day", "").zfill(2)
        month = data.get(f"{name}-month", "").zfill(2)
        year = data.get(f"{name}-year", "")
        if day and month and year:
            return f"{year}-{month}-{day}"
        return None


class GovukDateTimeInputWidget(GovukDateInputWidgetBase):
    format = "%Y-%m-%dT%H:%M:%SZ"

    def value_from_datadict(self, data, files, name):
        day = data.get(f"{name}-day", "").zfill(2)
        month = data.get(f"{name}-month", "").zfill(2)
        year = data.get(f"{name}-year", "")
        if day and month and year:
            return f"{year}-{month}-{day}T00:00:00Z"
        return None

    def format_value(self, value):
        if isinstance(value, datetime):
            return value.strftime(self.format)
        return value


class GovukDateField(forms.DateField):
    widget = GovukDateInputWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", ["%Y-%m-%d"])
        super().__init__(*args, **kwargs)


class GovukDateTimeField(forms.DateTimeField):
    widget = GovukDateTimeInputWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("input_formats", ["%Y-%m-%dT%H:%M:%SZ"])
        super().__init__(*args, **kwargs)


class StubForm(forms.Form):
    # Django form for display
    email_received_at = GovukDateTimeField(
        label="Email date",
        error_messages={
            "required": "Enter the date of the email",
        },
    )
    source_name = forms.CharField(
        label="Submitter name",
        error_messages={
            "required": "Enter the full submitter name",
        },
    )
    source_email = forms.CharField(
        label="Submitter email",
        validators=[validate_email],
        error_messages={
            "required": "Enter the submitter email address",
        },
    )
    decision_date = GovukDateField(
        label="Decision date",
        error_messages={
            "required": "Enter the date of the court decision",
        },
    )
    court_code = forms.ChoiceField(
        label="Court code",
        validators=[is_valid_court],
        error_messages={
            "required": "Select the court code",
        },
    )
    title = forms.CharField(
        label="Title",
        max_length=100,
        widget=forms.TextInput(attrs={"size": 50}),
        error_messages={
            "required": "Enter the title of the case",
        },
    )
    year = forms.IntegerField(
        label="Year",
        min_value=1001,
        error_messages={
            "required": "Enter the year of the case",
        },
    )
    case_numbers = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Case number(s)",
        max_length=100,
        required=False,
    )
    claimants = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Claimant(s)",
        max_length=100,
        required=False,
    )
    appellants = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Appellant(s)",
        max_length=100,
        required=False,
    )
    respondents = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Respondent(s)",
        max_length=100,
        required=False,
    )
    defendants = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label="Defendant(s)",
        max_length=100,
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide colons from field names
        for field in self.fields.values():
            field.label_suffix = ""
        court_choices = courts.get_all(with_jurisdictions=True)
        court_field = self.fields["court_code"]
        if isinstance(court_field, forms.ChoiceField):
            court_field.choices = [("", "Select a court")] + [(court.code, court.name) for court in court_choices]


class CreateStubView(TemplateView):
    template_engine = "jinja"
    template_name = "judgment/stub.jinja"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["view"] = "create_stub"
        context["form"] = StubForm()
        context["active_navigation_endpoint"] = "stub"
        return context


def list_from_string(s):
    return [line.strip() for line in s.split("\n") if line.strip()]


def create_stub(request):
    if not (user_is_superuser(request.user) or user_is_editor(request.user)):
        msg = "Only superusers and editors can create documents"
        raise PermissionDenied(msg)

    stub_form = StubForm(request.POST)
    if not stub_form.is_valid():
        messages.error(request, str(stub_form.errors))
        return render(
            request,
            "judgment/stub.jinja",
            {
                "view": "create_stub",
                "form": stub_form,
            },
            using="jinja",
        )

    case_numbers = list_from_string(stub_form["case_numbers"].value())
    claimants = list_from_string(stub_form["claimants"].value())
    respondents = list_from_string(stub_form["respondents"].value())
    appellants = list_from_string(stub_form["appellants"].value())
    defendants = list_from_string(stub_form["defendants"].value())

    parties = (
        [PartyData(role="Claimant", name=claimant) for claimant in claimants]
        + [PartyData(role="Respondent", name=respondent) for respondent in respondents]
        + [PartyData(role="Appellant", name=appellant) for appellant in appellants]
        + [PartyData(role="Defendant", name=defendant) for defendant in defendants]
    )

    stub_data = EditorStubData(
        {
            "decision_date": stub_form["decision_date"].value(),
            "transform_datetime": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S"),
            "court_code": stub_form["court_code"].value().upper(),
            "title": stub_form["title"].value(),
            "year": str(stub_form["year"].value()),
            "case_numbers": case_numbers,
            "parties": parties,
        },
    )

    document_uri = DocumentURIString("d-" + str(uuid4()))
    rendered_stub = render_stub_xml(stub_data)

    element = ElementTree.fromstring(rendered_stub)

    # create document in Marklogic
    api_client.insert_document_xml(
        document_uri=document_uri,
        document_xml=element,
        document_type=Judgment,
        annotation=ANNOTATION,
    )
    api_client.set_property(document_uri, "source-name", stub_form["source_name"].value())
    api_client.set_property(document_uri, "source-email", stub_form["source_email"].value())
    api_client.set_property(document_uri, "email-received-at", stub_form["email_received_at"].value())

    messages.success(
        request,
        f"Added stub to {document_uri}",
    )

    return HttpResponseRedirect(f"/{document_uri}/upload")
