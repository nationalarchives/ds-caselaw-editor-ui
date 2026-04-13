from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot


def test_home_page(authenticated_page: Page):
    expect(authenticated_page).to_have_title("Find and manage case law")

    expect(authenticated_page.get_by_text("5694 unpublished documents")).to_be_visible()

    assert_matches_snapshot(authenticated_page, "home_page")


def test_home_page_signout(authenticated_page: Page):
    expect(authenticated_page.get_by_role("button", name="Sign out")).to_be_visible()
