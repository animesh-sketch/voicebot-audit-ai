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


class IssueTag(str, Enum):
    LATENCY                  = "Latency"
    HALLUCINATION            = "Hallucination"
    STT_ERROR                = "STT Error"
    INTENT_MISCLASSIFICATION = "Intent Misclassification"
    CONVERSATION_DROP        = "Conversation Drop"


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
}

FAILURE_TYPE_COLORS = {
    FailureType.LATENCY.value:                  "#F39C12",
    FailureType.HALLUCINATION.value:            "#E74C3C",
    FailureType.ENTITY_CAPTURE.value:           "#C0392B",
    FailureType.INTENT_MISCLASSIFICATION.value: "#2980B9",
    FailureType.CONVERSATION_DROP.value:        "#E67E22",
    FailureType.LOOP_RESPONSE.value:            "#8E44AD",
    FailureType.LANGUAGE_DETECTION.value:       "#16A085",
    FailureType.CLOSURE_FAILURE.value:          "#7F8C8D",
}

LEAD_CATEGORY_COLORS = {
    LeadCategory.HOT_LEAD.value:           "#E74C3C",
    LeadCategory.WARM_LEAD.value:          "#F39C12",
    LeadCategory.COLD_LEAD.value:          "#3498DB",
    LeadCategory.NOT_INTERESTED.value:     "#7F8C8D",
    LeadCategory.CALLBACK_REQUESTED.value: "#27AE60",
    LeadCategory.ALREADY_CUSTOMER.value:   "#9B59B6",
    LeadCategory.WRONG_NUMBER.value:       "#BDC3C7",
    LeadCategory.UNKNOWN.value:            "#ECF0F1",
}

STATUS_COLORS = {
    CampaignStatus.ACTIVE.value:         "#27AE60",
    CampaignStatus.IN_PROGRESS.value:    "#2980B9",
    CampaignStatus.READY_TO_CLOSE.value: "#F39C12",
    CampaignStatus.CLOSED.value:         "#7F8C8D",
}
