from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
from playwright.sync_api import Page

from e2e_tests.utils.assertions import assert_matches_snapshot
from judgments.feature_flags import WAFFLE_FLAGS, WaffleFlag

from .pages import BASELINE_PAGE_NAMES, VISUAL_PAGES, VisualPage


def url_with_flag_overrides(url: str, enabled_flag: str | None = None) -> str:
    scheme, netloc, path, query, fragment = urlsplit(url)
    query_parameters = parse_qsl(query, keep_blank_values=True)
    query_parameters.extend((flag.name, "1" if flag.name == enabled_flag else "0") for flag in WAFFLE_FLAGS)
    return urlunsplit((scheme, netloc, path, urlencode(query_parameters), fragment))


def open_visual_page(page: Page, visual_page: VisualPage, enabled_flag: str | None = None) -> str:
    page.route("**/confetti.js*", lambda route: route.abort())
    if enabled_flag is not None:
        baseline_response = page.goto(url_with_flag_overrides(visual_page.path))
        assert baseline_response is not None
        assert baseline_response.ok, f"Visual page returned HTTP {baseline_response.status}: {baseline_response.url}"
    response = page.goto(url_with_flag_overrides(visual_page.path, enabled_flag))
    assert response is not None
    assert response.ok, f"Visual page returned HTTP {response.status}: {response.url}"
    page.wait_for_load_state("networkidle")
    return response.text()


@pytest.mark.parametrize("page_name", BASELINE_PAGE_NAMES)
def test_baseline_snapshots(authenticated_page: Page, page_name: str):
    visual_page = VISUAL_PAGES[page_name]
    page_content = open_visual_page(authenticated_page, visual_page)

    assert_matches_snapshot(
        authenticated_page,
        visual_page.name,
        snapshot_group="baseline",
        clip=visual_page.clip,
        page_content=page_content,
    )


FLAGGED_SNAPSHOT_CASES = [(flag, page_name) for flag in WAFFLE_FLAGS for page_name in flag.snapshot_pages]


def test_registered_flag_snapshot_pages_exist():
    configured_pages = {page_name for flag in WAFFLE_FLAGS for page_name in flag.snapshot_pages}

    assert configured_pages <= VISUAL_PAGES.keys()


@pytest.mark.parametrize(
    ("flag", "page_name"),
    FLAGGED_SNAPSHOT_CASES,
    ids=[f"{flag.name}-{page_name}" for flag, page_name in FLAGGED_SNAPSHOT_CASES],
)
def test_flagged_snapshots(authenticated_page: Page, flag: WaffleFlag, page_name: str):
    visual_page = VISUAL_PAGES[page_name]
    page_content = open_visual_page(authenticated_page, visual_page, enabled_flag=flag.name)

    assert_matches_snapshot(
        authenticated_page,
        visual_page.name,
        snapshot_group=flag.name,
        clip=visual_page.clip,
        page_content=page_content,
    )
