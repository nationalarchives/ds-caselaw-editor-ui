import environ

env = environ.Env()


def login_user(page):
    page.get_by_label("Username").fill(env("E2E_LOGIN_USERNAME"))
    page.get_by_label("Password").fill(env("E2E_LOGIN_PASSWORD"))

    page.get_by_role("button", name="Sign in").click()
