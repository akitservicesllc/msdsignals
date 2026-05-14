"""
Read-only DB access for MSDSignals standalone app.

Reads four external DBs synced into /home/data/ by MAG's cross_app_sync:
    - pine_screener.db  (has msd_trades table)
    - vl_tracker.db     (has cluster_bombs + positioning_trades tables)
    - marketsurge.db    (has screen_scans table)
    - news_tracker.db   (has news_items table)

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


def _resolve_ms_db_path() -> Path:
    env_val = os.environ.get("MARKETSURGE_DB_PATH")
    if env_val:
        return Path(env_val)
    if Path("/home/site/wwwroot").exists():
        return Path("/home/data") / "marketsurge.db"
    return Path(r"C:\Claude Projects\MarketSurge\data\marketsurge.db")


def _resolve_news_db_path() -> Path:
    env_val = os.environ.get("NEWS_TRACKER_DB_PATH")
    if env_val:
        return Path(env_val)
    if Path("/home/site/wwwroot").exists():
        return Path("/home/data") / "news_tracker.db"
    return Path(r"C:\Claude Projects\News Tracker\data\news_tracker.db")


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


def _ms_conn() -> sqlite3.Connection | None:
    return _ro_conn(_resolve_ms_db_path())


def _news_conn() -> sqlite3.Connection | None:
    return _ro_conn(_resolve_news_db_path())


# ---------------------------------------------------------------------------
# ETF detection — uses VL's security_type='ETF' classification
# ---------------------------------------------------------------------------
def get_etf_tickers(start_date: str, end_date: str) -> set[str]:
    """Tickers tagged as 'ETF' by VL in the given date range."""
    conn = _vl_conn()
    if conn is None:
        return set()
    try:
        rows = conn.execute(
            "SELECT DISTINCT ticker FROM positioning_trades "
            "WHERE trade_date BETWEEN ? AND ? AND security_type = 'ETF'",
            (start_date, end_date),
        ).fetchall()
        return {r["ticker"] for r in rows}
    except sqlite3.OperationalError:
        return set()
    finally:
        conn.close()


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


# ---------------------------------------------------------------------------
# Emerging Patterns — cross-DB join: VL top5 × MS scans × News catalysts
# ---------------------------------------------------------------------------
NEWS_QUALITY_THRESHOLD = 7  # urgency_score >= 7 = "good quality" catalyst

# MarketSurge screen display names
MS_SCREEN_DISPLAY = {
    "bear_c_shorts": "Bear C Shorts",
    "climax_shorts": "Climax Shorts",
    "continuation_shorts": "Continuation Shorts",
    "eps_40_pct": "EPS 40%+",
    "htf": "High Tight Flag",
    "massive_volume": "Massive Volume",
    "rule_of_80": "Rule of 80",
    "sales_45_pct": "Sales 45%+",
    "strength_during_chop": "Strength/Chop",
    "strength_during_downturn": "Strength/Downturn",
    "top_10_groups": "Top 10 Groups",
    "triple_90": "Triple 90",
}


def _get_vl_top5(start_date: str, end_date: str) -> dict[tuple[str, str], list[dict]]:
    """Return {(date, ticker): [print_dicts]} for VL rank<=5 prints in range."""
    conn = _vl_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            """
            SELECT trade_date, trade_time, ticker, sector, trade_rank,
                   trade_price, volume, dollar_amount, dark_pool
              FROM positioning_trades
             WHERE trade_date BETWEEN ? AND ?
               AND trade_rank IS NOT NULL
               AND CAST(trade_rank AS INTEGER) <= 5
             ORDER BY trade_date, ticker, trade_time
            """,
            (start_date, end_date),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()

    out: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r["trade_date"], r["ticker"])
        out.setdefault(key, []).append(dict(r))
    # Sort each ticker's prints by rank ASC so prints[0] = top print (rank 1 best)
    for key in out:
        out[key].sort(
            key=lambda p: int(p["trade_rank"]) if p.get("trade_rank") is not None else 9999
        )
    return out


def _get_ms_matches(start_date: str, end_date: str) -> dict[tuple[str, str], list[str]]:
    """Return {(date, ticker): [screen_name, ...]} for MS scans in range."""
    conn = _ms_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            """
            SELECT scan_date, symbol, screen_name, industry_name
              FROM screen_scans
             WHERE scan_date BETWEEN ? AND ?
             ORDER BY scan_date, symbol
            """,
            (start_date, end_date),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()

    out: dict[tuple[str, str], list[str]] = {}
    for r in rows:
        key = (r["scan_date"], r["symbol"])
        out.setdefault(key, []).append(r["screen_name"])
    return out


def _get_news_matches(start_date: str, end_date: str) -> dict[tuple[str, str], list[dict]]:
    """Return {(date, ticker): [{headline, urgency, category, source}]} for good-quality news."""
    conn = _news_conn()
    if conn is None:
        return {}
    try:
        rows = conn.execute(
            """
            SELECT ticker, date(published_at) AS pub_date,
                   headline, urgency_score, category, source
              FROM news_items
             WHERE date(published_at) BETWEEN ? AND ?
               AND urgency_score >= ?
             ORDER BY published_at DESC
            """,
            (start_date, end_date, NEWS_QUALITY_THRESHOLD),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    finally:
        conn.close()

    out: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r["pub_date"], r["ticker"])
        out.setdefault(key, []).append({
            "headline": r["headline"],
            "urgency": r["urgency_score"],
            "category": r["category"],
            "source": r["source"],
        })
    return out


def get_emerging_patterns(start_date: str, end_date: str) -> list[dict]:
    """Cross-join VL top5 x MS scans x News to produce Emerging Pattern rows.

    Categories (priority order -- highest wins):
        GOLDEN  -> VL top5 AND in MS top_10_groups same date
        MS+VL   -> VL top5 AND in any other MS screen same date
        NEWS+VL -> VL top5 AND news catalyst with urgency >= 7 same date

    Returns list of dicts sorted by date DESC, then category priority, then ticker.
    """
    vl = _get_vl_top5(start_date, end_date)
    if not vl:
        return []

    ms = _get_ms_matches(start_date, end_date)
    news = _get_news_matches(start_date, end_date)

    cat_priority = {"GOLDEN": 0, "MS+VL": 1, "NEWS+VL": 2}
    results: list[dict] = []

    for (trade_date, ticker), prints in vl.items():
        ms_screens = ms.get((trade_date, ticker), [])
        news_items = news.get((trade_date, ticker), [])

        has_top10_groups = "top_10_groups" in ms_screens
        has_any_ms = len(ms_screens) > 0
        has_news = len(news_items) > 0

        if not (has_any_ms or has_news):
            continue  # VL top5 alone = no emerging pattern

        # Determine category
        if has_top10_groups:
            category = "GOLDEN"
        elif has_any_ms:
            category = "MS+VL"
        elif has_news:
            category = "NEWS+VL"
        else:
            continue

        best_rank = min(
            int(p["trade_rank"]) for p in prints
            if p.get("trade_rank") is not None
        )
        sector = prints[0].get("sector") or ""
        total_dollars = sum(float(p.get("dollar_amount") or 0) for p in prints)
        # prints are sorted by rank ASC in _get_vl_top5; prints[0] is the top print
        top_print_price = prints[0].get("trade_price") if prints else None

        # Deduplicate MS screens
        ms_unique = sorted(set(ms_screens))
        ms_display = [MS_SCREEN_DISPLAY.get(s, s) for s in ms_unique]

        results.append({
            "trade_date": trade_date,
            "ticker": ticker,
            "category": category,
            "best_rank": best_rank,
            "sector": sector,
            "vl_prints": len(prints),
            "total_dollars": total_dollars,
            "top_print_price": top_print_price,
            "ms_screens": ms_display,
            "ms_screens_raw": ms_unique,
            "has_top10_groups": has_top10_groups,
            "news_items": news_items,
            "news_count": len(news_items),
        })

    results.sort(
        key=lambda r: (
            r["trade_date"],
            cat_priority.get(r["category"], 9),
            r["ticker"],
        ),
    )
    # Reverse so newest date first, but within same date keep priority order
    from functools import cmp_to_key
    def _cmp(a, b):
        # Date desc
        if a["trade_date"] != b["trade_date"]:
            return -1 if a["trade_date"] > b["trade_date"] else 1
        # Category priority asc
        pa = cat_priority.get(a["category"], 9)
        pb = cat_priority.get(b["category"], 9)
        if pa != pb:
            return -1 if pa < pb else 1
        # Ticker asc
        return -1 if a["ticker"] < b["ticker"] else (1 if a["ticker"] > b["ticker"] else 0)

    results.sort(key=cmp_to_key(_cmp))
    return results


def get_emerging_summary(start_date: str, end_date: str) -> dict:
    """Summary counts for emerging patterns."""
    rows = get_emerging_patterns(start_date, end_date)
    golden = sum(1 for r in rows if r["category"] == "GOLDEN")
    ms_vl = sum(1 for r in rows if r["category"] == "MS+VL")
    news_vl = sum(1 for r in rows if r["category"] == "NEWS+VL")
    dates = len({r["trade_date"] for r in rows})
    return {
        "total": len(rows),
        "golden": golden,
        "ms_vl": ms_vl,
        "news_vl": news_vl,
        "days": dates,
    }
