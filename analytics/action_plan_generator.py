"""
action_plan_generator.py — Generates prioritised, actionable improvement
recommendations from campaign insight data.
"""
from database.models import (
    FAILURE_RATE_THRESHOLDS,
    QA_SCORE_THRESHOLDS,
    ENTITY_CAPTURE_WARNING,
    FailureType,
)


# ── Priority ordering ─────────────────────────────────────────────
_PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

# ── Action templates per failure type ────────────────────────────
_FAILURE_ACTIONS = {
    FailureType.LATENCY.value: {
        "title":   "Reduce Bot Response Latency",
        "actions": [
            "Profile and optimise slow NLU / TTS pipeline stages.",
            "Implement response streaming instead of full-sentence synthesis.",
            "Add aggressive caching for common intent responses.",
            "Set a hard latency SLA of < 800 ms per bot turn.",
        ],
        "owner":    "Engineering Team",
        "timeline": "2 weeks",
    },
    FailureType.HALLUCINATION.value: {
        "title":   "Eliminate Bot Hallucinations",
        "actions": [
            "Audit and update the knowledge base — remove outdated entries.",
            "Add confidence gating: bot must flag low-confidence answers.",
            "Implement factual grounding by constraining responses to verified KB.",
            "Run weekly hallucination regression tests using golden datasets.",
        ],
        "owner":    "NLU / Content Team",
        "timeline": "1 week (immediate KB patch)",
    },
    FailureType.ENTITY_CAPTURE.value: {
        "title":   "Improve Entity Extraction Accuracy",
        "actions": [
            "Retrain NER model on domain-specific entity types.",
            "Add multi-attempt confirmation slot-filling logic.",
            "Use phonetic fuzzy matching for name/address recognition.",
            "Implement proactive spelling-out prompts after 1 failed attempt.",
        ],
        "owner":    "ML / NLU Team",
        "timeline": "3 weeks",
    },
    FailureType.INTENT_MISCLASSIFICATION.value: {
        "title":   "Improve Intent Classification",
        "actions": [
            "Add more training utterances for misclassified intents.",
            "Review and consolidate overlapping intents in the intent taxonomy.",
            "Lower confidence thresholds and add fallback clarification prompts.",
            "Introduce an 'intent clarification' dialog turn before acting.",
        ],
        "owner":    "ML Team",
        "timeline": "2–3 weeks",
    },
    FailureType.CONVERSATION_DROP.value: {
        "title":   "Reduce Conversation Drop Rate",
        "actions": [
            "Implement proactive re-engagement messages after silence > 5s.",
            "Add graceful handoff to human agent after 2 unanswered turns.",
            "Improve session recovery to resume dropped calls.",
            "Instrument drop points with detailed logging for root cause analysis.",
        ],
        "owner":    "Conversation Design / Engineering",
        "timeline": "1–2 weeks",
    },
    FailureType.LOOP_RESPONSE.value: {
        "title":   "Fix Bot Loop / Repetition Bugs",
        "actions": [
            "Add a response history tracker to prevent repeating same turn.",
            "Implement progressive escalation: 1st repeat → clarify, 2nd → escalate.",
            "Audit dialog state machine for infinite loop conditions.",
            "Add a maximum-turns-per-intent circuit breaker.",
        ],
        "owner":    "Engineering / Conversation Design",
        "timeline": "1 week",
    },
    FailureType.LANGUAGE_DETECTION.value: {
        "title":   "Enhance Multi-Language Support",
        "actions": [
            "Enable automatic language detection on every user turn.",
            "Deploy language-specific NLU models for top detected languages.",
            "Add a language preference prompt at call start.",
            "Gracefully escalate to bilingual human agent when bot cannot switch.",
        ],
        "owner":    "ML / Operations",
        "timeline": "3–4 weeks",
    },
    FailureType.CLOSURE_FAILURE.value: {
        "title":   "Enforce Proper Call Closure",
        "actions": [
            "Add a mandatory closure state to all dialog flows.",
            "Implement a post-resolution summary + confirmation step.",
            "Set a call-end policy: always provide next steps before goodbye.",
            "Log and alert when calls end without a closure turn.",
        ],
        "owner":    "Conversation Design",
        "timeline": "1 week",
    },
}


def _make_item(priority: str, category: str, finding: str, recommendation: str,
               actions: list[str], owner: str, timeline: str, impact: str) -> dict:
    return {
        "priority":       priority,
        "category":       category,
        "finding":        finding,
        "recommendation": recommendation,
        "actions":        actions,
        "owner":          owner,
        "timeline":       timeline,
        "expected_impact": impact,
    }


def generate_action_plan(
    qa_analysis:          dict,
    failure_analysis:     dict,
    entity_accuracy:      dict,
    conversation_analysis: dict,
    campaign_name:        str = "",
) -> list[dict]:
    """
    Returns a list of action items sorted by priority.
    """
    items: list[dict] = []
    rates   = failure_analysis.get("failure_rates", {})
    crit_t  = FAILURE_RATE_THRESHOLDS["critical"]
    warn_t  = FAILURE_RATE_THRESHOLDS["warning"]

    avg_score = qa_analysis.get("avg_score", 100)

    # ── Overall QA score ─────────────────────────────────────────
    if avg_score < QA_SCORE_THRESHOLDS["critical"]:
        items.append(_make_item(
            "CRITICAL", "Overall Quality",
            f"Campaign average QA score is critically low at {avg_score:.1f}%.",
            "Halt campaign and conduct a full quality review before resuming.",
            [
                "Suspend further outbound calls until root causes are identified.",
                "Conduct emergency review of bot scripts and NLU models.",
                "Retrain agents / adjust bot configuration immediately.",
                "Re-audit a sample of 10% of closed calls to validate findings.",
            ],
            "Campaign Management", "Immediately",
            "Prevent further low-quality customer interactions.",
        ))
    elif avg_score < QA_SCORE_THRESHOLDS["warning"]:
        items.append(_make_item(
            "HIGH", "Overall Quality",
            f"Campaign average QA score ({avg_score:.1f}%) is below the 70% quality threshold.",
            "Prioritise quality improvement initiatives across all bot components.",
            [
                "Schedule a QA review meeting with bot team and operations.",
                "Identify the bottom 20% scoring calls and analyse failure patterns.",
                "Set a quality improvement target of +10 pts in next sprint.",
            ],
            "QA Lead", "1 week",
            "Bring average QA score above 70% within 2 sprints.",
        ))

    # ── Per-failure-type actions ──────────────────────────────────
    for ftype, action_template in _FAILURE_ACTIONS.items():
        rate  = rates.get(ftype, 0)
        crit  = crit_t.get(ftype, 0.3)
        warn  = warn_t.get(ftype, 0.15)

        if rate == 0:
            continue

        if rate >= crit:
            priority = "CRITICAL" if rate >= crit * 1.5 else "HIGH"
        elif rate >= warn:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        pct_str = f"{rate * 100:.0f}%"
        items.append(_make_item(
            priority,
            "Bot Intelligence",
            f"{ftype} detected in {pct_str} of calls.",
            action_template["title"],
            action_template["actions"],
            action_template["owner"],
            action_template["timeline"],
            f"Reduce {ftype} rate from {pct_str} to < {warn * 100:.0f}%.",
        ))

    # ── Entity capture ────────────────────────────────────────────
    capture_rate = entity_accuracy.get("capture_rate", 1.0)
    if capture_rate < ENTITY_CAPTURE_WARNING:
        items.append(_make_item(
            "HIGH" if capture_rate < 0.50 else "MEDIUM",
            "Data Quality",
            f"Entity capture accuracy is low at {capture_rate * 100:.0f}%.",
            "Improve entity extraction to capture critical customer data reliably.",
            [
                "Retrain entity extraction model with campaign-specific examples.",
                "Add explicit entity confirmation turns to all dialog flows.",
                "Implement structured input collection (DTMF / form-fill) as fallback.",
            ],
            "ML Team", "2 weeks",
            f"Improve entity capture from {capture_rate * 100:.0f}% to > 85%.",
        ))

    # ── Conversation drop ─────────────────────────────────────────
    drop_rate = conversation_analysis.get("drop_rate", 0)
    if drop_rate > 0.20:
        items.append(_make_item(
            "HIGH",
            "Conversation Flow",
            f"High conversation drop rate: {drop_rate * 100:.0f}% of calls dropped.",
            "Reduce drop rate through improved bot resilience and recovery flows.",
            _FAILURE_ACTIONS[FailureType.CONVERSATION_DROP.value]["actions"],
            "Engineering / Conversation Design",
            "1–2 weeks",
            f"Reduce drop rate from {drop_rate * 100:.0f}% to < 10%.",
        ))

    # ── Low field scores ──────────────────────────────────────────
    for fb in qa_analysis.get("field_breakdown", []):
        if fb["percentage"] < 55:
            items.append(_make_item(
                "MEDIUM",
                "Training",
                f"Field \"{fb['field_name']}\" has a low average score of {fb['percentage']:.0f}%.",
                f"Conduct targeted improvement for '{fb['field_name']}' capability.",
                [
                    f"Review all low-scoring calls for '{fb['field_name']}'.",
                    "Update bot dialog logic / prompts for this capability.",
                    "Add more training data for this scenario.",
                ],
                "QA / Training", "2 weeks",
                f"Raise '{fb['field_name']}' score above 70%.",
            ))

    # ── Positive recognition ──────────────────────────────────────
    top_fields = [f for f in qa_analysis.get("field_breakdown", []) if f["percentage"] >= 85]
    if top_fields:
        names = ", ".join(f["field_name"] for f in top_fields[:3])
        items.append(_make_item(
            "LOW",
            "Recognition",
            f"Strong performance in: {names}.",
            "Document and replicate best practices from high-scoring areas.",
            [
                "Extract winning conversation patterns from top-scoring calls.",
                "Use as templates / few-shot examples for low-scoring dialog flows.",
                "Share success patterns in team knowledge base.",
            ],
            "QA Lead", "Ongoing",
            "Propagate best practices across the campaign.",
        ))

    # Sort by priority
    items.sort(key=lambda x: _PRIORITY_ORDER.get(x["priority"], 9))
    return items
