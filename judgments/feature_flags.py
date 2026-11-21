from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WaffleFlag:
    name: str
    snapshot_pages: tuple[str, ...]


DOCUMENT_LIST_QUEUE_FLAG = "document_list_queue"
DOCUMENT_METADATA_FLAG = "document_metadata"
DOCUMENT_MERGE_FLAG = "document_merge"
METADATA_ASIDE_JUDGES_FLAG = "metadata_aside_judges"
NOTES_ON_STATE_CHANGE_FLAG = "notes_on_state_change"
REPORTS_FLAG = "reports"
REPARSE_FLAG = "reparse"


WAFFLE_FLAGS = (
    WaffleFlag(DOCUMENT_LIST_QUEUE_FLAG, ("home_page", "search_results_page")),
    WaffleFlag(DOCUMENT_METADATA_FLAG, ("judgment_page",)),
    WaffleFlag(DOCUMENT_MERGE_FLAG, ("judgment_page",)),
    WaffleFlag(METADATA_ASIDE_JUDGES_FLAG, ("judgment_page",)),
    WaffleFlag(
        NOTES_ON_STATE_CHANGE_FLAG,
        (
            "judgment_hold_page",
            "judgment_publish_page",
            "judgment_unhold_page",
            "judgment_unpublish_page",
        ),
    ),
    WaffleFlag(REPARSE_FLAG, ("judgment_page",)),
    WaffleFlag(REPORTS_FLAG, ("home_page",)),
)

WAFFLE_FLAG_NAMES = {flag.name: flag.name for flag in WAFFLE_FLAGS}
