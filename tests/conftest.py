"""Test fixtures for the HDB CLI."""

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner


@pytest.fixture
def isolated_config(monkeypatch):
    """Ensure tests don't touch the user's real ~/.config/hdb-cli."""
    tmp = tempfile.mkdtemp(prefix="hdb-cli-test-")
    monkeypatch.setenv("HDB_CONFIG_DIR", tmp)
    # Reload the config module to pick up the new env var
    import importlib
    from hdb_cli import config as cfg
    importlib.reload(cfg)
    yield Path(tmp)


@pytest.fixture
def runner():
    return CliRunner()
