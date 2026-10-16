from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot


def test_metrics_page(authenticated_page: Page):
    authenticated_page.goto("/metrics")

    expect(authenticated_page.get_by_role("heading", name="Metrics")).to_be_visible()
    expect(authenticated_page.get_by_role("heading", name="Publication totals")).to_be_visible()
    expect(authenticated_page.get_by_role("heading", name="Time to first publication")).to_be_visible()
    expect(authenticated_page.get_by_role("heading", name="Time to latest publication")).to_be_visible()
    expect(authenticated_page.get_by_role("heading", name="Submissions before first publication")).to_be_visible()
    expect(authenticated_page.get_by_role("heading", name="Documents by courts and tribunals")).to_be_visible()

    assert_matches_snapshot(authenticated_page, "metrics_page")
