from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.backends.postgresql.base import DatabaseWrapper
from django.test import TestCase, override_settings

from judgments.utils.local_dev_safety import (
    LocalDevSafetyError,
    assert_local_database,
    assert_local_marklogic_host,
)


class TestLocalDevSafety(TestCase):
    def test_allows_local_marklogic_hosts(self):
        assert_local_marklogic_host("marklogic", use_https=False)
        assert_local_marklogic_host("127.0.0.1", use_https=False)

    def test_rejects_remote_marklogic_host(self):
        with pytest.raises(LocalDevSafetyError, match="remote environment"):
            assert_local_marklogic_host("cf-58785-Alb.example.elb.amazonaws.com", use_https=False)

    def test_rejects_https_marklogic(self):
        with pytest.raises(LocalDevSafetyError, match="MARKLOGIC_USE_HTTPS"):
            assert_local_marklogic_host("marklogic", use_https=True)

    @override_settings(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "ds_judgments_editor_ui",
                "HOST": "postgres",
                "USER": "postgres",
                "PASSWORD": "admin",
            },
        },
    )
    def test_allows_local_postgres_host(self):
        assert_local_database(connection)

    def test_rejects_remote_postgres_host(self):
        database = DatabaseWrapper(
            {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "prod",
                "HOST": "prod.example.amazonaws.com",
                "USER": "postgres",
                "PASSWORD": "admin",
            },
        )
        with pytest.raises(LocalDevSafetyError, match="not an allowed local host"):
            assert_local_database(database)


class TestResetLocalFixturesCommand(TestCase):
    @override_settings(MARKLOGIC_HOST="cf-58785.example.elb.amazonaws.com", MARKLOGIC_USE_HTTPS=False)
    def test_refuses_remote_marklogic(self):
        with pytest.raises(CommandError, match="remote environment"):
            call_command("reset_local_fixtures", noinput=True)

    @override_settings(MARKLOGIC_HOST="marklogic", MARKLOGIC_USE_HTTPS=False)
    @patch("judgments.management.commands.reset_local_fixtures.reload_marklogic_test_corpus")
    def test_reloads_marklogic_corpus_when_local(self, mock_reload_corpus):
        mock_reload_corpus.return_value = 8

        call_command("reset_local_fixtures", noinput=True)

        mock_reload_corpus.assert_called_once()
