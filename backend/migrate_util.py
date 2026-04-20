"""Test and tooling helpers for Alembic migrations."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def configure_default_test_env() -> None:
    if "DATABASE_URL" not in os.environ:
        tests_dir = Path(__file__).resolve().parent / "tests"
        os.environ["DATABASE_URL"] = f"sqlite:///{tests_dir / 'test.db'}"
    os.environ.setdefault("QDRANT_URL", "http://invalid-qdrant:6333")
    os.environ.setdefault("OPENAI_API_KEY", "")


def run_alembic_upgrade(database_url: str) -> None:
    backend_root = Path(__file__).resolve().parent
    ini_path = backend_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("sqlalchemy.url", database_url)
    cfg.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(cfg, "head")
