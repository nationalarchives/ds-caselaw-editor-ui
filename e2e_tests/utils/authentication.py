import environ

env = environ.Env()


def login_user(page):
    page.get_by_label("Username").fill(env("E2E_LOGIN_USERNAME", default="root"))
    page.get_by_label("Password").fill(env("E2E_LOGIN_PASSWORD", default="password"))

    page.get_by_role("button", name="Sign in").click()
