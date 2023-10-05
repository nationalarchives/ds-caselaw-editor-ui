import json

from caselawclient.models.documents import (
    DOCUMENT_STATUS_HOLD,
    DOCUMENT_STATUS_IN_PROGRESS,
    DOCUMENT_STATUS_PUBLISHED,
)
from django.test import TestCase

from judgments.templatetags.document_utils import display_annotation_type
from judgments.templatetags.status_tag_css import status_tag_colour


class TestStatusTagColour:
    def test_colour_in_progress(self):
        assert status_tag_colour(DOCUMENT_STATUS_IN_PROGRESS) == "light-blue"

    def test_colour_published(self):
        assert status_tag_colour(DOCUMENT_STATUS_PUBLISHED) == "green"

    def test_colour_hold(self):
        assert status_tag_colour(DOCUMENT_STATUS_HOLD) == "red"

    def test_colour_undefined(self):
        assert status_tag_colour("undefined") == "grey"


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
