from django.test import TestCase

from judgments.views.document_identifiers import AddIdentifierForm


class TestAddIdentifierForm(TestCase):
    def setUp(self):
        self.type_choices = [
            ("namespace1", "Type 1"),
            ("namespace2", "Type 2"),
        ]

    def test_valid_data(self):
        form = AddIdentifierForm(
            data={
                "type": "namespace1",
                "value": "ID123",
                "deprecated": False,
            },
            type_choices=self.type_choices,
        )
        assert form.is_valid() is True
        assert form.cleaned_data["type"] == "namespace1"
        assert form.cleaned_data["value"] == "ID123"
        assert form.cleaned_data["deprecated"] is False

    def test_missing_value(self):
        form = AddIdentifierForm(
            data={
                "type": "namespace1",
                "value": "",
                "deprecated": False,
            },
            type_choices=self.type_choices,
        )
        assert form.is_valid() is False
        assert "value" in form.errors

    def test_invalid_type(self):
        form = AddIdentifierForm(
            data={
                "type": "invalid_namespace",
                "value": "ID123",
                "deprecated": False,
            },
            type_choices=self.type_choices,
        )
        assert form.is_valid() is False
        assert "type" in form.errors

    def test_deprecated_checkbox_false_if_not_set(self):
        """When a checkbox is unchecked, forms usually don't provide any value. Check that this defaults to `False`."""
        form = AddIdentifierForm(
            data={
                "type": "namespace2",
                "value": "ID999",
            },
            type_choices=self.type_choices,
        )
        assert form.is_valid() is True
        assert form.cleaned_data["deprecated"] is False
