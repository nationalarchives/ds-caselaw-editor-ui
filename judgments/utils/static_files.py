from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.contrib.staticfiles.storage import staticfiles_storage


def versioned_static(path: str) -> str:
    """Return a static URL; in DEBUG append ?v=mtime so browsers pick up rebuilds."""
    url = staticfiles_storage.url(path)
    if not settings.DEBUG:
        return url

    mtimes: list[float] = []
    source = find(path)
    if source:
        mtimes.append(Path(source).stat().st_mtime)

    collected = Path(settings.STATIC_ROOT) / path
    if collected.exists():
        mtimes.append(collected.stat().st_mtime)

    if not mtimes:
        return url

    return f"{url}?v={int(max(mtimes))}"
