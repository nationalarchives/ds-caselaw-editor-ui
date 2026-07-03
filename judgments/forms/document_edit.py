import datetime
from typing import TYPE_CHECKING, Any

from caselawclient.models.identifiers.neutral_citation import NCNValidationException
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Field, Layout
from django import forms
from django.forms import BaseFormSet, formset_factory

if TYPE_CHECKING:
    from caselawclient.models.documents import Document


class DocumentMetadataForm(forms.Form):
    metadata_name = forms.CharField(label="Name", widget=forms.Textarea(attrs={"rows": 2, "id": "metadata_name"}))
    court = forms.CharField(label="Court", widget=forms.TextInput(attrs={"id": "court"}))
    judgment_date = forms.DateField(
        label="Judgment date",
        input_formats=["%d %b %Y"],
        widget=forms.DateInput(format="%d %b %Y", attrs={"id": "judgment_date"}),
        error_messages={
            "invalid": "Enter the judgment date in the format 2 Jan 2024.",
        },
    )

    def __init__(self, *args, court_choices: list[tuple[str, str]] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_choices = court_choices or []
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "metadata_name",
            "court",
            Field("judgment_date", css_class="govuk-input govuk-input--width-10"),
        )

    @classmethod
    def from_document(
        cls,
        document: "Document",
        court_choices: list[tuple[str, str]],
        data: dict[str, Any] | None = None,
    ):
        initial = {
            "metadata_name": document.body.name,
            "court": document.body.court_and_jurisdiction_identifier_string,
            "judgment_date": document.body.document_date_as_date,
        }
        return cls(data=data, initial=initial, court_choices=court_choices)

    @property
    def judgment_date_as_iso(self) -> str:
        judgment_date = self.cleaned_data["judgment_date"]
        if isinstance(judgment_date, datetime.datetime):
            return judgment_date.date().isoformat()
        return judgment_date.isoformat()


class DocumentIdentifierForm(forms.Form):
    uuid = forms.CharField(required=False, widget=forms.HiddenInput)
    type = forms.ChoiceField(label="Type", required=False)
    value = forms.CharField(label="Identifier value", max_length=100, required=False)
    deprecated = forms.BooleanField(label="Deprecated", required=False)

    def __init__(self, *args, type_choices=None, identifier_type_map=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.identifier_type_map = identifier_type_map or {}
        self.fields["type"].choices = type_choices or []

        if self.initial.get("uuid"):
            self.fields["type"].widget = forms.HiddenInput()

        self.fields["type"].widget.attrs.update({"class": "govuk-select"})
        self.fields["value"].widget.attrs.update({"class": "govuk-input"})

    @property
    def is_existing_identifier(self) -> bool:
        return bool(self.initial.get("uuid") or self.data.get(f"{self.prefix}-uuid"))

    @property
    def type_label(self) -> str:
        namespace = self.initial.get("type") or self.data.get(f"{self.prefix}-type")
        identifier_type = self.identifier_type_map.get(namespace)
        return identifier_type.schema.name if identifier_type else namespace

    def clean(self):
        cleaned_data = super().clean()

        if self._should_validate_identifier(cleaned_data):
            self._validate_identifier(cleaned_data)

        return cleaned_data

    def _should_validate_identifier(self, cleaned_data):
        if cleaned_data.get("DELETE"):
            return False

        return self.has_changed() or self.is_existing_identifier

    def _validate_identifier(self, cleaned_data):
        namespace = cleaned_data.get("type")
        value = cleaned_data.get("value")

        if not namespace:
            self.add_error("type", "Select an identifier type.")
            return

        if not value:
            self.add_error("value", "Enter an identifier value.")
            return

        identifier_type = self.identifier_type_map.get(namespace)

        if identifier_type is None:
            self.add_error("type", "Invalid identifier type selected.")
            return

        try:
            identifier_valid_value = identifier_type.schema.validate_identifier_value(value)
        except NCNValidationException as e:
            self.add_error("value", str(e))
            return

        if identifier_valid_value is False:
            self.add_error(
                "value",
                f'Identifier value "{value}" is not valid according to the {identifier_type.schema.name} schema.',
            )


class BaseDocumentIdentifierFormSet(BaseFormSet):
    def __init__(self, *args, document: "Document", **kwargs):
        self.document = document
        self.existing_identifier_type_map = {
            identifier.schema.namespace: type(identifier) for identifier in document.identifiers.by_score()
        }
        self.new_identifier_type_map = {
            identifier_type.schema.namespace: identifier_type
            for identifier_type in document.identifiers.valid_new_identifier_types(type(document))
        }
        self.identifier_type_map = {
            **self.existing_identifier_type_map,
            **self.new_identifier_type_map,
        }
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["identifier_type_map"] = self.identifier_type_map
        kwargs["type_choices"] = self.get_type_choices(index)
        return kwargs

    def get_type_choices(self, index):
        if index is not None and index < len(self.initial):
            namespace = self.initial[index]["type"]
            identifier_type = self.identifier_type_map[namespace]
            return [(namespace, identifier_type.schema.name)]

        return [
            ("", "Select an identifier type"),
            *[
                (identifier_type.schema.namespace, identifier_type.schema.name)
                for identifier_type in self.new_identifier_type_map.values()
            ],
        ]

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        deleted_forms = getattr(self, "deleted_forms", [])
        if deleted_forms and self.document.has_ever_been_published:
            error_message = f"Document {self.document.uri} has been published; identifiers cannot be deleted."

            raise forms.ValidationError(
                error_message,
            )


DocumentIdentifierFormSet = formset_factory(
    DocumentIdentifierForm,
    formset=BaseDocumentIdentifierFormSet,
    can_delete=True,
    extra=1,
)


def get_court_choices(courts) -> list[tuple[str, str]]:
    return [(court.code, court.name) for court in courts]


def get_identifier_formset_initial(document: "Document") -> list[dict[str, Any]]:
    return [
        {
            "uuid": identifier.uuid,
            "type": identifier.schema.namespace,
            "value": identifier.value,
            "deprecated": identifier.deprecated,
        }
        for identifier in document.identifiers.by_score()
    ]


def build_document_edit_forms(document: "Document", courts, data=None):
    court_choices = get_court_choices(courts)
    document_edit_form = DocumentMetadataForm.from_document(document, court_choices, data=data)
    return {
        "document_edit_form": document_edit_form,
        "document_form": document_edit_form,
        "identifier_formset": DocumentIdentifierFormSet(
            data=data,
            initial=get_identifier_formset_initial(document),
            document=document,
            prefix="identifiers",
        ),
    }
