from playwright.sync_api import Page, expect


def test_2fa_page(authenticated_page: Page):
    authenticated_page.goto("/accounts/2fa/")
    authenticated_page.get_by_text("Activate").click()

    expect(authenticated_page.get_by_text("Activate Authenticator App"))
