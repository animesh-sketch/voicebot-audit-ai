"""
insight_engine.py — Analytics Engine.
Aggregates audit results and bot failure data into a structured
insight payload for the campaign close report.
"""
from datetime import datetime

import numpy as np
import pandas as pd

from database.db_manager import (
    get_campaign,
    get_calls_for_campaign,
    get_audits_for_campaign,
    get_failures_for_campaign,
    get_campaign_progress,
    get_template_fields,
    save_campaign_insights,
    clear_failures_for_call,
    save_bot_failures,
)
from database.models import CONVIN_SENSE_PASS_THRESHOLD
from analytics.failure_engine import analyze_call_failures
from analytics.action_plan_generator import generate_action_plan


def _score_to_numeric(val, max_score: float, pass_value: str = "Yes") -> float | None:
    """Convert a field answer to a numeric score (or None for NA/excluded)."""
    if val is None:
        return None
    if isinstance(val, str):
        if val in ("NA",):
            return None
        if val == "FATAL":
            return 0.0
        return max_score if val == pass_value else 0.0
    return float(val)


def generate_campaign_insights(campaign_id: str) -> dict:
    """
    Main entry point called on campaign close.
    1. Re-runs failure detection on every call.
    2. Computes all analytics.
    3. Generates action plan.
    4. Persists and returns the full insight payload.
    """
    campaign = get_campaign(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found.")

    progress = get_campaign_progress(campaign_id)
    calls    = get_calls_for_campaign(campaign_id)
    audits   = get_audits_for_campaign(campaign_id)
    fields   = get_template_fields(campaign_id)

    # ── Step 1: (Re-)run failure detection on all calls ──────────
    all_failures = []
    for call in calls:
        clear_failures_for_call(call["call_id"])
        detected = analyze_call_failures(
            call["call_id"], campaign_id,
            call.get("transcript") or "",
            call.get("duration") or 0,
        )
        all_failures.extend(detected)
    if all_failures:
        save_bot_failures(all_failures)

    # ── Step 2: Build DataFrames ──────────────────────────────────
    calls_df   = pd.DataFrame(calls)   if calls   else pd.DataFrame()
    audits_df  = pd.DataFrame(audits)  if audits  else pd.DataFrame()
    failure_df = pd.DataFrame(all_failures) if all_failures else pd.DataFrame()

    # ── Step 3: QA Score Analysis ─────────────────────────────────
    qa_analysis = _compute_qa_analysis(audits_df, fields)

    # ── Step 4: Failure Analysis ──────────────────────────────────
    n_calls = max(progress["total"], 1)
    failure_analysis = _compute_failure_analysis(failure_df, n_calls)

    # ── Step 5: Entity capture ────────────────────────────────────
    entity_accuracy = _compute_entity_accuracy(audits_df, fields)

    # ── Step 6: Lead classification ───────────────────────────────
    lead_classification = _compute_lead_classification(calls_df, audits_df)

    # ── Step 7: Conversation analysis ────────────────────────────
    conversation_analysis = _compute_conversation_analysis(calls_df, failure_df)

    # ── Step 8: Issue tag analysis ────────────────────────────────
    issue_analysis = _compute_issue_tags(audits_df)

    # ── Step 9: Action plan ───────────────────────────────────────
    action_plan = generate_action_plan(
        qa_analysis, failure_analysis, entity_accuracy,
        conversation_analysis, campaign.get("campaign_name", ""),
        lead_classification=lead_classification,
    )

    campaign_summary = {
        "campaign_id":    campaign_id,
        "campaign_name":  campaign.get("campaign_name"),
        "client_name":    campaign.get("client_name"),
        "total_calls":    progress["total"],
        "audited_calls":  progress["audited"],
        "avg_qa_score":   qa_analysis.get("avg_score", 0),
        "pass_rate":      qa_analysis.get("pass_rate", 0),
        "total_failures": failure_analysis.get("total_unique_failure_calls", 0),
        "failure_rate":   failure_analysis.get("call_failure_rate", 0),
    }

    payload = {
        "campaign_summary":       campaign_summary,
        "qa_analysis":            qa_analysis,
        "failure_analysis":       failure_analysis,
        "entity_accuracy":        entity_accuracy,
        "lead_classification":    lead_classification,
        "conversation_analysis":  conversation_analysis,
        "issue_analysis":         issue_analysis,
        "action_plan":            action_plan,
        "generated_at":           datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_campaign_insights(campaign_id, payload)
    return payload


# ─────────────────────────── QA Scoring ──────────────────────────

def _compute_qa_analysis(audits_df: pd.DataFrame, fields: list[dict]) -> dict:
    if audits_df.empty or "percentage_score" not in audits_df.columns:
        return {"avg_score": 0, "min_score": 0, "max_score": 0, "std_dev": 0,
                "pass_rate": 0, "score_distribution": {}, "field_breakdown": []}

    scores = audits_df["percentage_score"].dropna()
    avg    = float(scores.mean())
    pass_r = float((scores >= CONVIN_SENSE_PASS_THRESHOLD).mean() * 100)

    # Score distribution
    bins   = [0, 40, 55, 70, 80, 101]
    labels = ["0–40 (Poor)", "40–55 (Below Avg)", "55–70 (Average)", "70–80 (Near Pass)", "80–100 (Pass)"]
    cut    = pd.cut(scores, bins=bins, labels=labels, right=False)
    dist   = cut.value_counts().reindex(labels, fill_value=0).to_dict()

    # Per-field breakdown (handles both numeric legacy and Yes/No string values)
    import json as _json
    field_breakdown = []
    for field in fields:
        fid      = field["field_id"]
        max_s    = float(field.get("weight_percent") or field.get("max_score") or 10)
        pass_val = field.get("pass_value") or "Yes"
        is_fatal = bool(int(field.get("is_fatal") or 0))
        if is_fatal:
            continue  # exclude FATAL-only params from numeric breakdown

        field_scores = []
        for _, row in audits_df.iterrows():
            fs = row.get("field_scores") or {}
            if isinstance(fs, str):
                fs = _json.loads(fs)
            if fid in fs:
                numeric = _score_to_numeric(fs[fid], max_s, pass_val)
                if numeric is not None:
                    field_scores.append(numeric)
        if field_scores:
            avg_f = sum(field_scores) / len(field_scores)
            field_breakdown.append({
                "field_name":  field["field_name"],
                "avg_score":   round(avg_f, 2),
                "max_score":   max_s,
                "percentage":  round(avg_f / max_s * 100, 2) if max_s else 0,
                "count":       len(field_scores),
            })

    return {
        "avg_score":          round(avg, 2),
        "min_score":          round(float(scores.min()), 2),
        "max_score":          round(float(scores.max()), 2),
        "std_dev":            round(float(scores.std()), 2) if len(scores) > 1 else 0,
        "pass_rate":          round(pass_r, 2),
        "score_distribution": dist,
        "field_breakdown":    field_breakdown,
        "scores_list":        scores.tolist(),
    }


# ─────────────────────────── Failure Analysis ────────────────────

def _compute_failure_analysis(failure_df: pd.DataFrame, n_calls: int) -> dict:
    if failure_df.empty:
        return {
            "total_failures": 0,
            "failure_distribution": {},
            "failure_rates": {},
            "call_failure_rate": 0,
            "total_unique_failure_calls": 0,
            "avg_confidence": 0,
            "top_failures": [],
        }

    dist = failure_df["failure_type"].value_counts().to_dict()
    unique_calls = failure_df["call_id"].nunique()
    avg_conf = float(failure_df["confidence_score"].mean())

    # Failure rate per type (% of calls affected)
    per_call = failure_df.groupby("failure_type")["call_id"].nunique().to_dict()
    rates    = {k: round(v / n_calls, 3) for k, v in per_call.items()}

    # Top 5 most confident failures
    top = (
        failure_df.nlargest(5, "confidence_score")[
            ["failure_type", "failure_reason", "confidence_score", "call_id"]
        ].to_dict("records")
    )

    return {
        "total_failures":             int(failure_df.shape[0]),
        "failure_distribution":       {k: int(v) for k, v in dist.items()},
        "failure_rates":              rates,
        "call_failure_rate":          round(unique_calls / n_calls, 3),
        "total_unique_failure_calls": int(unique_calls),
        "avg_confidence":             round(avg_conf, 3),
        "top_failures":               top,
    }


# ─────────────────────────── Entity Accuracy ─────────────────────

def _compute_entity_accuracy(audits_df: pd.DataFrame, fields: list[dict]) -> dict:
    import json as _json

    # For Convin Sense framework: parameter #3 "All required entities captured correctly?"
    # For legacy: match by category or keyword
    entity_keywords = ["entity", "capture", "name", "address", "email", "phone",
                       "contact", "route", "passenger", "sailing", "date", "count"]
    entity_fields = [
        f for f in fields
        if (f.get("field_category") or "").lower() == "entity capture"
        or any(kw in f["field_name"].lower() for kw in entity_keywords)
        or "entities captured" in f["field_name"].lower()
    ]

    empty = {"capture_rate": 0, "avg_entity_score": 0, "field_count": len(entity_fields), "field_breakdown": []}
    if not entity_fields or audits_df.empty:
        return empty

    all_entity_scores: list[float] = []
    field_breakdown: list[dict] = []

    for field in entity_fields:
        fid      = field["field_id"]
        max_s    = float(field.get("weight_percent") or field.get("max_score") or 10)
        pass_val = field.get("pass_value") or "Yes"
        scores   = []
        for _, row in audits_df.iterrows():
            fs = row.get("field_scores") or {}
            if isinstance(fs, str):
                fs = _json.loads(fs)
            if fid in fs:
                numeric = _score_to_numeric(fs[fid], max_s, pass_val)
                if numeric is not None:
                    scores.append(numeric)
                    all_entity_scores.append(numeric / max_s if max_s else 0)

        if scores:
            avg_raw = sum(scores) / len(scores)
            pct     = round(avg_raw / max_s * 100, 2) if max_s else 0
            field_breakdown.append({
                "field_name":  field["field_name"],
                "avg_score":   round(avg_raw, 2),
                "max_score":   max_s,
                "percentage":  pct,
                "count":       len(scores),
            })

    if not all_entity_scores:
        return empty

    capture_rate = sum(1 for s in all_entity_scores if s >= 0.6) / len(all_entity_scores)
    avg_entity   = sum(all_entity_scores) / len(all_entity_scores) * 100

    return {
        "capture_rate":     round(capture_rate, 3),
        "avg_entity_score": round(avg_entity, 2),
        "field_count":      len(entity_fields),
        "field_breakdown":  field_breakdown,
    }


# ─────────────────────────── Lead Classification ─────────────────

def _compute_lead_classification(calls_df: pd.DataFrame, audits_df: pd.DataFrame = None) -> dict:
    if calls_df.empty or "lead_category" not in calls_df.columns:
        return {"distribution": {}, "hot_lead_rate": 0, "total": 0,
                "mismatch_count": 0, "mismatch_rate": 0, "mismatch_pairs": []}

    dist  = calls_df["lead_category"].value_counts().to_dict()
    total = len(calls_df)
    hot   = dist.get("HOT_LEAD", 0)

    result = {
        "distribution":  {k: int(v) for k, v in dist.items()},
        "hot_lead_rate": round(hot / total, 3) if total else 0,
        "total":         total,
        "mismatch_count": 0,
        "mismatch_rate":  0,
        "mismatch_pairs": [],
    }

    # Compute mismatch between bot classification and auditor assessment
    if (
        audits_df is not None
        and not audits_df.empty
        and "lead_audit_category" in audits_df.columns
        and "call_id" in audits_df.columns
        and "call_id" in calls_df.columns
    ):
        merged = calls_df[["call_id", "lead_category"]].merge(
            audits_df[["call_id", "lead_audit_category"]].dropna(subset=["lead_audit_category"]),
            on="call_id",
            how="inner",
        )
        if not merged.empty:
            mismatches = merged[
                merged["lead_audit_category"].notna()
                & (merged["lead_audit_category"] != "")
                & (merged["lead_category"] != merged["lead_audit_category"])
            ]
            mismatch_count = len(mismatches)
            mismatch_rate  = round(mismatch_count / len(merged), 3) if len(merged) else 0

            pairs: list[dict] = []
            for _, row in mismatches.iterrows():
                pairs.append({
                    "call_id":    row["call_id"],
                    "bot_label":  row["lead_category"],
                    "audit_label": row["lead_audit_category"],
                })

            result["mismatch_count"] = mismatch_count
            result["mismatch_rate"]  = mismatch_rate
            result["mismatch_pairs"] = pairs[:20]  # cap at 20 examples

    return result


# ─────────────────────────── Conversation Analysis ───────────────

def _compute_conversation_analysis(calls_df: pd.DataFrame, failure_df: pd.DataFrame) -> dict:
    result: dict = {"avg_duration": 0, "short_calls": 0, "drop_off": {}}

    if calls_df.empty or "duration" not in calls_df.columns:
        return result

    durations = calls_df["duration"].dropna().astype(float)
    result["avg_duration"] = round(float(durations.mean()), 1) if len(durations) else 0
    result["short_calls"]  = int((durations < 60).sum())
    result["long_calls"]   = int((durations >= 300).sum())

    # Drop-off stages based on duration thirds
    n = len(calls_df)
    if not failure_df.empty and "failure_type" in failure_df.columns:
        drops = failure_df[failure_df["failure_type"] == "Conversation Drop"]
        result["conversation_drops"] = int(len(drops))
        result["drop_rate"]          = round(len(drops) / max(n, 1), 3)
    else:
        result["conversation_drops"] = 0
        result["drop_rate"]          = 0

    # Duration distribution
    bins   = [0, 60, 120, 180, 300, float("inf")]
    labels = ["<1 min", "1–2 min", "2–3 min", "3–5 min", "5+ min"]
    if len(durations):
        cut = pd.cut(durations, bins=bins, labels=labels, right=False)
        result["duration_distribution"] = cut.value_counts().reindex(labels, fill_value=0).to_dict()

    return result


# ─────────────────────────── Issue Tags ──────────────────────────

def _compute_issue_tags(audits_df: pd.DataFrame) -> dict:
    import json
    if audits_df.empty or "issue_tags" not in audits_df.columns:
        return {"tag_distribution": {}, "total_tagged_calls": 0}

    all_tags: list = []
    tagged   = 0
    for _, row in audits_df.iterrows():
        tags = row.get("issue_tags") or []
        if isinstance(tags, str):
            tags = json.loads(tags)
        if tags:
            tagged += 1
            all_tags.extend(tags)

    from collections import Counter
    dist = dict(Counter(all_tags))

    return {
        "tag_distribution":    dist,
        "total_tagged_calls":  tagged,
    }
