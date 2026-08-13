"""
Intelligent Observing Assistant — Part B (the thin chat layer).

STRICT ARCHITECTURE: the LLM does two narrow jobs and NOTHING else.
  1. Parse the user's natural-language question into structured parameters
     (target name or RA/Dec, date, constraints) via structured outputs.
  2. Phrase the ENGINE's already-computed answer into conversational text.

The LLM never computes astronomy and never invents numbers. Every real value
(observability, airmass, best time, site ranking, weather) comes from
observing_engine.rank_sites (Part A). If the engine can't answer, the assistant
says so — it must not fabricate.

Safeguards (required before public):
  - Per-user rate limit (DB-backed sliding window).
  - Hard global spending cap (cumulative token cost tracked in the DB; the
    assistant refuses once the cap is reached).

Model: claude-opus-5 via the anthropic SDK. Extraction uses output_config.format
(structured outputs) — no prefill, no temperature.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import anthropic

import db
from observing_engine import rank_sites, resolve_target, KNOWN_TARGETS


MODEL = "claude-opus-5"

# ── Safeguard configuration ─────────────────────────────────────────
RATE_LIMIT_PER_HOUR = 15          # requests per user per rolling hour
SPEND_CAP_USD = 5.00              # hard global ceiling on assistant LLM spend
# claude-opus-5 list price, $ per token (from the API reference: $5 / $25 per 1M)
PRICE_IN_PER_TOK = 5.0 / 1_000_000
PRICE_OUT_PER_TOK = 25.0 / 1_000_000


class AssistantError(Exception):
    """Raised for user-facing refusals (rate limit, spend cap, bad input)."""


# ── Safeguard checks (DB-backed, survive restarts) ──────────────────
def _requests_last_hour(user_key: str) -> int:
    try:
        row = db.fetch_one(
            "SELECT COUNT(*) AS c FROM assistant_requests "
            "WHERE user_key = %s AND created_at >= NOW() - INTERVAL '1 hour'",
            (user_key,),
        )
        return int(row["c"]) if row else 0
    except Exception:
        return 0  # fail open on the counter, not on the spend cap


def _total_spend_usd() -> float:
    try:
        row = db.fetch_one("SELECT COALESCE(SUM(cost_usd), 0) AS s FROM assistant_requests")
        return float(row["s"]) if row else 0.0
    except Exception:
        # Fail CLOSED on spend: if we can't read spend, don't risk overspending.
        raise AssistantError("Assistant temporarily unavailable (usage check failed).")


def _record_request(user_key, in_tok, out_tok, cost):
    try:
        db.execute(
            "INSERT INTO assistant_requests (user_key, input_tokens, output_tokens, cost_usd) "
            "VALUES (%s, %s, %s, %s)",
            (user_key, in_tok, out_tok, round(cost, 6)),
        )
    except Exception:
        pass  # never let accounting failure break a served answer


def check_safeguards(user_key: str):
    """Raise AssistantError if the user is rate-limited or the spend cap is hit.
    Call BEFORE making any LLM request."""
    if _total_spend_usd() >= SPEND_CAP_USD:
        raise AssistantError(
            "The observing assistant has reached its usage budget for now. "
            "Please try again later.")
    if _requests_last_hour(user_key) >= RATE_LIMIT_PER_HOUR:
        raise AssistantError(
            f"You've reached the limit of {RATE_LIMIT_PER_HOUR} questions per hour. "
            "Please try again later.")


# ── Step 1: LLM extracts structured parameters ONLY ─────────────────
_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "target_name": {
            "type": ["string", "null"],
            "description": "The astronomical target the user named, verbatim "
                           "(e.g. 'Vela X-1', 'M31'). Null if they gave "
                           "coordinates instead or named no target.",
        },
        "ra_deg": {
            "type": ["number", "null"],
            "description": "Right ascension in decimal degrees, ONLY if the "
                           "user explicitly gave coordinates. Never guess.",
        },
        "dec_deg": {
            "type": ["number", "null"],
            "description": "Declination in decimal degrees, ONLY if the user "
                           "explicitly gave coordinates. Never guess.",
        },
        "date_iso": {
            "type": ["string", "null"],
            "description": "The observing date as YYYY-MM-DD if the user "
                           "specified one (resolve 'tonight'/'today' to the "
                           "provided current date). Null if unspecified.",
        },
        "is_observing_question": {
            "type": "boolean",
            "description": "True if the user is asking where/whether/when to "
                           "observe a target. False for anything else "
                           "(greetings, unrelated questions).",
        },
    },
    "required": ["target_name", "ra_deg", "dec_deg", "date_iso",
                 "is_observing_question"],
    "additionalProperties": False,
}

_EXTRACT_SYSTEM = (
    "You extract structured parameters from an astronomer's question about "
    "where to observe a target. You do NOT answer the question, compute "
    "anything, or invent coordinates. Only fill ra_deg/dec_deg if the user "
    "literally provided numeric coordinates. Otherwise put the target's name "
    "in target_name and leave coordinates null — a separate engine resolves "
    "names to coordinates. Resolve relative dates against the current date "
    "given in the user message."
)


def _extract_params(client, question, current_date_iso):
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=1024,
        system=_EXTRACT_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": _EXTRACT_SCHEMA}},
        messages=[{
            "role": "user",
            "content": f"Current date (UTC): {current_date_iso}\n\nQuestion: {question}",
        }],
    )
    # parse() guarantees schema-valid JSON in the first text block
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text), resp.usage


# ── Step 2: LLM formats the ENGINE's numbers (never invents) ────────
_FORMAT_SYSTEM = (
    "You are GOWC's observing assistant. You are given a user's question and a "
    "JSON result computed by GOWC's deterministic observing engine. Write a "
    "brief, friendly answer that relays ONLY the numbers and facts in the "
    "engine result. Absolute rules:\n"
    "- NEVER state a number (altitude, airmass, time, score) that is not in the "
    "engine JSON. Do not estimate, round differently, or infer values.\n"
    "- If best_site is null (target not observable from any site tonight), say "
    "so plainly and, if present, mention why (it's a daytime object on this "
    "date, etc.). Do not invent an alternative.\n"
    "- Name the top 1-3 observable sites with their airmass, best UTC time, and "
    "weather score exactly as given. Note when a site's weather is a default "
    "(weather_known false) rather than live.\n"
    "- Keep it concise: a sentence or two plus a short ranked list. All times "
    "are UTC."
)


def _format_answer(client, question, engine_result):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_FORMAT_SYSTEM,
        messages=[{
            "role": "user",
            "content": (f"User question: {question}\n\n"
                        f"Engine result (the ONLY source of numbers):\n"
                        f"{json.dumps(engine_result, default=str)}"),
        }],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage


def _usage_cost(usage):
    return (usage.input_tokens * PRICE_IN_PER_TOK
            + usage.output_tokens * PRICE_OUT_PER_TOK)


# ── Public entry point ──────────────────────────────────────────────
def ask(question: str, user_key: str, weather_rows=None, api_key=None):
    """Answer one observing question.

    Returns {"answer": str, "engine_result": dict|None, "params": dict}.
    Raises AssistantError for refusals (rate limit, spend cap, unresolvable).
    """
    check_safeguards(user_key)

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("ANTHROPIC_API_KEY")
        except Exception:
            key = None
    if not key:
        raise AssistantError("The observing assistant isn't configured (no API key).")

    client = anthropic.Anthropic(api_key=key)
    now = datetime.now(timezone.utc)
    current_date_iso = now.strftime("%Y-%m-%d")

    total_in = total_out = 0
    total_cost = 0.0

    # Step 1 — extract parameters (LLM: parse only)
    try:
        params, u1 = _extract_params(client, question, current_date_iso)
        total_in += u1.input_tokens; total_out += u1.output_tokens
        total_cost += _usage_cost(u1)
    except anthropic.APIError as e:
        raise AssistantError(f"Sorry, I couldn't process that right now ({type(e).__name__}).")

    if not params.get("is_observing_question"):
        _record_request(user_key, total_in, total_out, total_cost)
        return {
            "answer": ("I'm the observing assistant — ask me where or when to "
                       "observe a target, e.g. \"Where should I observe Sco X-1 "
                       "tonight?\""),
            "engine_result": None,
            "params": params,
        }

    # Resolve coordinates: explicit RA/Dec, else known-target name. NEVER guess.
    ra = params.get("ra_deg")
    dec = params.get("dec_deg")
    if ra is None or dec is None:
        name = params.get("target_name")
        coords = resolve_target(name) if name else None
        if coords is None:
            _record_request(user_key, total_in, total_out, total_cost)
            known = ", ".join(sorted(t.title() for t in KNOWN_TARGETS))
            return {
                "answer": (f"I don't have coordinates for "
                           f"\"{name or 'that target'}\". I can look up: {known}. "
                           "Or give me RA/Dec in decimal degrees."),
                "engine_result": None,
                "params": params,
            }
        ra, dec = coords

    # Resolve date
    date_utc = now.replace(tzinfo=None)
    if params.get("date_iso"):
        try:
            date_utc = datetime.strptime(params["date_iso"], "%Y-%m-%d")
        except ValueError:
            pass

    # Step 2 — ENGINE computes the real answer (no LLM)
    engine_result = rank_sites(ra, dec, date_utc, weather_rows=weather_rows)

    # Step 3 — LLM formats the engine's numbers (relay only)
    try:
        answer, u2 = _format_answer(client, question, engine_result)
        total_in += u2.input_tokens; total_out += u2.output_tokens
        total_cost += _usage_cost(u2)
    except anthropic.APIError as e:
        raise AssistantError(f"Sorry, I couldn't phrase the answer ({type(e).__name__}).")

    _record_request(user_key, total_in, total_out, total_cost)
    return {"answer": answer, "engine_result": engine_result, "params": params}
