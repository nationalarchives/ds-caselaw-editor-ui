from playwright.sync_api import Page

from .utils.assertions import assert_matches_snapshot

JUDGMENT_URI = "/eat/2023/1"


def test_judgment_review(authenticated_page: Page):
    authenticated_page.goto(JUDGMENT_URI)
    assert_matches_snapshot(authenticated_page, "judgment_page")


def test_judgment_identifiers(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/identifiers")
    assert_matches_snapshot(authenticated_page, "judgment_identifiers_page")


def test_judgment_history(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/history")
    assert_matches_snapshot(authenticated_page, "judgment_history_page")


def test_judgment_downloads(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/downloads")
    assert_matches_snapshot(authenticated_page, "judgment_downloads_page")


def test_judgment_upload(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/upload")
    assert_matches_snapshot(authenticated_page, "judgment_upload_page")


def test_judgment_hold(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/upload")
    assert_matches_snapshot(authenticated_page, "judgment_upload_page")


def test_judgment_delete(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/delete")
    assert_matches_snapshot(authenticated_page, "judgment_delete_page")


def test_judgment_onhold(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/onhold")
    assert_matches_snapshot(authenticated_page, "judgment_onhold_page")


def test_judgment_publish(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/publish")
    assert_matches_snapshot(authenticated_page, "judgment_publish_page")


def test_judgment_published(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/published")
    assert_matches_snapshot(authenticated_page, "judgment_published_page")


def test_judgment_unheld(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/unheld")
    assert_matches_snapshot(authenticated_page, "judgment_unheld_page")


def test_judgment_unhold(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/unhold")
    assert_matches_snapshot(authenticated_page, "judgment_unhold_page")


def test_judgment_unpublish(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/unpublish")
    assert_matches_snapshot(authenticated_page, "judgment_unpublish_page")


def test_judgment_unpublished(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/unpublished")
    assert_matches_snapshot(authenticated_page, "judgment_unpublished_page")


def test_judgment_uploaded(authenticated_page: Page):
    authenticated_page.goto(f"{JUDGMENT_URI}/uploaded")
    assert_matches_snapshot(authenticated_page, "judgment_uploaded_page")
