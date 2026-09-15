from config.settings.base import env


def environment(request):
    return {"environment": env("ROLLBAR_ENV", None)}


def user_context(request):
    return {
        "user": request.user,
        "is_authenticated": request.user.is_authenticated,
    }
