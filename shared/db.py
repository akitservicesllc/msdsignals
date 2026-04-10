"""
Read-only DB access for MSDSignals standalone app.

Reads two external DBs synced into /home/data/ by MAG's cross_app_sync:
    - pine_screener.db  (has msd_trades table)
    - vl_tracker.db     (has cluster_bombs table)

On the local workstation, falls back to the source project paths.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB path resolution
# ---------------------------------------------------------------------------
def _resolve_pine_db_path() -> Path:
    env_val = os.environ.get("PINE_SCREENER_DB_PATH")
    if env_val:
        return Path(env_val)
    if Path("/home/site/wwwroot").exists():
        return Path("/home/data") / "pine_screener.db"
    return Path(r"C:\Claude Projects\Pine Screener\data\pine_screener.db")


def _resolve_vl_db_path() -> Path:
    env_val = os.environ.get("VL_TRACKER_DB_PATH")
    if env_val:
        return Path(env_val)
    if Path("/home/site/wwwroot").exists():
        return Path("/home/data") / "vl_tracker.db"
    return Path(r"C:\Claude Projects\VL Tracker\data\vl_tracker.db")


def _ro_conn(db_path: Path) -> sqlite3.Connection | None:
    if not db_path.exists():
        logger.debug("DB not found: %s", db_path)
        return None
    try:
        c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA query_only=ON")
        c.execute("PRAGMA busy_timeout=5000")
        return c
    except sqlite3.Error as e:
        logger.warning("Failed to open %s: %s", db_path, e)
        return None


def _pine_conn() -> sqlite3.Connection | None:
    return _ro_conn(_resolve_pine_db_path())


def _vl_conn() -> sqlite3.Connection | None:
    return _ro_conn(_resolve_vl_db_path())


# ---------------------------------------------------------------------------
# MSD queries — reads pine_screener.db.msd_trades
# ---------------------------------------------------------------------------
def get_msd_available_dates(limit: int = 120) -> list[str]:
    """Distinct trade dates in msd_trades, newest first."""
    conn = _pine_conn()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT DISTINCT trade_date FROM msd_trades "
            "ORDER BY trade_date DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [r["trade_date"] for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def get_msd_latest_date() -> str | None:
    conn = _pine_conn()
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT MAX(trade_date) FROM msd_trades").fetchone()
        return row[0] if row and row[0] else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def get_msd_last_computed_at() -> str | None:
    conn = _pine_conn()
    if conn is None:
        return None
    try:
        row = conn.execute("SELECT MAX(computed_at) FROM msd_trades").fetchone()
        return row[0] if row and row[0] else None
    except sqlite3.OperationalError:
        return None
    finally:
        conn.close()


def get_msd_signals_range(
    start_date: str,
    end_date: str,
    category: str | None = None,
    min_score: float = 0.0,
) -> list[dict]:
    """Return MSD rows for a date range (inclusive), sorted by date desc then score desc."""
    conn = _pine_conn()
    if conn is None:
        return []
    try:
        sql = (
            "SELECT trade_date, ticker, sector, hit_count, best_rank, "
            "       has_top5, strong_signal, category, score, "
            "       first_print_time, first_print_rank, "
            "       last_print_time, last_print_rank, "
            "       total_dollars, prints_json, computed_at "
            "  FROM msd_trades "
            " WHERE trade_date BETWEEN ? AND ? AND score >= ?"
        )
        params: list = [start_date, end_date, min_score]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY trade_date DESC, score DESC, ticker ASC"
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        logger.warning("get_msd_signals_range failed: %s", e)
        return []
    finally:
        conn.close()

    out: list[dict] = []
    for r in rows:
        d = dict(r)
        try:
            d["prints"] = json.loads(d.get("prints_json") or "[]")
        except (ValueError, TypeError):
            d["prints"] = []
        out.append(d)
    return out


def get_msd_summary_range(start_date: str, end_date: str) -> dict:
    """Aggregate category counts over a date range."""
    conn = _pine_conn()
    if conn is None:
        return {"start": start_date, "end": end_date, "total": 0,
                "strong": 0, "top5": 0, "msd": 0, "days": 0}
    try:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n FROM msd_trades "
            "WHERE trade_date BETWEEN ? AND ? GROUP BY category",
            (start_date, end_date),
        ).fetchall()
        day_row = conn.execute(
            "SELECT COUNT(DISTINCT trade_date) FROM msd_trades "
            "WHERE trade_date BETWEEN ? AND ?",
            (start_date, end_date),
        ).fetchone()
    except sqlite3.OperationalError:
        return {"start": start_date, "end": end_date, "total": 0,
                "strong": 0, "top5": 0, "msd": 0, "days": 0}
    finally:
        conn.close()

    counts = {r["category"]: r["n"] for r in rows}
    return {
        "start": start_date,
        "end": end_date,
        "total": sum(counts.values()),
        "strong": counts.get("STRONG", 0),
        "top5": counts.get("TOP5_MSD", 0),
        "msd": counts.get("MSD", 0),
        "days": day_row[0] if day_row else 0,
    }


# ---------------------------------------------------------------------------
# Cluster Bombs queries — reads vl_tracker.db.cluster_bombs
# ---------------------------------------------------------------------------
def get_cluster_bomb_rows(trade_date: str | None = None, limit: int = 5000) -> list[dict]:
    conn = _vl_conn()
    if conn is None:
        return []
    try:
        sql = (
            "SELECT trade_date, time_range, ticker, sector, cluster_size, "
            "       total_volume, total_dollars, avg_price "
            "  FROM cluster_bombs WHERE 1=1"
        )
        params: list = []
        if trade_date:
            sql += " AND trade_date = ?"
            params.append(trade_date)
        sql += " ORDER BY trade_date DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def get_cluster_bomb_available_dates() -> list[str]:
    """Distinct dates with cluster bomb rows, newest first."""
    conn = _vl_conn()
    if conn is None:
        return []
    try:
        rows = conn.execute(
            "SELECT DISTINCT trade_date FROM cluster_bombs "
            "ORDER BY trade_date DESC"
        ).fetchall()
        return [r["trade_date"] for r in rows]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()
