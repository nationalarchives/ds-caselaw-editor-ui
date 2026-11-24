from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisualPage:
    name: str
    path: str
    clip: dict[str, int] | None = None


VISUAL_PAGES = {
    page.name: page
    for page in (
        VisualPage("2fa_page", "/accounts/2fa/"),
        VisualPage("home_page", "/"),
        VisualPage(
            "judgment_page",
            "/eat/2023/1",
            clip={"x": 0, "y": 0, "width": 1280, "height": 650},
        ),
        VisualPage("judgment_associated_documents_page", "/eat/2023/1/associated-documents"),
        VisualPage("judgment_identifiers_page", "/eat/2023/1/identifiers"),
        VisualPage("judgment_identifiers_add_page", "/eat/2023/1/identifiers/add"),
        VisualPage("judgment_history_page", "/eat/2023/1/history"),
        VisualPage("judgment_downloads_page", "/eat/2023/1/downloads"),
        VisualPage("judgment_upload_page", "/eat/2023/1/upload"),
        VisualPage("judgment_unpublished_upload_page", "/eat/2023/123/upload"),
        VisualPage("judgment_hold_page", "/eat/2023/1/hold"),
        VisualPage("judgment_delete_page", "/eat/2023/1/delete"),
        VisualPage("judgment_onhold_page", "/eat/2023/1/onhold"),
        VisualPage("judgment_publish_page", "/eat/2023/1/publish"),
        VisualPage("judgment_published_page", "/eat/2023/1/published"),
        VisualPage("judgment_unheld_page", "/eat/2023/1/unheld"),
        VisualPage("judgment_unhold_page", "/eat/2023/1/unhold"),
        VisualPage("judgment_unpublish_page", "/eat/2023/1/unpublish"),
        VisualPage("judgment_unpublished_page", "/eat/2023/1/unpublished"),
        VisualPage("judgment_uploaded_page", "/eat/2023/1/uploaded"),
        VisualPage("search_results_page", "/results?search_filter=default&query=Imperial"),
    )
}

BASELINE_PAGE_NAMES = tuple(VISUAL_PAGES)
