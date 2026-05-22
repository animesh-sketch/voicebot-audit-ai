"""
models.py — Enums, constants, and domain types for VoiceBot Audit AI.
"""
from enum import Enum


class CampaignStatus(str, Enum):
    ACTIVE          = "ACTIVE"
    IN_PROGRESS     = "IN_PROGRESS"
    READY_TO_CLOSE  = "READY_TO_CLOSE"
    CLOSED          = "CLOSED"


class LeadCategory(str, Enum):
    HOT_LEAD            = "HOT_LEAD"
    WARM_LEAD           = "WARM_LEAD"
    COLD_LEAD           = "COLD_LEAD"
    NOT_INTERESTED      = "NOT_INTERESTED"
    CALLBACK_REQUESTED  = "CALLBACK_REQUESTED"
    ALREADY_CUSTOMER    = "ALREADY_CUSTOMER"
    WRONG_NUMBER        = "WRONG_NUMBER"
    UNKNOWN             = "UNKNOWN"


class FailureType(str, Enum):
    LATENCY                 = "Latency Failure"
    HALLUCINATION           = "Hallucination"
    ENTITY_CAPTURE          = "Entity Capture Failure"
    INTENT_MISCLASSIFICATION = "Intent Misclassification"
    CONVERSATION_DROP       = "Conversation Drop"
    LOOP_RESPONSE           = "Loop Response"
    LANGUAGE_DETECTION      = "Language Detection Failure"
    CLOSURE_FAILURE         = "Closure Failure"


class FieldCategory(str, Enum):
    AI_ISSUES           = "AI Issues"
    ENTITY_CAPTURE      = "Entity Capture"
    LEAD_CLASSIFICATION = "Lead Classification"
    CALL_QUALITY        = "Call Quality"
    COMPLIANCE          = "Compliance"
    GENERAL             = "General"


class IssueTag(str, Enum):
    LATENCY                  = "Latency"
    HALLUCINATION            = "Hallucination"
    STT_ERROR                = "STT Error"
    INTENT_MISCLASSIFICATION = "Intent Misclassification"
    CONVERSATION_DROP        = "Conversation Drop"
    LANGUAGE_SWITCH          = "Language Switch"


# ── Failure detection thresholds ───────────────────────────────────
FAILURE_CONFIDENCE_THRESHOLD = 0.35

FAILURE_RATE_THRESHOLDS = {
    "critical": {
        FailureType.LATENCY.value:                  0.30,
        FailureType.HALLUCINATION.value:             0.15,
        FailureType.ENTITY_CAPTURE.value:            0.30,
        FailureType.CONVERSATION_DROP.value:         0.25,
        FailureType.LOOP_RESPONSE.value:             0.20,
        FailureType.INTENT_MISCLASSIFICATION.value:  0.25,
        FailureType.LANGUAGE_DETECTION.value:        0.20,
        FailureType.CLOSURE_FAILURE.value:           0.30,
    },
    "warning": {
        FailureType.LATENCY.value:                  0.15,
        FailureType.HALLUCINATION.value:             0.08,
        FailureType.ENTITY_CAPTURE.value:            0.15,
        FailureType.CONVERSATION_DROP.value:         0.12,
        FailureType.LOOP_RESPONSE.value:             0.10,
        FailureType.INTENT_MISCLASSIFICATION.value:  0.12,
        FailureType.LANGUAGE_DETECTION.value:        0.10,
        FailureType.CLOSURE_FAILURE.value:           0.15,
    },
}

# ── Action plan thresholds ─────────────────────────────────────────
QA_SCORE_THRESHOLDS = {
    "critical": 55.0,
    "warning":  70.0,
    "good":     85.0,
}

ENTITY_CAPTURE_WARNING = 0.70   # below 70% accuracy → flag
DROP_RATE_WARNING      = 0.20   # above 20% drop rate → flag

# ── Issue tag → failure type mapping ──────────────────────────────
ISSUE_TAG_COLORS = {
    IssueTag.LATENCY.value:                  "#F39C12",
    IssueTag.HALLUCINATION.value:            "#E74C3C",
    IssueTag.STT_ERROR.value:                "#8E44AD",
    IssueTag.INTENT_MISCLASSIFICATION.value: "#2980B9",
    IssueTag.CONVERSATION_DROP.value:        "#E67E22",
    IssueTag.LANGUAGE_SWITCH.value:          "#16A085",
}

FAILURE_TYPE_COLORS = {
    FailureType.LATENCY.value:                  "#FBBF24",
    FailureType.HALLUCINATION.value:            "#F472B6",
    FailureType.ENTITY_CAPTURE.value:           "#EC4899",
    FailureType.INTENT_MISCLASSIFICATION.value: "#0EA5E9",
    FailureType.CONVERSATION_DROP.value:        "#FB923C",
    FailureType.LOOP_RESPONSE.value:            "#A78BFA",
    FailureType.LANGUAGE_DETECTION.value:       "#00D68F",
    FailureType.CLOSURE_FAILURE.value:          "#64748B",
}

LEAD_CATEGORY_COLORS = {
    LeadCategory.HOT_LEAD.value:           "#EC4899",
    LeadCategory.WARM_LEAD.value:          "#FBBF24",
    LeadCategory.COLD_LEAD.value:          "#38BDF8",
    LeadCategory.NOT_INTERESTED.value:     "#64748B",
    LeadCategory.CALLBACK_REQUESTED.value: "#00D68F",
    LeadCategory.ALREADY_CUSTOMER.value:   "#A78BFA",
    LeadCategory.WRONG_NUMBER.value:       "#475569",
    LeadCategory.UNKNOWN.value:            "#1E293B",
}

STATUS_COLORS = {
    CampaignStatus.ACTIVE.value:         "#00D68F",
    CampaignStatus.IN_PROGRESS.value:    "#0EA5E9",
    CampaignStatus.READY_TO_CLOSE.value: "#F472B6",
    CampaignStatus.CLOSED.value:         "#64748B",
}
