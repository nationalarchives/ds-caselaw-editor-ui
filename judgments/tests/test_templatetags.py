import json

from caselawclient.models.documents import (
    DOCUMENT_STATUS_HOLD,
    DOCUMENT_STATUS_IN_PROGRESS,
    DOCUMENT_STATUS_NEW,
    DOCUMENT_STATUS_PUBLISHED,
)
from django.test import TestCase

from judgments.templatetags.document_utils import display_annotation_type, render_json
from judgments.templatetags.status_tag_css import status_tag


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
