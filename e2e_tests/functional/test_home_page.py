from playwright.sync_api import Page, expect


def test_home_page(authenticated_page: Page):
    expect(authenticated_page).to_have_title("Find and manage case law")
    expect(authenticated_page.get_by_text("655 unpublished documents")).to_be_visible()


def test_home_page_signout(authenticated_page: Page):
    expect(authenticated_page.get_by_role("button", name="Sign out")).to_be_visible()
