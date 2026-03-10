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
from analytics.failure_engine import analyze_call_failures
from analytics.action_plan_generator import generate_action_plan


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
    lead_classification = _compute_lead_classification(calls_df)

    # ── Step 7: Conversation analysis ────────────────────────────
    conversation_analysis = _compute_conversation_analysis(calls_df, failure_df)

    # ── Step 8: Issue tag analysis ────────────────────────────────
    issue_analysis = _compute_issue_tags(audits_df)

    # ── Step 9: Action plan ───────────────────────────────────────
    action_plan = generate_action_plan(
        qa_analysis, failure_analysis, entity_accuracy,
        conversation_analysis, campaign.get("campaign_name", "")
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
    pass_r = float((scores >= 70).mean() * 100)

    # Score distribution
    bins   = [0, 40, 55, 70, 85, 101]
    labels = ["0–40 (Poor)", "40–55 (Below Avg)", "55–70 (Average)", "70–85 (Good)", "85–100 (Excellent)"]
    cut    = pd.cut(scores, bins=bins, labels=labels, right=False)
    dist   = cut.value_counts().reindex(labels, fill_value=0).to_dict()

    # Per-field breakdown
    field_breakdown = []
    for field in fields:
        fid  = field["field_id"]
        max_s = field["max_score"]
        field_scores = []
        for _, row in audits_df.iterrows():
            fs = row.get("field_scores") or {}
            if isinstance(fs, str):
                import json; fs = json.loads(fs)
            if fid in fs:
                field_scores.append(float(fs[fid]))
        if field_scores:
            avg_f = sum(field_scores) / len(field_scores)
            field_breakdown.append({
                "field_name":  field["field_name"],
                "avg_score":   round(avg_f, 2),
                "max_score":   max_s,
                "percentage":  round(avg_f / max_s * 100, 2),
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
    # Find entity-related fields (heuristic match)
    entity_keywords = ["entity", "capture", "name", "address", "email", "phone", "contact"]
    entity_fields   = [
        f for f in fields
        if any(kw in f["field_name"].lower() for kw in entity_keywords)
    ]

    if not entity_fields or audits_df.empty:
        return {"capture_rate": 0, "avg_entity_score": 0, "field_count": len(entity_fields)}

    import json
    entity_scores = []
    for _, row in audits_df.iterrows():
        fs = row.get("field_scores") or {}
        if isinstance(fs, str):
            fs = json.loads(fs)
        for field in entity_fields:
            fid = field["field_id"]
            if fid in fs:
                pct = float(fs[fid]) / float(field["max_score"])
                entity_scores.append(pct)

    if not entity_scores:
        return {"capture_rate": 0, "avg_entity_score": 0, "field_count": len(entity_fields)}

    capture_rate  = sum(1 for s in entity_scores if s >= 0.6) / len(entity_scores)
    avg_entity    = sum(entity_scores) / len(entity_scores) * 100

    return {
        "capture_rate":    round(capture_rate, 3),
        "avg_entity_score": round(avg_entity, 2),
        "field_count":     len(entity_fields),
    }


# ─────────────────────────── Lead Classification ─────────────────

def _compute_lead_classification(calls_df: pd.DataFrame) -> dict:
    if calls_df.empty or "lead_category" not in calls_df.columns:
        return {"distribution": {}, "hot_lead_rate": 0, "total": 0}

    dist = calls_df["lead_category"].value_counts().to_dict()
    total = len(calls_df)
    hot   = dist.get("HOT_LEAD", 0)

    return {
        "distribution":  {k: int(v) for k, v in dist.items()},
        "hot_lead_rate": round(hot / total, 3) if total else 0,
        "total":         total,
    }


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
