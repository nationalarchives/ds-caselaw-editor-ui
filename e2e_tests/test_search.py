import re

from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot


def test_search(authenticated_page: Page):
    authenticated_page.goto("/")
    expect(authenticated_page.get_by_label("Everywhere")).to_be_checked()
    expect(authenticated_page.get_by_label("NCN")).not_to_be_checked()

    authenticated_page.get_by_label("NCN").click()
    expect(authenticated_page.get_by_label("NCN")).to_be_checked()
    expect(authenticated_page.get_by_label("Everywhere")).not_to_be_checked()

    authenticated_page.get_by_label("Everywhere").click()
    authenticated_page.get_by_role("searchbox").fill("Imperial")
    authenticated_page.get_by_role("button", name="Search").click()
    expect(authenticated_page).to_have_url(re.compile(r"/results"))
    assert_matches_snapshot(authenticated_page, "search_results_page")
