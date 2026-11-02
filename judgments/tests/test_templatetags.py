import json
from types import SimpleNamespace
from unittest.mock import patch

from caselawclient.models.documents import (
    DOCUMENT_STATUS_HOLD,
    DOCUMENT_STATUS_IN_PROGRESS,
    DOCUMENT_STATUS_NEW,
    DOCUMENT_STATUS_PUBLISHED,
)
from django.test import TestCase

from judgments.templatetags.document_utils import (
    display_annotation_type,
    get_dict_key_with_hyphen,
    is_current_document_version,
    render_json,
)
from judgments.templatetags.status_tag_css import status_tag
from judgments.templatetags.user_permissions import (
    DOCUMENT_RESTORE_PUBLISHED_DISABLED_REASON,
    get_document_restore_disabled_reason,
    is_document_restore_disabled,
)
from judgments.utils.permissions import editors_only_hint


class TestIsCurrentDocumentVersion:
    def test_highest_version_is_current(self):
        document = SimpleNamespace(versions=[{"version": 2}, {"version": 3}, {"version": 1}])

        assert is_current_document_version(document, 3) is True
        assert is_current_document_version(document, 2) is False

    def test_document_without_versions_has_no_current_version(self):
        document = SimpleNamespace(versions=[])

        assert is_current_document_version(document, 1) is False


class TestDocumentRestoreDisabled:
    @patch("judgments.templatetags.user_permissions.user_can_edit", return_value=True)
    def test_restore_is_enabled_for_editor_when_document_is_unpublished(self, mock_user_can_edit):
        document = SimpleNamespace(is_published=False)
        user = object()

        assert is_document_restore_disabled(document, user) is False
        assert get_document_restore_disabled_reason(document, user) is None
        mock_user_can_edit.assert_called_with(user)

    @patch("judgments.templatetags.user_permissions.user_can_edit", return_value=True)
    def test_restore_is_disabled_when_document_is_published(self, mock_user_can_edit):
        document = SimpleNamespace(is_published=True)
        user = object()

        assert is_document_restore_disabled(document, user) is True
        assert get_document_restore_disabled_reason(document, user) == DOCUMENT_RESTORE_PUBLISHED_DISABLED_REASON
        mock_user_can_edit.assert_not_called()

    @patch("judgments.templatetags.user_permissions.user_can_edit", return_value=False)
    def test_restore_is_disabled_when_user_cannot_edit(self, mock_user_can_edit):
        document = SimpleNamespace(is_published=False)
        user = object()

        assert is_document_restore_disabled(document, user) is True
        assert get_document_restore_disabled_reason(document, user) == editors_only_hint()
        mock_user_can_edit.assert_called_with(user)


class TestStatusTagColour:
    def test_colour_in_progress(self):
        assert status_tag(DOCUMENT_STATUS_IN_PROGRESS) == "in-progress"

    def test_colour_in_progress_editor_status(self):
        assert status_tag("In Progress") == "in-progress"

    def test_colour_published(self):
        assert status_tag(DOCUMENT_STATUS_PUBLISHED) == "published"

    def test_colour_hold(self):
        assert status_tag(DOCUMENT_STATUS_HOLD) == "on-hold"

    def test_colour_hold_editor_status(self):
        assert status_tag("Hold") == "on-hold"

    def test_colour_new(self):
        assert status_tag(DOCUMENT_STATUS_NEW) == "new"

    def test_colour_undefined(self):
        assert status_tag("undefined") == "new"


class TestDisplayAnnotationType(TestCase):
    def test_allows_empty_annotation(self):
        assert display_annotation_type(None) is None

    def test_displays_string_annotation(self):
        annotation = "This is an annotation"
        assert display_annotation_type(annotation) == annotation

    def test_displays_submission_type(self):
        annotation = json.dumps({"type": "submission"})
        assert display_annotation_type(annotation) == "Submitted"

    def test_displays_enrichment_type(self):
        annotation = json.dumps({"type": "enrichment"})
        assert display_annotation_type(annotation) == "Enriched"

    def test_displays_edit_type(self):
        annotation = json.dumps({"type": "edit"})
        assert display_annotation_type(annotation) == "Edited"

    def test_displays_other_type(self):
        version_type = "Another type"
        annotation = json.dumps({"type": version_type})
        assert display_annotation_type(annotation) == version_type

    def test_returns_none_for_json_with_no_type(self):
        annotation = json.dumps({})
        assert display_annotation_type(annotation) is None


class TestRenderJson:
    def test_render_json(self):
        assert (
            render_json({"string": "stringValue", "array": ["one", "two"]})
            == '{\n  "string": "stringValue",\n  "array": [\n    "one",\n    "two"\n  ]\n}'
        )


class TestGetDictKeyWithHyphen:
    def test_when_dict_is_none(self):
        assert get_dict_key_with_hyphen(None, "some-key") == ""

    def test_when_dict_exists(self):
        data = {"some-key": "value"}
        assert get_dict_key_with_hyphen(data, "some-key") == "value"
