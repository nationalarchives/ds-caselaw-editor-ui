from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot


def test_login_page(page: Page):
    page.goto("/")

    expect(page).to_have_title("Find and manage case law")
    expect(page.locator("h1", has_text="Sign in to Find Case Law")).to_be_visible()

    assert_matches_snapshot(page, "login_page")
