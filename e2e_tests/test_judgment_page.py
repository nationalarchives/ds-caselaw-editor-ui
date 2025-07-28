import environ

from playwright.sync_api import Page, expect

from .utils.assertions import assert_matches_snapshot
from .utils.authentication import login_user

environ.Env.read_env()

def test_judgment_page(page: Page):
    judgment_url = "/eat/2023/1"
    judgment_name = "Imperial College Healthcare NHS Trust & Anor v N Matar"
    judgment_ncn = "[2023] EAT 1"
    page.goto("/")

    login_user(page)

    page.goto(judgment_url)

    assert_matches_snapshot(page, "judgment_review")

    # Toolbar
    expect(page.locator("a", has_text="Review")).to_be_visible()
    expect(page.locator("a", has_text="Unpublish")).to_be_visible()
    expect(page.locator("a", has_text="Identifiers")).to_be_visible()
    expect(page.locator("a", has_text="History")).to_be_visible()
    expect(page.locator("a", has_text="Downloads")).to_be_visible()

    # Actions
    expect(page.locator("a", has_text="Create in Jira")).to_be_visible()
    expect(page.get_by_role("button", name="Request enrichment")).to_be_visible()
    expect(page.locator("a", has_text="Delete")).to_be_visible()

    # Forms
    expect(page.get_by_label("NCN")).to_have_value(judgment_ncn)
    expect(page.get_by_label("Court")).to_have_value("EAT")
    expect(page.get_by_label("Judgment date")).to_have_value("24 Jan 2023")
    expect(page.get_by_label("Name")).to_have_value(judgment_name)

    # Info
    expect(page.locator("a", has_text="Tess Testerton")).to_be_visible()
    expect(page.locator("div.judgment-status-indicator", has_text="Published")).to_be_visible()
    expect(page.locator("p", has_text="TDR-1999-ABC")).to_be_visible()

    # Document view
    expect(page.locator("a", has_text="HTML view")).to_be_visible()
    expect(page.locator("a", has_text="PDF view")).to_be_visible()


    # Unpublish
    page.locator("a", has_text="Unpublish").click()
    assert_matches_snapshot(page, "judgment_unpublish")


    expect(page.locator("h1", has_text="I want to unpublish:")).to_be_visible()
    expect(page.locator("h2", has_text=judgment_name)).to_be_visible()
    expect(page.get_by_role("button", name="Unpublish")).to_be_visible()
    expect(page.locator("a", has_text="Go back to review")).to_be_visible()

    # Identifiers
    page.locator("a", has_text="Identifiers").click()
    assert_matches_snapshot(page, "judgment_identifiers")

    expect(page.locator("h1", has_text="Identifiers for:")).to_be_visible()
    expect(page.locator("h2", has_text=judgment_name)).to_be_visible()
    expect(page.locator("h2", has_text="Preferred identifier")).to_be_visible()
    expect(page.locator("b", has_text=f"Neutral Citation Number: {judgment_ncn}")).to_be_visible()
    expect(page.locator("h2", has_text="All identifiers")).to_be_visible()


    # Identifiers > Table Heading
    expect(page.locator("table")).to_contain_text("Type")
    expect(page.locator("table")).to_contain_text("Value")
    expect(page.locator("table")).to_contain_text("Public URL")
    expect(page.locator("table")).to_contain_text("Deprecated")

    # Identifiers > Table Body
    expect(page.locator("table")).to_contain_text("Neutral Citation Number")
    expect(page.locator("table")).to_contain_text(judgment_ncn)
    expect(page.locator("table")).to_contain_text(judgment_url)
    expect(page.locator("table")).to_contain_text("False")


    # History
    page.locator("a", has_text="History").click()
    assert_matches_snapshot(page, "judgment_history")

    expect(page.locator("h2", has_text="Legacy version 2")).to_be_visible()
    expect(page.locator("h2", has_text="Legacy version 1")).to_be_visible()


    # Downloads
    page.locator("a", has_text="Downloads").click()
    assert_matches_snapshot(page, "judgment_downloads")

    expect(page.locator("h1", has_text="Download documents for:")).to_be_visible()
    expect(page.locator("h2", has_text=judgment_name)).to_be_visible()

    expect(page.locator("a", has_text="Download .DOCX")).to_be_visible()
    expect(page.locator("a", has_text="Download PDF")).to_be_visible()
    expect(page.locator("a", has_text="Download XML")).to_be_visible()
