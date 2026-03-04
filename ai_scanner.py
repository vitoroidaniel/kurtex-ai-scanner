"""
ai_scanner.py — Groq API calls for issue detection and summarization.
"""

import logging
import os
from groq import AsyncGroq

logger = logging.getLogger(__name__)

# Groq client — reads GROQ_API_KEY from environment or config
_client = None

def _get_client():
    global _client
    if _client is None:
        from config_ai import config
        _client = AsyncGroq(api_key=config.GROQ_API_KEY)
    return _client


DETECT_PROMPT = """You are a truck fleet maintenance assistant.
Your job is to read a driver's message and decide if it describes a vehicle issue, breakdown, or maintenance problem.

Answer with EXACTLY this format:
ISSUE: YES or NO
CONFIDENCE: HIGH, MEDIUM, or LOW

Examples of issues: engine problems, flat tire, overheating, strange noise, smoke, warning lights, accident, fuel leak, brakes, steering problems.
Examples of non-issues: greetings, arrival confirmations, general chat, asking for directions, weather comments.

Message: {message}"""

SUMMARIZE_PROMPT = """Summarize this truck driver message in max 8 words. Be direct and specific. No filler words.

Examples:
Message: "the engine is making a loud knocking noise and smoke is coming out" -> "Engine knocking, smoke coming out"
Message: "i have a flat tire on the highway" -> "Flat tire on highway"
Message: "truck abs light is on and brakes feel weird" -> "ABS warning, brakes feeling off"

Message: {message}
Summary:"""


async def is_maintenance_issue(text: str) -> tuple[bool, str]:
    """
    Returns (is_issue: bool, confidence: str)
    """
    try:
        client   = _get_client()
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": DETECT_PROMPT.format(message=text)
            }],
            max_tokens=50,
            temperature=0.1,
        )

        reply = response.choices[0].message.content.strip().upper()
        logger.info(f"Groq detection response: {reply}")

        is_issue   = "ISSUE: YES" in reply
        confidence = "HIGH" if "HIGH" in reply else ("MEDIUM" if "MEDIUM" in reply else "LOW")

        # Only fire alerts for HIGH or MEDIUM confidence
        if confidence == "LOW":
            return False, confidence

        return is_issue, confidence

    except Exception as e:
        logger.error(f"Groq detection error: {e}")
        return False, "ERROR"


async def summarize_issue(text: str) -> str:
    """
    Returns a short summary of the issue.
    """
    try:
        client   = _get_client()
        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{
                "role": "user",
                "content": SUMMARIZE_PROMPT.format(message=text)
            }],
            max_tokens=60,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq summarize error: {e}")
        return text[:100]