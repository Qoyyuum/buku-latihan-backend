"""
OpenRouter client for the grading pipeline.

Two calls per submission:
  1. `transcribe_page` — a vision model (default ``openrouter/free``) reads the
     composited page image and returns a structured transcript of the
     student's handwritten answers.
  2. `grade_answers` — the Jev decision model (``typesafe/jev-1.13``) scores
     each transcribed answer against the teacher's answer key, returning
     typed decisions with probabilities. Jev is text-only — it never sees
     images — which is why transcription happens first.

The key is server-side only; nothing here is called from the app.
"""

import base64
import json
import logging
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(120.0, connect=15.0)

_TRANSCRIBE_PROMPT = """You are a handwriting transcription engine.
Look at this worksheet page image. It shows a student's handwritten answers
on a printed worksheet.

Return ONLY JSON in this shape:
{"answers": [{"question": "<question label or number you see>",
              "answer_text": "<the student's handwritten answer, transcribed exactly>",
              "confidence": <0.0-1.0>}],
 "notes": "<anything ambiguous or illegible>"}

Transcribe exactly what is written — do not correct, solve, or judge it."""


def _headers() -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "X-Title": settings.OPENROUTER_APP_NAME,
        "Content-Type": "application/json",
    }
    if settings.OPENROUTER_HTTP_REFERER:
        headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
    return headers


def transcribe_page(
    image_png: bytes,
    regions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Vision model → JSON transcript of the handwritten answers on a page."""
    b64 = base64.b64encode(image_png).decode()

    user_content: list[dict[str, Any]] = [
        {"type": "text", "text": _TRANSCRIBE_PROMPT},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        },
    ]
    if regions:
        regions_json = json.dumps(regions)
        user_content[0]["text"] += (
            f'\n\nAnswer regions (use these labels for "question"): {regions_json}'
        )

    payload = {
        "model": settings.OPENROUTER_TRANSCRIBE_MODEL,
        "messages": [{"role": "user", "content": user_content}],
        "response_format": {"type": "json_object"},
    }
    resp = httpx.post(
        f"{settings.OPENROUTER_BASE_URL}/v1/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    try:
        result: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("transcriber returned non-JSON: %.200s", text)
        result = {"answers": [], "notes": text[:500]}
    return result


def grade_answers(
    worksheet_title: str,
    answer_key_notes: str,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Jev decision model → typed score (0-10) per transcribed answer.

    One Decisions-API request carries all questions about the same state.
    """
    state = {
        "worksheet": worksheet_title,
        "marking_scheme": (
            answer_key_notes or "Grade against the expected answer for each question."
        ),
        "student_answers": answers,
    }
    questions = [
        {
            "id": str(i),
            "type": "score",
            "question": (
                f"Score the student's answer to {a.get('question', i)} "
                "out of 10 against the marking scheme."
            ),
        }
        for i, a in enumerate(answers)
    ]

    payload = {
        "model": settings.OPENROUTER_GRADE_MODEL,
        "state": state,
        "questions": questions,
    }
    resp = httpx.post(
        f"{settings.OPENROUTER_BASE_URL}/alpha/decisions",
        headers=_headers(),
        json=payload,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    result: dict[str, Any] = resp.json()
    return result
