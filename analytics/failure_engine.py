"""
failure_engine.py — Bot Failure Intelligence Engine.
Analyses call transcripts to detect 8 categories of voice-bot failures
using rule-based NLP pattern matching, structural checks, and duration analysis.
"""
import re
import uuid
from difflib import SequenceMatcher
from typing import Any

from database.models import FAILURE_CONFIDENCE_THRESHOLD, FailureType


# ─────────────────────────── Keyword banks ───────────────────────

_LATENCY_BOT = [
    "please wait", "one moment", "just a moment", "hold on",
    "processing your request", "loading", "let me check",
    "bear with me", "checking that for you", "i'm looking that up",
]
_LATENCY_CUSTOMER = [
    "hello?", "are you there?", "anyone there", "hello hello",
    "is anyone listening", "this is taking long", "too slow",
]
_HALLUCINATION_CUSTOMER = [
    "that's wrong", "that's incorrect", "you're wrong", "not right",
    "wrong information", "you told me", "you said", "that's not accurate",
    "you gave me wrong", "that was incorrect", "misleading",
    "that's not true", "i can't trust", "false information",
]
_ENTITY_REPEAT_BOT = [
    "could you repeat", "say that again", "didn't catch", "didn't get",
    "could you spell", "pardon", "come again", "one more time",
    "could you say your name", "what was that", "sorry?",
]
_ENTITY_FRUSTRATION_CUSTOMER = [
    "already told you", "said it before", "told you already",
    "third time", "fourth time", "said my name", "keep repeating",
    "how many times",
]
_INTENT_CORRECTION_CUSTOMER = [
    "no i meant", "that's not what i", "i said i wanted",
    "not asking about", "you misunderstood", "that's not my question",
    "i asked for", "wrong topic", "different question",
    "no, i want", "i'm not interested in that",
]
_DROP_CUSTOMER = [
    "hello?", "are you there?", "hello hello", "can you hear me",
]
_LANGUAGE_CUSTOMER = [
    "habla español", "speak spanish", "hablo", "parlez", "comprendo",
    "sprechen", "italiano", "português", "français",
    "en español", "en français",
]
_CLOSURE_BOT = [
    "thank you", "goodbye", "have a great", "take care", "bye",
    "farewell", "next steps", "we'll follow up", "pleasure speaking",
    "good day", "have a wonderful",
]
_LOOP_SIMILARITY_THRESHOLD = 0.78
_LOOP_MIN_LENGTH = 25


# ─────────────────────────── Engine ──────────────────────────────

class FailureEngine:
    """
    Stateless engine — call `analyze(call_id, campaign_id, transcript, duration)`
    to get a list of failure dicts ready for db_manager.save_bot_failures().
    """

    def analyze(
        self,
        call_id: str,
        campaign_id: str,
        transcript: str,
        duration: int = 0,
    ) -> list[dict]:
        """
        Main entry point.
        Returns list[dict] with keys:
            failure_id, call_id, campaign_id, failure_type,
            failure_reason, confidence_score
        """
        failures: list[dict] = []

        # Duration-only check when no transcript
        if not transcript or not transcript.strip():
            if duration and duration < 30:
                failures.append(self._make(
                    call_id, campaign_id,
                    FailureType.CONVERSATION_DROP.value,
                    "Call duration under 30 seconds — likely dropped immediately.",
                    0.90,
                ))
            return failures

        turns = self._parse_turns(transcript)
        bot_turns   = [t for t in turns if t["speaker"] == "Bot"]
        cust_turns  = [t for t in turns if t["speaker"] == "Customer"]
        bot_text    = " ".join(t["text"].lower() for t in bot_turns)
        cust_text   = " ".join(t["text"].lower() for t in cust_turns)

        checks = [
            self._check_latency(call_id, campaign_id, bot_turns, cust_turns, duration),
            self._check_hallucination(call_id, campaign_id, cust_turns),
            self._check_entity_capture(call_id, campaign_id, bot_turns, cust_turns),
            self._check_intent_misclassification(call_id, campaign_id, cust_turns),
            self._check_conversation_drop(call_id, campaign_id, turns, duration),
            self._check_loop_response(call_id, campaign_id, bot_turns),
            self._check_language_detection(call_id, campaign_id, cust_turns, bot_turns),
            self._check_closure_failure(call_id, campaign_id, bot_turns),
        ]
        for result in checks:
            failures.extend(result)

        # Filter below threshold
        return [f for f in failures if f["confidence_score"] >= FAILURE_CONFIDENCE_THRESHOLD]

    # ── Private helpers ───────────────────────────────────────────

    @staticmethod
    def _make(call_id, campaign_id, ftype, reason, confidence) -> dict:
        return {
            "failure_id":       f"FAIL-{uuid.uuid4().hex[:8].upper()}",
            "call_id":          call_id,
            "campaign_id":      campaign_id,
            "failure_type":     ftype,
            "failure_reason":   reason,
            "confidence_score": round(min(confidence, 1.0), 3),
        }

    @staticmethod
    def _parse_turns(transcript: str) -> list[dict]:
        """Split transcript into speaker turns."""
        turns = []
        for line in transcript.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("bot:"):
                turns.append({"speaker": "Bot",      "text": line[4:].strip()})
            elif line.lower().startswith("customer:"):
                turns.append({"speaker": "Customer",  "text": line[9:].strip()})
            elif line.lower().startswith("user:"):
                turns.append({"speaker": "Customer",  "text": line[5:].strip()})
            elif line.lower().startswith("agent:"):
                turns.append({"speaker": "Bot",       "text": line[6:].strip()})
            elif ":" in line:
                sp, txt = line.split(":", 1)
                turns.append({"speaker": sp.strip(), "text": txt.strip()})
        return turns

    @staticmethod
    def _hit_rate(text: str, keywords: list[str]) -> float:
        """Proportion of keywords found in text."""
        if not text:
            return 0.0
        hits = sum(1 for kw in keywords if kw in text)
        return hits / len(keywords)

    @staticmethod
    def _any_keyword(text: str, keywords: list[str]) -> list[str]:
        return [kw for kw in keywords if kw in text.lower()]

    # ── 1. Latency Failure ────────────────────────────────────────

    def _check_latency(self, call_id, campaign_id, bot_turns, cust_turns, duration) -> list[dict]:
        failures = []
        bot_wait_turns = [t for t in bot_turns if self._any_keyword(t["text"], _LATENCY_BOT)]
        cust_wait = self._any_keyword(" ".join(t["text"] for t in cust_turns), _LATENCY_CUSTOMER)

        confidence = 0.0
        reason_parts = []
        if bot_wait_turns:
            ratio = len(bot_wait_turns) / max(len(bot_turns), 1)
            confidence += min(ratio * 1.5, 0.55)
            reason_parts.append(f"{len(bot_wait_turns)} bot turn(s) contain wait/delay messages")
        if cust_wait:
            confidence += 0.30
            reason_parts.append(f"customer expressed frustration with waiting: \"{cust_wait[0]}\"")
        if duration and duration < 90 and bot_wait_turns:
            confidence += 0.10
            reason_parts.append("short call with latency signals")

        if confidence >= FAILURE_CONFIDENCE_THRESHOLD:
            failures.append(self._make(
                call_id, campaign_id, FailureType.LATENCY.value,
                " | ".join(reason_parts),
                confidence,
            ))
        return failures

    # ── 2. Hallucination ─────────────────────────────────────────

    def _check_hallucination(self, call_id, campaign_id, cust_turns) -> list[dict]:
        cust_text = " ".join(t["text"].lower() for t in cust_turns)
        hits = self._any_keyword(cust_text, _HALLUCINATION_CUSTOMER)
        if not hits:
            return []
        confidence = min(0.40 + len(hits) * 0.20, 0.95)
        return [self._make(
            call_id, campaign_id, FailureType.HALLUCINATION.value,
            f"Customer correction signals detected: {hits[:3]}",
            confidence,
        )]

    # ── 3. Entity Capture Failure ─────────────────────────────────

    def _check_entity_capture(self, call_id, campaign_id, bot_turns, cust_turns) -> list[dict]:
        bot_text  = " ".join(t["text"].lower() for t in bot_turns)
        cust_text = " ".join(t["text"].lower() for t in cust_turns)

        repeat_hits = self._any_keyword(bot_text, _ENTITY_REPEAT_BOT)
        frustration = self._any_keyword(cust_text, _ENTITY_FRUSTRATION_CUSTOMER)

        # Count how many times bot asks to repeat
        repeat_count = len(repeat_hits)
        confidence = 0.0
        reasons = []

        if repeat_count >= 2:
            confidence += min(0.20 * repeat_count, 0.55)
            reasons.append(f"bot requested clarification {repeat_count}+ times")
        if frustration:
            confidence += 0.35
            reasons.append(f"customer frustration: \"{frustration[0]}\"")

        if confidence >= FAILURE_CONFIDENCE_THRESHOLD:
            return [self._make(
                call_id, campaign_id, FailureType.ENTITY_CAPTURE.value,
                " | ".join(reasons),
                confidence,
            )]
        return []

    # ── 4. Intent Misclassification ───────────────────────────────

    def _check_intent_misclassification(self, call_id, campaign_id, cust_turns) -> list[dict]:
        cust_text = " ".join(t["text"].lower() for t in cust_turns)
        hits = self._any_keyword(cust_text, _INTENT_CORRECTION_CUSTOMER)
        if not hits:
            return []
        confidence = min(0.45 + len(hits) * 0.20, 0.92)
        return [self._make(
            call_id, campaign_id, FailureType.INTENT_MISCLASSIFICATION.value,
            f"Customer had to correct bot intent: {hits[:3]}",
            confidence,
        )]

    # ── 5. Conversation Drop ─────────────────────────────────────

    def _check_conversation_drop(self, call_id, campaign_id, turns, duration) -> list[dict]:
        total_turns = len(turns)
        confidence = 0.0
        reasons = []

        if duration and duration < 25:
            confidence += 0.65
            reasons.append(f"very short call ({duration}s)")
        elif duration and duration < 60 and total_turns < 6:
            confidence += 0.40
            reasons.append(f"short call ({duration}s) with only {total_turns} turns")

        if total_turns < 4:
            confidence += 0.35
            reasons.append(f"only {total_turns} conversation turns recorded")

        # Check if transcript ends mid-sentence (no full stop or proper close)
        if turns:
            last = turns[-1]["text"].strip()
            if last and not last[-1] in ".!?":
                confidence += 0.20
                reasons.append("transcript appears to end abruptly")

        # Trailing bot monologue (last 3 turns all bot)
        if len(turns) >= 3:
            last3_speakers = [t["speaker"] for t in turns[-3:]]
            if all(s == "Bot" for s in last3_speakers):
                confidence += 0.20
                reasons.append("customer went silent — bot speaking to no one")

        # Customer asks "are you there?" signals drop
        cust_text = " ".join(t["text"].lower() for t in turns if t["speaker"] == "Customer")
        drop_hits = self._any_keyword(cust_text, _DROP_CUSTOMER)
        if drop_hits:
            confidence += 0.25
            reasons.append(f"customer checking if bot is connected: \"{drop_hits[0]}\"")

        if confidence >= FAILURE_CONFIDENCE_THRESHOLD:
            return [self._make(
                call_id, campaign_id, FailureType.CONVERSATION_DROP.value,
                " | ".join(reasons),
                confidence,
            )]
        return []

    # ── 6. Loop Response ─────────────────────────────────────────

    def _check_loop_response(self, call_id, campaign_id, bot_turns) -> list[dict]:
        if len(bot_turns) < 3:
            return []
        loop_pairs = []
        for i in range(len(bot_turns)):
            a = bot_turns[i]["text"]
            if len(a) < _LOOP_MIN_LENGTH:
                continue
            for j in range(i + 1, len(bot_turns)):
                b = bot_turns[j]["text"]
                sim = SequenceMatcher(None, a.lower(), b.lower()).ratio()
                if sim >= _LOOP_SIMILARITY_THRESHOLD:
                    loop_pairs.append((a[:60], sim))
                    break

        if not loop_pairs:
            return []

        confidence = min(0.55 + len(loop_pairs) * 0.20, 0.97)
        example = loop_pairs[0][0]
        return [self._make(
            call_id, campaign_id, FailureType.LOOP_RESPONSE.value,
            f"Bot repeated similar response {len(loop_pairs)} time(s). Example: \"{example}...\"",
            confidence,
        )]

    # ── 7. Language Detection Failure ────────────────────────────

    def _check_language_detection(self, call_id, campaign_id, cust_turns, bot_turns) -> list[dict]:
        cust_text = " ".join(t["text"].lower() for t in cust_turns)
        lang_hits = self._any_keyword(cust_text, _LANGUAGE_CUSTOMER)
        if not lang_hits:
            return []

        # Bot should acknowledge language switch
        bot_text = " ".join(t["text"].lower() for t in bot_turns)
        bot_acknowledged = any(
            kw in bot_text for kw in ["español", "french", "spanish", "language", "translate"]
        )
        confidence = 0.65 if not bot_acknowledged else 0.35
        reason = (
            f"Customer switched language ({lang_hits[0]}) "
            + ("— bot did not acknowledge." if not bot_acknowledged
               else "— bot attempted to acknowledge but may have failed.")
        )
        return [self._make(
            call_id, campaign_id, FailureType.LANGUAGE_DETECTION.value,
            reason,
            confidence,
        )]

    # ── 8. Closure Failure ────────────────────────────────────────

    def _check_closure_failure(self, call_id, campaign_id, bot_turns) -> list[dict]:
        if not bot_turns:
            return [self._make(
                call_id, campaign_id, FailureType.CLOSURE_FAILURE.value,
                "No bot turns found — cannot verify closure.",
                0.45,
            )]

        # Check last two bot turns for closing phrases
        last_two = " ".join(t["text"].lower() for t in bot_turns[-2:])
        all_bot  = " ".join(t["text"].lower() for t in bot_turns)
        has_close_last = any(kw in last_two for kw in _CLOSURE_BOT)
        has_close_any  = any(kw in all_bot  for kw in _CLOSURE_BOT)

        if has_close_last:
            return []    # Proper closure
        if has_close_any:
            confidence = 0.38
            reason = "Closing phrase found mid-conversation but not at end — closure may be premature."
        else:
            confidence = 0.72
            reason = "No closing/farewell phrase detected anywhere in bot responses."

        return [self._make(
            call_id, campaign_id, FailureType.CLOSURE_FAILURE.value,
            reason,
            confidence,
        )]


# ── Module-level convenience function ────────────────────────────

_engine = FailureEngine()

def analyze_call_failures(call_id: str, campaign_id: str, transcript: str, duration: int = 0) -> list[dict]:
    """Public API — wraps FailureEngine.analyze()."""
    return _engine.analyze(call_id, campaign_id, transcript, duration)
