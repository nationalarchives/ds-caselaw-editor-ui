import re

from playwright.sync_api import Page, expect


def test_judgment_list(authenticated_page: Page):
    authenticated_page.goto("/")
    items = authenticated_page.locator(".judgments-list__judgment")
    expect(items).not_to_have_count(0)

    first = items.first
    expect(first.get_by_role("link")).to_have_attribute("href", re.compile(r".+"))

    for label in ["NCN", "Submitter", "Court", "Status", "TDR ref"]:
        expect(first.get_by_text(label, exact=True)).to_be_visible()


def test_judgment_list_pagination(authenticated_page: Page):
    authenticated_page.goto("/")
    expect(authenticated_page.locator(".pagination__page-chevron-previous--disabled")).to_be_visible()

    authenticated_page.get_by_role("link", name="Next page").click()
    expect(authenticated_page).to_have_url(re.compile(r"page=2"))
