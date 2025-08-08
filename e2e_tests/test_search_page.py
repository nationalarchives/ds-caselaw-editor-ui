import environ
from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot
from .utils.authentication import login_user

environ.Env.read_env()


def test_search_page(page: Page):
    judgment_name = "Imperial College Healthcare NHS Trust & Anor v N Matar"
    page.goto("/")

    login_user(page)

    page.get_by_placeholder("Enter a keyword or neutral citation").fill(judgment_name)

    page.get_by_role("button", name="Search").click()

    assert_matches_snapshot(page, "search_results")

    expect(page.locator("p", has_text="We found 1 documents:")).to_be_visible()
    expect(page.locator("a", has_text=judgment_name)).to_be_visible()
