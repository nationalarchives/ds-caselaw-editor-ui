from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot


def test_2fa_page(authenticated_page: Page):
    authenticated_page.goto("/accounts/2fa/")

    assert_matches_snapshot(authenticated_page, "2fa_page")

    authenticated_page.get_by_text("Activate").click()
    expect(authenticated_page.get_by_text("Activate Authenticator App"))
