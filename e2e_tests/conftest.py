import os

import pytest
from playwright.sync_api import Browser, Page


@pytest.fixture(scope="module")
def authenticated_page(browser: Browser, base_url: str) -> Page:
    username = os.getenv("E2E_LOGIN_USER", "root")
    password = os.getenv("E2E_LOGIN_PASSWORD", "password")
    context = browser.new_context(base_url=base_url)
    context.add_cookies(
        [
            {
                "name": "dontShowCookieNotice",
                "value": "true",
                "domain": "django",
                "path": "/",
            },
        ],
    )
    page = context.new_page()
    page.goto("/")
    page.fill("#id_login", username)
    page.fill("#id_password", password)
    page.click("button.button")
    page.wait_for_load_state("networkidle")
    yield page
    context.close()
