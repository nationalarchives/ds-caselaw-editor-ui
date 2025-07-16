from playwright.sync_api import Page, expect


def test_home_page(page: Page):
    page.goto("/")

    expect(page).to_have_title("Find and manage case law")
    expect(page.locator("h1", has_text="Sign in to Find Case Law")).to_be_visible()
