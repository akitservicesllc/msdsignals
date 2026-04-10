"""Smoke tests for MSDSignals standalone app."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_shared_db_imports():
    from shared import db
    assert hasattr(db, "get_msd_signals_range")
    assert hasattr(db, "get_msd_summary_range")
    assert hasattr(db, "get_cluster_bomb_rows")
    assert hasattr(db, "get_cluster_bomb_available_dates")


def test_views_import():
    from views import msd_signals, cluster_bombs
    assert callable(msd_signals.render)
    assert callable(cluster_bombs.render)


def test_msd_range_basic():
    """If local DB exists, ensure range query returns rows for latest 30d."""
    from shared.db import (
        get_msd_latest_date, get_msd_signals_range, get_msd_summary_range,
    )
    latest = get_msd_latest_date()
    if not latest:
        return  # no DB -> skip
    from datetime import date, timedelta
    end = date.fromisoformat(latest)
    start = end - timedelta(days=30)
    rows = get_msd_signals_range(start.isoformat(), end.isoformat())
    summary = get_msd_summary_range(start.isoformat(), end.isoformat())
    assert isinstance(rows, list)
    assert summary["total"] == len(rows)
    if rows:
        assert "category" in rows[0]
        assert "score" in rows[0]
        assert "prints" in rows[0]
