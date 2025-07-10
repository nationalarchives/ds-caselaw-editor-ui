from typing import TYPE_CHECKING

from caselawclient.models.identifiers.neutral_citation import NCNValidationException
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button, Layout
from django import forms
from django.urls import reverse
from django.views.generic import FormView

from judgments.utils.view_helpers import DocumentView, DocumentViewMixin

if TYPE_CHECKING:
    from caselawclient.models.identifiers import Identifier


def identifier_types_to_form_list(identifier_types: list[type["Identifier"]]) -> list[tuple[str, str]]:
    return [(t.schema.namespace, t.schema.name) for t in identifier_types]


class DocumentIdentifiersView(DocumentView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "document_identifiers"

        return context

    template_name = "judgment/identifiers.html"


class AddIdentifierForm(forms.Form):
    def __init__(self, *args, type_choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["type"] = forms.ChoiceField(
            label="Type",
            choices=type_choices or [],
        )
        self.fields["value"] = forms.CharField(label="Identifier Value", max_length=100)
        self.fields["deprecated"] = forms.BooleanField(
            label="Deprecated",
            help_text="Should this identifier be marked as deprecated?",
            required=False,
        )
        self.helper = FormHelper()
        self.helper.layout = Layout("type", "value", "deprecated", Button("submit", "Submit"))


class AddDocumentIdentifierView(DocumentViewMixin, FormView):
    template_name = "judgment/identifiers_add.html"
    form_class = AddIdentifierForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["type_choices"] = identifier_types_to_form_list(
            self.document.identifiers.valid_new_identifier_types(type(self.document)),
        )
        return kwargs

    def form_valid(self, form):
        identifier_namespace = form.cleaned_data["type"]
        identifier_value = form.cleaned_data["value"]
        identifier_deprecated = form.cleaned_data["deprecated"]

        # Get the available identifier types for the document, to check
        identifier_types = self.document.identifiers.valid_new_identifier_types(type(self.document))

        # Find the correct Identifier class by namespace
        identifier_type: type[Identifier] | None = next(
            (t for t in identifier_types if t.schema.namespace == identifier_namespace),
            None,
        )
        if identifier_type is None:
            form.add_error("type", "Invalid identifier type selected.")
            return self.form_invalid(form)

        # Check that the identifier itself is valid
        try:
            identifier_valid_value = identifier_type.schema.validate_identifier_value(identifier_value)
        except NCNValidationException as e:
            form.add_error("value", str(e))
            return self.form_invalid(form)
        if identifier_valid_value is False:
            form.add_error(
                "value",
                f'Identifier value "{identifier_value}" is not valid according to the {identifier_type.schema.name} schema.',
            )
            return self.form_invalid(form)

        # Create a new identifier instance
        new_identifier = identifier_type(value=identifier_value, deprecated=identifier_deprecated)

        # Add it to the identifiers collection
        self.document.identifiers.add(new_identifier)

        # Run identifiers collection validations
        valid, error_messages = self.document.validate_identifiers()
        if not valid:
            for error_message in error_messages:
                form.add_error(None, error_message)
            return self.form_invalid(form)

        # Everything checks out - save the identifiers to the database.
        self.document.save_identifiers()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("document-identifiers", kwargs={"document_uri": self.document.uri})
