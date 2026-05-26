"""Guardrails engine: NeMo Guardrails with rule-based fallback."""

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

USE_NEMO = os.getenv("USE_NEMO_GUARDRAILS", "false").lower() in ("1", "true", "yes")

SPAM_PATTERNS = [
    r"win\s+money",
    r"click\s+here",
    r"free\s+money",
    r"!!!{2,}",
    r"lottery",
    r"crypto\s+giveaway",
]
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(your\s+)?(rules|instructions)",
    r"system\s+prompt",
    r"jailbreak",
    r"you\s+are\s+now\s+",
    r"override\s+(your\s+)?instructions",
]
OFFENSIVE_PATTERNS = [
    r"\b(hate|kill|attack)\s+(all|every)\b",
]
OFF_TOPIC_KEYWORDS = [
    "recipe",
    "football score",
    "python tutorial",
    "write me a poem",
    "sorting algorithm",
]
PROPERTY_KEYWORDS = [
    "apartment", "house", "villa", "property", "room", "bedroom", "kitchen",
    "price", "ils", "usd", "eur", "rent", "sale", "listing", "balcony",
    "parking", "office", "retail", "industrial", "warehouse", "land", "sqm",
    "renovated", "bathroom", "garden", "mortgage", "broker",
]
PRICE_PATTERN = re.compile(r"[\d,]+\s*(ils|usd|eur|₪|\$)", re.IGNORECASE)

OUTPUT_LEGAL_PATTERNS = [
    r"legally\s+guaranteed",
    r"guaranteed\s+to\s+(double|triple)",
    r"investment\s+return\s+guaranteed",
    r"will\s+definitely\s+increase\s+in\s+value",
    r"double\s+in\s+price\s+within",
]
OUTPUT_FABRICATION_PATTERNS = [
    r"leed\s+platinum\s+certified",
    r"energy\s+star\s+certified",
    r"iso\s+9001\s+certified",
]
DISCRIMINATORY_PATTERNS = [
    r"no\s+(children|families|pets)",
    r"christians\s+only",
    r"whites\s+only",
    r"perfect\s+for\s+[a-z]+\s+only",
    r"no\s+\w+\s+allowed",
]


class GuardrailsEngine:
    """Unified input/output validation."""

    def __init__(self) -> None:
        self._nemo = None
        if USE_NEMO:
            self._try_init_nemo()

    def _try_init_nemo(self) -> None:
        try:
            from nemoguardrails import RailsConfig

            config_dir = os.path.join(os.path.dirname(__file__), "config")
            if os.path.isdir(config_dir):
                self._nemo = RailsConfig.from_path(config_dir)
                logger.info("NeMo Guardrails config loaded")
        except ImportError:
            logger.info("NeMo Guardrails not installed; using rule-based fallback")
        except Exception as exc:
            logger.warning("NeMo init failed: %s", exc)

    def _match_any(self, text: str, patterns: list[str]) -> str | None:
        lower = text.lower()
        for pattern in patterns:
            if re.search(pattern, lower, re.IGNORECASE):
                return pattern
        return None

    def _is_likely_listing(self, text: str) -> bool:
        lower = text.lower()
        if PRICE_PATTERN.search(text):
            return True
        hits = sum(1 for kw in PROPERTY_KEYWORDS if kw in lower)
        return hits >= 2 or (len(text.strip()) >= 40 and hits >= 1)

    def check_input_rules(self, text: str) -> dict[str, Any]:
        stripped = text.strip()
        if len(stripped) < 15:
            return {
                "pass": False,
                "reason": "Rejected: text too short to be a property listing",
                "safe_text": "",
            }

        if self._match_any(text, SPAM_PATTERNS):
            return {
                "pass": False,
                "reason": "Rejected: spam or promotional content detected",
                "safe_text": "",
            }

        if self._match_any(text, INJECTION_PATTERNS):
            return {
                "pass": False,
                "reason": "Rejected: prompt injection attempt detected",
                "safe_text": "",
            }

        if self._match_any(text, OFFENSIVE_PATTERNS):
            return {
                "pass": False,
                "reason": "Rejected: offensive content detected",
                "safe_text": "",
            }

        lower = text.lower()
        if any(kw in lower for kw in OFF_TOPIC_KEYWORDS):
            return {
                "pass": False,
                "reason": "Rejected: off-topic content (not a property listing)",
                "safe_text": "",
            }

        if not self._is_likely_listing(text):
            return {
                "pass": False,
                "reason": "Rejected: text does not appear to be a genuine property listing",
                "safe_text": "",
            }

        safe = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
        safe = re.sub(
            r"ignore\s+previous\s+instructions",
            "[removed]",
            safe,
            flags=re.IGNORECASE,
        )
        return {"pass": True, "reason": "", "safe_text": safe.strip()}

    def check_output_rules(self, text: str) -> dict[str, Any]:
        if self._match_any(text, OUTPUT_LEGAL_PATTERNS):
            return {
                "pass": False,
                "reason": "Rejected: legal or investment return guarantees not permitted",
                "safe_text": text,
            }

        if self._match_any(text, DISCRIMINATORY_PATTERNS):
            return {
                "pass": False,
                "reason": "Rejected: discriminatory housing language detected",
                "safe_text": text,
            }

        if self._match_any(text, OUTPUT_FABRICATION_PATTERNS):
            return {
                "pass": False,
                "reason": "Rejected: unsupported or invented certifications detected",
                "safe_text": text,
            }

        if re.search(r"guaranteed\s+price", text, re.IGNORECASE):
            return {
                "pass": False,
                "reason": "Rejected: price guarantees are not permitted",
                "safe_text": text,
            }

        return {"pass": True, "reason": "", "safe_text": text.strip()}

    def check_input(self, text: str) -> dict[str, Any]:
        return self.check_input_rules(text)

    def check_output(self, text: str) -> dict[str, Any]:
        return self.check_output_rules(text)
