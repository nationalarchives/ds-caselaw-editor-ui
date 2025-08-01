import environ
from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot
from .utils.authentication import login_user

environ.Env.read_env()


def test_login_page(page: Page):
    page.goto("/")

    expect(page).to_have_title("Find and manage case law")
    expect(page.locator("h1", has_text="Sign in to Find Case Law")).to_be_visible()

    assert_matches_snapshot(page, "login_page")

    login_user(page)

    assert_matches_snapshot(page, "home_page")

    expect(page.locator("p", has_text="0 unpublished documents")).to_be_visible()
