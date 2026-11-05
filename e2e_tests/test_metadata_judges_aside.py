import uuid

from playwright.sync_api import Page, expect

JUDGMENT_URI = "/eat/2023/1"


def _claim_row(page: Page, value: str):
    return page.locator(".aside__metadata-compact-entry").filter(has_text=value)


def test_metadata_aside_judges_editor_form(authenticated_editor_page: Page):
    page = authenticated_editor_page
    judge_name = f"E2E Judge {uuid.uuid4()}"

    page.goto(JUDGMENT_URI)
    page.wait_for_load_state("networkidle")

    judges_form = page.locator("[data-metadata-compact-form]")
    expect(judges_form).to_be_visible()
    expect(page.locator("dt").filter(has_text="Judge/s")).to_be_visible()

    page.locator("[data-metadata-compact-draft]").fill(judge_name)
    page.locator("[data-metadata-compact-add]").click()

    pending_row = _claim_row(page, judge_name)
    expect(pending_row).to_be_visible()
    expect(pending_row).to_have_attribute("data-metadata-compact-pending", "")
    expect(pending_row.get_by_label(f"Remove {judge_name}")).to_be_visible()

    expect(page.get_by_role("button", name="Update judges")).to_be_enabled()
