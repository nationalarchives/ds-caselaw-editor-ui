from caselawclient.factories import JudgmentFactory
from django.test import TestCase

from judgments.templatetags.navigation_tags import get_navigation_items


class TestNavigationTags(TestCase):
    def test_get_navigation_items(self):
        judgment = JudgmentFactory.build(is_published=False)

        context = {
            "view": "judgment_html",
            "document": judgment,
        }

        navigation_items = get_navigation_items(context)

        assert navigation_items == [
            {"id": "review", "selected": True, "label": "Review", "url": "/test/2023/123"},
            {"id": "put-on-hold", "selected": False, "label": "Put on hold", "url": "/test/2023/123/hold"},
            {"id": "publish", "selected": False, "label": "Publish", "url": "/test/2023/123/publish"},
            {"id": "identifiers", "selected": False, "label": "Identifiers", "url": "/test/2023/123/identifiers"},
            {"id": "history", "selected": False, "label": "History", "url": "/test/2023/123/history"},
            {"id": "downloads", "selected": False, "label": "Downloads", "url": "/test/2023/123/downloads"},
        ]

    def test_get_navigation_items_published(self):
        judgment = JudgmentFactory.build(is_published=True)

        context = {
            "view": "judgment_html",
            "document": judgment,
        }

        navigation_items = get_navigation_items(context)

        assert not any(item["id"] == "take-off-hold" for item in navigation_items)
        assert not any(item["id"] == "put-on-hold" for item in navigation_items)

    def test_get_navigation_items_selected_pages(self):
        judgment = JudgmentFactory.build(is_published=False)

        base_context = {
            "document": judgment,
        }

        tests = [
            {"expected_selected_id": "review", "view": "judgment_html"},
            {"expected_selected_id": "review", "view": "judgment_pdf"},
            {"expected_selected_id": "history", "view": "document_history"},
            {"expected_selected_id": "publish", "view": "publish_judgment"},
            {"expected_selected_id": "publish", "view": "unpublish_judgment"},
            {"expected_selected_id": "downloads", "view": "document_downloads"},
            {"expected_selected_id": "take-off-hold", "view": "hold_judgment"},
            {"expected_selected_id": "take-off-hold", "view": "unhold_judgment"},
        ]

        for test in tests:
            navigation_items = get_navigation_items({**base_context, "view": test["view"]})

            for item in navigation_items:
                if item["id"] == test["expected_selected_id"]:
                    assert item["selected"] is True

    def test_get_navigation_items_with_associated_documents(self):
        judgment = JudgmentFactory.build(is_published=False)

        context = {
            "view": "associated_documents",
            "document": judgment,
            "linked_document_uri": judgment.uri,
        }

        navigation_items = get_navigation_items(context)

        expected_associated_documents_navigation_item = {
            "id": "associated_documents",
            "selected": True,
            "label": "Associated documents",
            "url": "/test/2023/123/associated-documents",
        }

        assert expected_associated_documents_navigation_item in navigation_items
