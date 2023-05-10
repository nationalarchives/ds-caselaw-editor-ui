from unittest.mock import patch

import pytest
from caselawclient.errors import JudgmentNotFoundError
from django.http import Http404
from factories import JudgmentFactory

from judgments.utils.view_helpers import get_judgment_by_uri_or_404


class TestGetPublishedJudgment:
    @patch("judgments.utils.view_helpers.get_judgment_by_uri")
    def test_published_judgment_returns(self, mock_judgment):
        judgment = JudgmentFactory.build(is_published=True)
        mock_judgment.return_value = judgment
        assert get_judgment_by_uri_or_404("2022/eat/1") == judgment

    @patch("judgments.utils.view_helpers.get_judgment_by_uri")
    def test_unpublished_judgment_returns(self, mock_judgment):
        judgment = JudgmentFactory.build(is_published=False)
        mock_judgment.return_value = judgment
        assert get_judgment_by_uri_or_404("2022/eat/1") == judgment

    @patch(
        "judgments.utils.view_helpers.get_judgment_by_uri",
        side_effect=JudgmentNotFoundError,
    )
    def test_judgment_missing(self, mock_judgment):
        with pytest.raises(Http404):
            get_judgment_by_uri_or_404("not-a-judgment")
