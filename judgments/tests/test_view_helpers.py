from unittest.mock import patch

import pytest
from caselawclient.errors import DocumentNotFoundError
from django.http import Http404
from factories import JudgmentFactory

from judgments.utils.view_helpers import get_document_by_uri_or_404


class TestGetDocumentByURIOr404:
    @patch("judgments.utils.view_helpers.api_client.get_document_by_uri")
    def test_published_judgment_returns(self, mock_judgment):
        judgment = JudgmentFactory.build(is_published=True)
        mock_judgment.return_value = judgment
        assert get_document_by_uri_or_404("2022/eat/1") == judgment

    @patch("judgments.utils.view_helpers.api_client.get_document_by_uri")
    def test_unpublished_judgment_returns(self, mock_judgment):
        judgment = JudgmentFactory.build(is_published=False)
        mock_judgment.return_value = judgment
        assert get_document_by_uri_or_404("2022/eat/1") == judgment

    @patch(
        "judgments.utils.view_helpers.api_client.get_document_by_uri",
        side_effect=DocumentNotFoundError,
    )
    def test_judgment_missing(self, mock_judgment):
        with pytest.raises(Http404):
            get_document_by_uri_or_404("not-a-judgment")
