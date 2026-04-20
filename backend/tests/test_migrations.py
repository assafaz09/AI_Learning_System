"""Alembic migration smoke tests (SQLite)."""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from migrate_util import run_alembic_upgrade


def test_alembic_upgrade_reaches_head_on_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "migrate_smoke.db"
    url = f"sqlite:///{db_path.as_posix()}"
    run_alembic_upgrade(url)
    eng = create_engine(url)
    insp = inspect(eng)
    assert "users" in insp.get_table_names()
    assert "learning_projects" in insp.get_table_names()
    lp_cols = {c["name"] for c in insp.get_columns("learning_projects")}
    assert "source" in lp_cols
    assert "importance" in lp_cols
    msg_cols = {c["name"] for c in insp.get_columns("messages")}
    assert "document_scope_json" in msg_cols
