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


class Tier(str, Enum):
    CRITICAL  = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    QUALITY   = "QUALITY"


class ResponseType(str, Enum):
    YES_NO    = "YES_NO"
    YES_NO_NA = "YES_NO_NA"
    NO_FATAL  = "NO_FATAL"


# ── Convin Sense Audit Framework v0.3 — 25 parameters ─────────────
CONVIN_SENSE_FRAMEWORK = [
    # ── TIER 1 — CRITICAL (9 params, 65% total) ───────────────────
    {"no":  1, "name": "Lead metrices accurately selected?",
     "tier": "CRITICAL",  "weight_percent": 12.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no":  2, "name": "Lead qualified accurately?",
     "tier": "CRITICAL",  "weight_percent":  8.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no":  3, "name": "All required entities captured correctly?",
     "tier": "CRITICAL",  "weight_percent":  4.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no":  4, "name": "Context passed correctly across conversation turns?",
     "tier": "CRITICAL",  "weight_percent": 11.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no":  5, "name": "Any flow issue during the conversation?",
     "tier": "CRITICAL",  "weight_percent": 10.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no":  6, "name": "Bot restarted conversation unnecessarily?",
     "tier": "CRITICAL",  "weight_percent":  8.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no":  7, "name": "WhatsApp message content appropriate and well understood?",
     "tier": "CRITICAL",  "weight_percent":  5.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no":  8, "name": "Follow-up completed within specified time?",
     "tier": "CRITICAL",  "weight_percent":  4.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no":  9, "name": "Any latency issue during the conversation?",
     "tier": "CRITICAL",  "weight_percent":  3.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    # ── TIER 2 — IMPORTANT (8 params, 25% total) ──────────────────
    {"no": 10, "name": "Bot repeated responses or questions unnecessarily?",
     "tier": "IMPORTANT", "weight_percent":  5.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 11, "name": "Unnecessary repeated calls in short timeframe?",
     "tier": "IMPORTANT", "weight_percent":  3.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 12, "name": "Background noise affecting audio clarity?",
     "tier": "IMPORTANT", "weight_percent":  2.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 13, "name": "Any STT issues observed?",
     "tier": "IMPORTANT", "weight_percent":  3.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 14, "name": "TTS quality clear and understandable?",
     "tier": "IMPORTANT", "weight_percent":  3.0, "response_type": "YES_NO_NA", "is_fatal": False, "pass_value": "Yes"},
    {"no": 15, "name": "Bot switched language correctly per customer preference?",
     "tier": "IMPORTANT", "weight_percent":  3.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no": 16, "name": "Bot handled interruption well?",
     "tier": "IMPORTANT", "weight_percent":  3.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no": 17, "name": "Any AI Call Failed?",
     "tier": "IMPORTANT", "weight_percent":  3.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    # ── TIER 3 — QUALITY (5 weighted params + 3 FATAL) ────────────
    {"no": 18, "name": "Any script issues in the transcript?",
     "tier": "QUALITY",   "weight_percent":  2.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 19, "name": "Any bot pronunciation issues affecting clarity?",
     "tier": "QUALITY",   "weight_percent":  2.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 20, "name": "Any WhatsApp template issues?",
     "tier": "QUALITY",   "weight_percent":  2.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    {"no": 21, "name": "WhatsApp/message delivery successful?",
     "tier": "QUALITY",   "weight_percent":  2.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "Yes"},
    {"no": 22, "name": "Any technical/platform issue observed?",
     "tier": "QUALITY",   "weight_percent":  2.0, "response_type": "YES_NO",    "is_fatal": False, "pass_value": "No"},
    # ── FATAL AUTO-FAIL parameters ─────────────────────────────────
    {"no": 23, "name": "Abrupt disconnection before logical closure?",
     "tier": "QUALITY",   "weight_percent":  0.0, "response_type": "NO_FATAL",  "is_fatal": True,  "pass_value": "No"},
    {"no": 24, "name": "Next Best Action (NBA) executed correctly?",
     "tier": "QUALITY",   "weight_percent":  0.0, "response_type": "YES_NO",    "is_fatal": True,  "pass_value": "Yes"},
    {"no": 25, "name": "Call/Message triggered in DND hours?",
     "tier": "QUALITY",   "weight_percent":  0.0, "response_type": "YES_NO",    "is_fatal": True,  "pass_value": "No"},
]

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

# ── Action plan thresholds (pass threshold: 80%) ──────────────────
QA_SCORE_THRESHOLDS = {
    "critical": 55.0,
    "warning":  80.0,   # Convin Sense v0.3 pass threshold
    "good":     90.0,
}

CONVIN_SENSE_PASS_THRESHOLD = 80.0

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
