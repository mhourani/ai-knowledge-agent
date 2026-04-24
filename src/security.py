"""
Security module for the AI Knowledge Agent.

Provides input sanitization (prompt injection detection) and output
validation (preventing system prompt leakage and sensitive data exposure).

Production AI systems need defense-in-depth against prompt injection:
  1. Input classification — detect and block malicious inputs before they
     reach the LLM
  2. Instruction-data separation — ensure user input is never treated as
     system instructions
  3. Output validation — verify the LLM response doesn't contain leaked
     system prompts or sensitive patterns

This module implements layers 1 and 3. Layer 2 is handled by the system
prompt design in agent.py.
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# PROMPT INJECTION DETECTION
# ============================================================================

# Patterns that indicate prompt injection attempts.
# Organized by category for clear reporting in evals.
INJECTION_PATTERNS = {
    "instruction_override": [
        r"ignore\s+(all\s+)?previous\s+(instructions|prompts|rules)",
        r"ignore\s+(the\s+)?(above|prior|preceding)",
        r"disregard\s+(all\s+)?previous",
        r"forget\s+(all\s+)?(your\s+)?(instructions|rules|guidelines|prompts)",
        r"override\s+(your\s+)?(instructions|rules|programming)",
        r"bypass\s+(your\s+)?(rules|restrictions|guidelines|safety)",
    ],
    "system_prompt_extraction": [
        r"(show|tell|reveal|display|print|output|repeat|share)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions|rules|programming|guidelines|directives)",
        r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions|rules)",
        r"(copy|paste|echo|dump)\s+(your\s+)?(system\s+)?(prompt|instructions)",
        r"(act|behave|respond)\s+as\s+if\s+you\s+(have\s+)?no\s+(rules|restrictions|guidelines)",
    ],
    "role_manipulation": [
        r"you\s+are\s+now\s+(a|an|the)",
        r"pretend\s+(you\s+are|to\s+be)\s+(a|an)",
        r"act\s+as\s+(a|an|if)",
        r"switch\s+(to|into)\s+.*(mode|persona|character)",
        r"(enter|enable|activate)\s+.*(mode|persona)",
        r"from\s+now\s+on\s+(you\s+are|you\'re|act)",
    ],
    "delimiter_injection": [
        r"<\/?system>",
        r"\[INST\]",
        r"\[\/INST\]",
        r"<<SYS>>",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"###\s*(system|instruction|human|assistant)",
        r"```\s*(system|instruction)",
    ],
    "encoding_evasion": [
        r"base64\s*(encode|decode|convert)",
        r"rot13",
        r"(hex|hexadecimal)\s*(encode|decode|convert)",
        r"(encode|decode)\s+this\s+(in|to|using)",
    ],
}

# Phrases that should NEVER appear in agent output
OUTPUT_FORBIDDEN_PATTERNS = [
    r"(my|the)\s+system\s+prompt\s+(is|says|reads|contains)",
    r"(my|the)\s+instructions\s+(are|say|read|tell\s+me\s+to)",
    r"I\s+(was|am)\s+(programmed|instructed|told)\s+to",
    r"(here\s+is|here\'s)\s+(my|the)\s+system\s+prompt",
    r"my\s+(rules|guidelines|programming)\s+(are|say|include)",
]

# Standard refusal message — clear, helpful, not defensive
REFUSAL_MESSAGE = (
    "I can't process that request. It appears to contain instructions "
    "that would alter my behavior or extract system information. "
    "I'm designed to answer questions about the documents in my "
    "knowledge base. Could you rephrase your question about the "
    "content you'd like to explore?"
)


def detect_injection(user_input: str) -> Tuple[bool, str]:
    """
    Analyze user input for prompt injection patterns.

    Returns:
        Tuple of (is_injection: bool, category: str)
        If no injection detected, returns (False, "")
        If injection detected, returns (True, category_name)
    """
    if not user_input or not user_input.strip():
        return False, ""

    # Normalize input for pattern matching
    normalized = user_input.lower().strip()

    for category, patterns in INJECTION_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                logger.warning(
                    f"Prompt injection detected: category={category}, "
                    f"input='{user_input[:100]}...'"
                )
                return True, category

    return False, ""


def sanitize_input(user_input: str) -> str:
    """
    Clean user input by removing potentially dangerous delimiters
    and control characters, without blocking the request entirely.

    This is a softer defense than detect_injection — it strips
    dangerous patterns rather than refusing the request. Used for
    inputs that don't trigger full injection detection but may
    contain embedded injection fragments (e.g., from ingested
    documents).
    """
    if not user_input:
        return ""

    # Remove common LLM control delimiters
    sanitized = user_input
    delimiter_patterns = [
        r"<\/?system>",
        r"\[INST\]",
        r"\[\/INST\]",
        r"<<SYS>>",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
    ]
    for pattern in delimiter_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

    # Remove null bytes and control characters (except newlines and tabs)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)

    return sanitized.strip()


def validate_output(agent_response: str) -> Tuple[bool, str]:
    """
    Validate agent output to ensure it doesn't contain leaked
    system prompts or sensitive information.

    Returns:
        Tuple of (is_safe: bool, violation: str)
        If output is safe, returns (True, "")
        If output contains forbidden content, returns (False, description)
    """
    if not agent_response:
        return True, ""

    normalized = agent_response.lower()

    for pattern in OUTPUT_FORBIDDEN_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            logger.warning(
                f"Output validation failed: pattern='{pattern}', "
                f"response='{agent_response[:100]}...'"
            )
            return False, f"Response may contain system prompt leakage"

    return True, ""


def get_safe_response(agent_response: str) -> str:
    """
    If output validation fails, return a safe fallback response
    instead of the potentially compromised one.
    """
    is_safe, violation = validate_output(agent_response)

    if is_safe:
        return agent_response

    logger.warning(f"Replacing unsafe output: {violation}")
    return (
        "I encountered an issue generating a response to that question. "
        "Could you try rephrasing? I'm here to help with questions about "
        "the documents in my knowledge base."
    )
