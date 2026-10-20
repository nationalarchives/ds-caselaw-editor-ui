"""Load the MarkLogic integration-test corpus from the API client checkout."""

# ruff: noqa: TRY003, EM102, TC002, TC003, SLF001, SIM105

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from importlib import import_module
from pathlib import Path

from caselawclient.Client import MarklogicApiClient
from caselawclient.errors import MarklogicCommunicationError

from config.settings.base import ROOT_DIR
from judgments.utils.local_dev_safety import LocalDevSafetyError


def _api_client_repo_candidates() -> list[Path]:
    candidates: list[Path] = []
    if env_path := os.environ.get("CASELAW_API_CLIENT_PATH"):
        candidates.append(Path(env_path).expanduser())
    candidates.extend(
        [
            Path("/apiclient"),
            ROOT_DIR.parent / "ds-caselaw-custom-api-client",
            ROOT_DIR / ".." / "ds-caselaw-custom-api-client",
        ],
    )
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def find_api_client_repo() -> Path:
    for candidate in _api_client_repo_candidates():
        if (candidate / "marklogic_harness" / "corpus.py").is_file():
            return candidate
    searched = ", ".join(str(path) for path in _api_client_repo_candidates())
    raise LocalDevSafetyError(
        "Could not find ds-caselaw-custom-api-client (marklogic_harness). "
        f"Searched: {searched}. Set CASELAW_API_CLIENT_PATH to your API client checkout.",
    )


def load_test_corpus_loader() -> Callable[[MarklogicApiClient], None]:
    repo = find_api_client_repo()
    repo_str = str(repo)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
    corpus = import_module("marklogic_harness.corpus")
    return corpus.load_test_corpus


def _configure_merge_demo_metadata_and_properties(client: MarklogicApiClient) -> None:
    corpus = import_module("marklogic_harness.corpus")
    for uri in (corpus.TEST_MERGE_TARGET_URI, corpus.TEST_MERGE_SOURCE_URI):
        corpus._configure_merge_test_properties_only(client, uri)


def reload_marklogic_test_corpus(client: MarklogicApiClient) -> int:
    load_test_corpus_loader()
    corpus = import_module("marklogic_harness.corpus")
    corpus.load_test_corpus(client)
    try:
        corpus.configure_merge_test_documents(client)
    except RuntimeError:
        _configure_merge_demo_metadata_and_properties(client)
    else:
        try:
            corpus.configure_merge_test_identifiers(client)
        except (RuntimeError, MarklogicCommunicationError):
            pass
    return len(corpus.TEST_CORPUS_DOCUMENTS)
