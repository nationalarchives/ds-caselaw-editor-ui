from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from config.settings.base import ROOT_DIR
from judgments.utils.static_files import versioned_static

_FIXTURES = ROOT_DIR / "judgments" / "tests" / "fixtures"


class TestVersionedStatic(SimpleTestCase):
    @override_settings(
        DEBUG=True,
        STATIC_ROOT=str(_FIXTURES / "static_root"),
    )
    @patch(
        "judgments.utils.static_files.find",
        return_value=str(_FIXTURES / "example.css"),
    )
    @patch.object(Path, "stat")
    def test_versioned_static_appends_mtime_in_debug(self, mock_stat, mock_find):
        mock_stat.return_value = SimpleNamespace(st_mtime=1_700_000_000.5)

        url = versioned_static("css/example.css")

        assert url == "/static/css/example.css?v=1700000000"
        mock_find.assert_called_once_with("css/example.css")

    @override_settings(DEBUG=False)
    def test_versioned_static_plain_url_when_not_debug(self):
        url = versioned_static("css/main.css")
        assert url == "/static/css/main.css"
