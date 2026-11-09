import uuid

from playwright.sync_api import Page, expect

JUDGMENT_URI = "/eat/2023/1"


def test_metadata_aside_judges_editor_form(authenticated_editor_page: Page):
    page = authenticated_editor_page
    judge_name = f"E2E Judge {uuid.uuid4()}"

    page.goto(JUDGMENT_URI)
    page.wait_for_load_state("networkidle")

    judges_form = page.locator("[data-metadata-compact-form]")
    expect(judges_form).to_be_visible()
    expect(judges_form.locator("dt").filter(has_text="Judges")).to_be_visible()

    new_judge_entries = judges_form.locator("[data-metadata-compact-new-entry]")
    initial_entry_count = new_judge_entries.count()

    judges_form.locator("[data-metadata-compact-add]").click()
    expect(new_judge_entries).to_have_count(initial_entry_count + 1)

    new_judge_entry = new_judge_entries.last
    new_judge_input = new_judge_entry.locator("[data-metadata-compact-new-input]")
    new_judge_input.fill(judge_name)

    expect(new_judge_input).to_have_value(judge_name)
    expect(
        new_judge_entry.get_by_role("button", name="Remove", exact=True),
    ).to_be_visible()
    expect(
        judges_form.get_by_role("button", name="Save", exact=True),
    ).to_be_enabled()
