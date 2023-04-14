from caselawclient.models.judgments import (
    JUDGMENT_STATUS_HOLD,
    JUDGMENT_STATUS_IN_PROGRESS,
    JUDGMENT_STATUS_PUBLISHED,
)

from judgments.templatetags.status_tag_css import status_tag_colour


class TestStatusTagColour:
    def test_colour_in_progress(self):
        assert status_tag_colour(JUDGMENT_STATUS_IN_PROGRESS) == "light-blue"

    def test_colour_published(self):
        assert status_tag_colour(JUDGMENT_STATUS_PUBLISHED) == "green"

    def test_colour_hold(self):
        assert status_tag_colour(JUDGMENT_STATUS_HOLD) == "red"

    def test_colour_undefined(self):
        assert status_tag_colour("undefined") == "grey"
