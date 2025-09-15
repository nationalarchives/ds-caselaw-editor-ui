from typing import TYPE_CHECKING

from caselawclient.models.documents import Document
from caselawclient.models.identifiers.neutral_citation import NCNValidationException
from crispy_forms_gds.helper import FormHelper
from crispy_forms_gds.layout import Button, Layout
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse
from django.views.generic import FormView

from judgments.utils.view_helpers import DocumentView, DocumentViewMixin

if TYPE_CHECKING:
    from caselawclient.models.identifiers import Identifier


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
            help_text="Should this identifier be marked as deprecated, ie the identifier has previously been used for the document but is not longer considered current?",
            required=False,
        )
        self.helper = FormHelper()
        self.helper.layout = Layout("type", "value", "deprecated", Button("submit", "Submit"))


class AddDocumentIdentifierView(DocumentViewMixin, FormView):
    template_name = "judgment/identifiers_add.html"
    form_class = AddIdentifierForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["view"] = "document_identifiers"

        return context

    def _identifier_types_to_form_list(self, identifier_types: list[type["Identifier"]]) -> list[tuple[str, str]]:
        """Given a list of identifier types, unpack them into tuples suitable for the form."""
        return [(t.schema.namespace, t.schema.name) for t in identifier_types]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["type_choices"] = self._identifier_types_to_form_list(
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

        messages.success(
            self.request,
            f'New {identifier_type.schema.name} with value "{identifier_value}" added successfully!',
        )

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("document-identifiers", kwargs={"document_uri": self.document.uri})


class DeleteIdentifierForm(forms.Form):
    def __init__(self, *args, type_choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(Button.warning("submit", "Delete"))


def check_safe_to_delete_identifier(document: Document, identifier_uuid: str):
    if document.has_ever_been_published:
        msg = f"Document {document.uri} has previously been published; identifiers cannot be deleted."
        raise PermissionDenied(
            msg,
        )

    if identifier_uuid not in document.identifiers:
        msg = f'Identifier "{identifier_uuid}" does not exist in {document.uri}.'
        raise Http404(
            msg,
        )


class DeleteDocumentIdentifierView(DocumentViewMixin, FormView):
    template_name = "judgment/identifier_delete.html"
    form_class = DeleteIdentifierForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        check_safe_to_delete_identifier(self.document, self.kwargs["identifier_uuid"])

        context["view"] = "document_identifiers"
        context["identifier"] = self.document.identifiers[self.kwargs["identifier_uuid"]]

        return context

    def form_valid(self, form):
        check_safe_to_delete_identifier(self.document, self.kwargs["identifier_uuid"])

        identifier = self.document.identifiers[self.kwargs["identifier_uuid"]]

        # Remove the identifier
        del self.document.identifiers[self.kwargs["identifier_uuid"]]

        # Save the identifiers to the database. This runs validations as part of save operations, so if we've ended up here but the result is invalid it won't be committed.
        self.document.save_identifiers()

        messages.success(self.request, f'{identifier.schema.name} with value "{identifier.value}" has been deleted.')

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("document-identifiers", kwargs={"document_uri": self.document.uri})
