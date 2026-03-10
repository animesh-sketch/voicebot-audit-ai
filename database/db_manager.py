"""
db_manager.py — All SQLite database operations for VoiceBot Audit AI.
Pure data access layer; zero business logic.
"""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from database.models import CampaignStatus

DB_PATH = Path(__file__).parent.parent / "voicebot_audit.db"


# ─────────────────────────── Connection ──────────────────────────

@contextmanager
def _conn():
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _rows(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ─────────────────────────── Schema Init ─────────────────────────

def init_db():
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS campaigns (
                campaign_id   TEXT PRIMARY KEY,
                campaign_name TEXT NOT NULL,
                client_name   TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now')),
                status        TEXT DEFAULT 'ACTIVE'
            );

            CREATE TABLE IF NOT EXISTS calls (
                call_id       TEXT PRIMARY KEY,
                campaign_id   TEXT NOT NULL,
                call_link     TEXT,
                duration      INTEGER DEFAULT 0,
                timestamp     TEXT,
                transcript    TEXT,
                lead_category TEXT DEFAULT 'UNKNOWN',
                FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_templates (
                field_id    TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                field_name  TEXT NOT NULL,
                max_score   REAL DEFAULT 10.0,
                order_index INTEGER DEFAULT 0,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_results (
                audit_id          TEXT PRIMARY KEY,
                call_id           TEXT NOT NULL UNIQUE,
                campaign_id       TEXT NOT NULL,
                auditor_name      TEXT DEFAULT 'Auditor',
                field_scores      TEXT,   -- JSON: {field_id: score}
                total_score       REAL DEFAULT 0,
                max_possible_score REAL DEFAULT 0,
                percentage_score  REAL DEFAULT 0,
                issue_tags        TEXT DEFAULT '[]',  -- JSON array
                notes             TEXT DEFAULT '',
                created_at        TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (call_id) REFERENCES calls(call_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS bot_failures (
                failure_id       TEXT PRIMARY KEY,
                call_id          TEXT NOT NULL,
                campaign_id      TEXT NOT NULL,
                failure_type     TEXT NOT NULL,
                failure_reason   TEXT,
                confidence_score REAL DEFAULT 0,
                detected_at      TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (call_id) REFERENCES calls(call_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS campaign_insights (
                insight_id    TEXT PRIMARY KEY,
                campaign_id   TEXT NOT NULL UNIQUE,
                generated_at  TEXT DEFAULT (datetime('now')),
                avg_qa_score  REAL,
                total_failures INTEGER,
                insights_json TEXT,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id)
            );
        """)


# ─────────────────────────── Campaigns ───────────────────────────

def create_campaign(campaign_name: str, client_name: str) -> str:
    cid = f"CAMP-{uuid.uuid4().hex[:8].upper()}"
    with _conn() as con:
        con.execute(
            "INSERT INTO campaigns (campaign_id, campaign_name, client_name) VALUES (?, ?, ?)",
            (cid, campaign_name, client_name),
        )
    return cid


def get_campaign(campaign_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
    return dict(row) if row else None


def get_all_campaigns() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM campaigns ORDER BY created_at DESC"
        ).fetchall()
    return _rows(rows)


def update_campaign_status(campaign_id: str, status: str):
    with _conn() as con:
        con.execute(
            "UPDATE campaigns SET status = ? WHERE campaign_id = ?",
            (status, campaign_id),
        )


def close_campaign(campaign_id: str):
    with _conn() as con:
        con.execute(
            "UPDATE campaigns SET status = ? WHERE campaign_id = ?",
            (CampaignStatus.CLOSED.value, campaign_id),
        )


def auto_update_campaign_status(campaign_id: str):
    """Recompute and persist campaign status based on audit progress."""
    prog = get_campaign_progress(campaign_id)
    camp = get_campaign(campaign_id)
    if not camp or camp["status"] == CampaignStatus.CLOSED.value:
        return
    total, audited = prog["total"], prog["audited"]
    if total == 0:
        new_status = CampaignStatus.ACTIVE.value
    elif audited == 0:
        new_status = CampaignStatus.ACTIVE.value
    elif audited < total:
        new_status = CampaignStatus.IN_PROGRESS.value
    else:
        new_status = CampaignStatus.READY_TO_CLOSE.value
    update_campaign_status(campaign_id, new_status)


def get_campaign_progress(campaign_id: str) -> dict:
    with _conn() as con:
        total = con.execute(
            "SELECT COUNT(*) FROM calls WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()[0]
        audited = con.execute(
            "SELECT COUNT(*) FROM audit_results WHERE campaign_id = ?",
            (campaign_id,)
        ).fetchone()[0]
    return {
        "total":   total,
        "audited": audited,
        "pending": total - audited,
        "pct":     round(audited / total * 100, 1) if total else 0,
    }


# ─────────────────────────── Calls ───────────────────────────────

def create_call(
    campaign_id: str,
    call_link: str = "",
    duration: int = 0,
    timestamp: str = "",
    transcript: str = "",
    lead_category: str = "UNKNOWN",
) -> str:
    cid = f"CALL-{uuid.uuid4().hex[:8].upper()}"
    with _conn() as con:
        con.execute(
            """INSERT INTO calls
               (call_id, campaign_id, call_link, duration, timestamp, transcript, lead_category)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cid, campaign_id, call_link, duration, timestamp, transcript, lead_category),
        )
    return cid


def get_call(call_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            """SELECT c.*, ar.audit_id, ar.percentage_score, ar.auditor_name,
                      ar.issue_tags, ar.notes
               FROM calls c
               LEFT JOIN audit_results ar ON ar.call_id = c.call_id
               WHERE c.call_id = ?""",
            (call_id,)
        ).fetchone()
    return dict(row) if row else None


def get_calls_for_campaign(campaign_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            """SELECT c.*, ar.audit_id, ar.percentage_score, ar.auditor_name,
                      ar.issue_tags, ar.total_score, ar.max_possible_score
               FROM calls c
               LEFT JOIN audit_results ar ON ar.call_id = c.call_id
               WHERE c.campaign_id = ?
               ORDER BY c.timestamp DESC, c.call_id""",
            (campaign_id,),
        ).fetchall()
    return _rows(rows)


def update_call_lead_category(call_id: str, lead_category: str):
    with _conn() as con:
        con.execute(
            "UPDATE calls SET lead_category = ? WHERE call_id = ?",
            (lead_category, call_id),
        )


def bulk_import_calls(campaign_id: str, df: pd.DataFrame) -> int:
    """Import calls from a DataFrame. Returns number of rows imported."""
    count = 0
    for _, row in df.iterrows():
        create_call(
            campaign_id=campaign_id,
            call_link=str(row.get("call_link", "")),
            duration=int(row.get("duration", 0)),
            timestamp=str(row.get("timestamp", datetime.now().isoformat())),
            transcript=str(row.get("transcript", "")),
            lead_category=str(row.get("lead_category", "UNKNOWN")),
        )
        count += 1
    return count


# ─────────────────────────── Audit Templates ─────────────────────

def get_template_fields(campaign_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM audit_templates WHERE campaign_id = ? ORDER BY order_index",
            (campaign_id,)
        ).fetchall()
    return _rows(rows)


def add_template_field(campaign_id: str, field_name: str, max_score: float = 10.0) -> str:
    fid = f"FLD-{uuid.uuid4().hex[:6].upper()}"
    with _conn() as con:
        order = con.execute(
            "SELECT COALESCE(MAX(order_index),0)+1 FROM audit_templates WHERE campaign_id = ?",
            (campaign_id,)
        ).fetchone()[0]
        con.execute(
            "INSERT INTO audit_templates (field_id, campaign_id, field_name, max_score, order_index) VALUES (?,?,?,?,?)",
            (fid, campaign_id, field_name, max_score, order),
        )
    return fid


def delete_template_field(field_id: str):
    with _conn() as con:
        con.execute("DELETE FROM audit_templates WHERE field_id = ?", (field_id,))


def seed_template_fields(campaign_id: str, fields: list[tuple[str, float]]):
    """Bulk-insert (field_name, max_score) pairs — for seeding."""
    for i, (name, max_s) in enumerate(fields):
        fid = f"FLD-{uuid.uuid4().hex[:6].upper()}"
        with _conn() as con:
            con.execute(
                "INSERT INTO audit_templates (field_id, campaign_id, field_name, max_score, order_index) VALUES (?,?,?,?,?)",
                (fid, campaign_id, name, max_s, i),
            )


# ─────────────────────────── Audit Results ───────────────────────

def submit_audit(
    call_id: str,
    campaign_id: str,
    auditor_name: str,
    field_scores: dict,        # {field_id: score}
    issue_tags: list[str],
    notes: str = "",
) -> str:
    """Save audit result and auto-update campaign status."""
    fields = get_template_fields(campaign_id)
    total = sum(field_scores.get(f["field_id"], 0) for f in fields)
    max_p = sum(f["max_score"] for f in fields)
    pct   = round(total / max_p * 100, 2) if max_p else 0.0

    with _conn() as con:
        existing = con.execute(
            "SELECT audit_id FROM audit_results WHERE call_id = ?", (call_id,)
        ).fetchone()
        if existing:
            con.execute(
                """UPDATE audit_results
                   SET auditor_name=?, field_scores=?, total_score=?,
                       max_possible_score=?, percentage_score=?,
                       issue_tags=?, notes=?, created_at=datetime('now')
                   WHERE call_id=?""",
                (auditor_name, json.dumps(field_scores), total, max_p, pct,
                 json.dumps(issue_tags), notes, call_id),
            )
            aid = existing["audit_id"]
        else:
            aid = f"AUD-{uuid.uuid4().hex[:8].upper()}"
            con.execute(
                """INSERT INTO audit_results
                   (audit_id, call_id, campaign_id, auditor_name, field_scores,
                    total_score, max_possible_score, percentage_score, issue_tags, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (aid, call_id, campaign_id, auditor_name, json.dumps(field_scores),
                 total, max_p, pct, json.dumps(issue_tags), notes),
            )
    auto_update_campaign_status(campaign_id)
    return aid


def get_audit_for_call(call_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM audit_results WHERE call_id = ?", (call_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["field_scores"] = json.loads(d["field_scores"] or "{}")
    d["issue_tags"]   = json.loads(d["issue_tags"] or "[]")
    return d


def get_audits_for_campaign(campaign_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM audit_results WHERE campaign_id = ? ORDER BY created_at",
            (campaign_id,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["field_scores"] = json.loads(d["field_scores"] or "{}")
        d["issue_tags"]   = json.loads(d["issue_tags"] or "[]")
        result.append(d)
    return result


# ─────────────────────────── Bot Failures ────────────────────────

def save_bot_failures(failures: list[dict]):
    with _conn() as con:
        for f in failures:
            con.execute(
                """INSERT OR REPLACE INTO bot_failures
                   (failure_id, call_id, campaign_id, failure_type, failure_reason, confidence_score)
                   VALUES (?,?,?,?,?,?)""",
                (
                    f.get("failure_id", f"FAIL-{uuid.uuid4().hex[:8].upper()}"),
                    f["call_id"], f["campaign_id"],
                    f["failure_type"], f["failure_reason"],
                    f["confidence_score"],
                ),
            )


def clear_failures_for_call(call_id: str):
    with _conn() as con:
        con.execute("DELETE FROM bot_failures WHERE call_id = ?", (call_id,))


def get_failures_for_call(call_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM bot_failures WHERE call_id = ? ORDER BY confidence_score DESC",
            (call_id,)
        ).fetchall()
    return _rows(rows)


def get_failures_for_campaign(campaign_id: str) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM bot_failures WHERE campaign_id = ? ORDER BY detected_at",
            (campaign_id,)
        ).fetchall()
    return _rows(rows)


# ─────────────────────────── Campaign Insights ───────────────────

def save_campaign_insights(campaign_id: str, insights: dict):
    iid = f"INS-{uuid.uuid4().hex[:8].upper()}"
    summary = insights.get("campaign_summary", {})
    with _conn() as con:
        con.execute(
            """INSERT INTO campaign_insights
               (insight_id, campaign_id, avg_qa_score, total_failures, insights_json)
               VALUES (?,?,?,?,?)
               ON CONFLICT(campaign_id) DO UPDATE SET
                   generated_at   = datetime('now'),
                   avg_qa_score   = excluded.avg_qa_score,
                   total_failures = excluded.total_failures,
                   insights_json  = excluded.insights_json""",
            (
                iid, campaign_id,
                summary.get("avg_qa_score", 0),
                summary.get("total_failures", 0),
                json.dumps(insights),
            ),
        )


def get_campaign_insights(campaign_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM campaign_insights WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("insights_json"):
        d["insights_json"] = json.loads(d["insights_json"])
    return d


# ─────────────────────────── Cross-campaign stats ────────────────

def get_stats_for_campaigns(campaign_ids: list[str]) -> dict:
    """Return aggregated stats for a specific subset of campaigns."""
    if not campaign_ids:
        return {"campaigns": 0, "active": 0, "closed": 0,
                "total_calls": 0, "audited": 0, "failures": 0, "avg_score": 0.0}
    placeholders = ",".join("?" * len(campaign_ids))
    with _conn() as con:
        active = con.execute(
            f"SELECT COUNT(*) FROM campaigns WHERE campaign_id IN ({placeholders}) AND status != 'CLOSED'",
            campaign_ids,
        ).fetchone()[0]
        closed = con.execute(
            f"SELECT COUNT(*) FROM campaigns WHERE campaign_id IN ({placeholders}) AND status = 'CLOSED'",
            campaign_ids,
        ).fetchone()[0]
        total_calls = con.execute(
            f"SELECT COUNT(*) FROM calls WHERE campaign_id IN ({placeholders})",
            campaign_ids,
        ).fetchone()[0]
        audited = con.execute(
            f"SELECT COUNT(*) FROM audit_results WHERE campaign_id IN ({placeholders})",
            campaign_ids,
        ).fetchone()[0]
        failures = con.execute(
            f"SELECT COUNT(*) FROM bot_failures WHERE campaign_id IN ({placeholders})",
            campaign_ids,
        ).fetchone()[0]
        avg_score = con.execute(
            f"SELECT AVG(percentage_score) FROM audit_results WHERE campaign_id IN ({placeholders})",
            campaign_ids,
        ).fetchone()[0] or 0
    return {
        "campaigns": len(campaign_ids),
        "active": active,
        "closed": closed,
        "total_calls": total_calls,
        "audited": audited,
        "failures": failures,
        "avg_score": round(avg_score, 2),
    }


def get_platform_stats() -> dict:
    with _conn() as con:
        campaigns  = con.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
        active     = con.execute("SELECT COUNT(*) FROM campaigns WHERE status NOT IN ('CLOSED')").fetchone()[0]
        closed     = con.execute("SELECT COUNT(*) FROM campaigns WHERE status='CLOSED'").fetchone()[0]
        total_calls = con.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
        audited    = con.execute("SELECT COUNT(*) FROM audit_results").fetchone()[0]
        failures   = con.execute("SELECT COUNT(*) FROM bot_failures").fetchone()[0]
        avg_score  = con.execute(
            "SELECT AVG(percentage_score) FROM audit_results"
        ).fetchone()[0] or 0
    return {
        "campaigns": campaigns, "active": active, "closed": closed,
        "total_calls": total_calls, "audited": audited,
        "failures": failures, "avg_score": round(avg_score, 2),
    }
