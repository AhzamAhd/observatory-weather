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
from observing_engine import (rank_sites, resolve_target, find_targets,
                              resolve_solar_system, KNOWN_TARGETS)


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
        "intent": {
            "type": "string",
            "enum": ["observing", "help", "other"],
            "description": "Classify the question. 'observing' = where/whether/"
                           "when to observe a specific target or target class. "
                           "'help' = a question about how the GOWC website "
                           "works, what a metric means, what a page does, or "
                           "how a score is calculated. 'other' = greeting or "
                           "unrelated.",
        },
    },
    "required": ["target_name", "ra_deg", "dec_deg", "date_iso", "intent"],
    "additionalProperties": False,
}

_EXTRACT_SYSTEM = (
    "You route an astronomer's question and, if it's about observing a target, "
    "extract parameters. You do NOT answer, compute, or invent coordinates.\n"
    "- Set intent: 'observing' (asking where/when/whether to observe a target "
    "or class), 'help' (how GOWC works, what a metric/page means, how a score "
    "is computed), or 'other' (greeting/unrelated).\n"
    "- For observing questions, put the target's name verbatim in target_name "
    "and leave coordinates null unless the user literally gave numeric RA/Dec. "
    "A separate engine resolves names.\n"
    "Resolve relative dates against the current date given in the message."
)


# ── Help lane: answer GOWC how-does-it-work questions, grounded in facts ──
_HELP_SYSTEM = (
    "You are GOWC's help assistant. Answer the user's question about the GOWC "
    "website using ONLY the facts provided below. Rules:\n"
    "- Do NOT invent features, pages, metrics, or numbers that are not in the "
    "facts. If the facts don't cover it, say you're not sure and suggest the "
    "Feedback & Suggestions page.\n"
    "- Be concise and friendly: a short, direct answer, not an essay.\n"
    "- If the user seems to want observing advice for a specific target, tell "
    "them to ask e.g. \"Where should I observe Sco X-1 tonight?\"\n\n"
    "GOWC FACTS:\n" + __import__("gowc_facts").GOWC_FACTS
)


def _answer_help(client, question):
    resp = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=_HELP_SYSTEM,
        messages=[{"role": "user", "content": question}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage


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

    intent = params.get("intent", "observing")

    # Help lane — GOWC how-does-it-work questions, grounded in gowc_facts.
    if intent == "help":
        try:
            answer, u2 = _answer_help(client, question)
            total_in += u2.input_tokens; total_out += u2.output_tokens
            total_cost += _usage_cost(u2)
        except anthropic.APIError as e:
            raise AssistantError(f"Sorry, I couldn't answer that right now ({type(e).__name__}).")
        _record_request(user_key, total_in, total_out, total_cost)
        return {"answer": answer, "engine_result": None, "params": params}

    # Greetings / unrelated.
    if intent == "other":
        _record_request(user_key, total_in, total_out, total_cost)
        return {
            "answer": ("I can help you observe targets (\"Where should I observe "
                       "Sco X-1 tonight?\") and answer questions about how GOWC "
                       "works (scores, metrics, pages). What would you like?"),
            "engine_result": None,
            "params": params,
        }

    # Resolve coordinates: explicit RA/Dec, else known-target name. NEVER guess.
    ra = params.get("ra_deg")
    dec = params.get("dec_deg")
    body_cls = None
    if ra is None or dec is None:
        name = params.get("target_name")
        # Moon / planets are moving bodies — the engine computes them live.
        body_cls = resolve_solar_system(name) if name else None
        coords = None if body_cls else (resolve_target(name) if name else None)
        if coords is None and body_cls is None:
            # The engine can directly rank X-ray-binary targets (it has their
            # coords). For anything else, act as a concierge: consult the GOWC
            # object directory and DIRECT the user to the GOWC page that already
            # handles that object. Never fabricate coordinates.
            candidates = find_targets(name) if name else []
            if candidates:
                _record_request(user_key, total_in, total_out, total_cost)
                lines = "\n".join(
                    f"- **{c['display']}**"
                    + (f" ({c['kind']})" if c.get("kind") else "")
                    for c in candidates)
                return {
                    "answer": (
                        f"\"{name}\" matches several targets I can rank — "
                        f"ask about one of these by name:\n\n{lines}\n\n"
                        "…or give me RA/Dec in decimal degrees."),
                    "engine_result": None,
                    "params": params,
                    "candidates": candidates,
                }

            # Concierge: is this object already in GOWC somewhere?
            from gowc_directory import lookup as _dir_lookup
            hits = _dir_lookup(name) if name else []
            _record_request(user_key, total_in, total_out, total_cost)
            if hits:
                best = hits[0]
                if best["page"] == "Object Visibility":
                    return {
                        "answer": (
                            f"**{best['display']}** is in GOWC. Head to the "
                            f"**Object Visibility** page and search for it there "
                            "— it shows whether the object is up tonight, its "
                            "airmass through the night, and the best "
                            "observatories to catch it."),
                        "engine_result": None,
                        "params": params,
                        "directory_hit": best,
                    }
                return {
                    "answer": (
                        f"**{best['display']}** is tracked on the **Transient "
                        f"Follow-Up** page (active X-ray-binary targets and "
                        "outburst alerts). You can also ask me to rank sites for "
                        "it directly by name."),
                    "engine_result": None,
                    "params": params,
                    "directory_hit": best,
                }

            return {
                "answer": (f"I couldn't find \"{name or 'that target'}\" in "
                           "GOWC. For deep-sky objects, planets and named stars, "
                           "try the **Object Visibility** page; for X-ray "
                           "binaries, **Transient Follow-Up**. Or give me RA/Dec "
                           "in decimal degrees and I'll rank sites for it."),
                "engine_result": None,
                "params": params,
            }
        if coords is not None:
            ra, dec = coords

    # Resolve date
    date_utc = now.replace(tzinfo=None)
    if params.get("date_iso"):
        try:
            date_utc = datetime.strptime(params["date_iso"], "%Y-%m-%d")
        except ValueError:
            pass

    # Step 2 — ENGINE computes the real answer (no LLM)
    engine_result = rank_sites(ra, dec, date_utc, weather_rows=weather_rows,
                               body_cls=body_cls)
    if body_cls is not None:
        engine_result["target"] = {"name": params.get("target_name")}

    # Step 3 — LLM formats the engine's numbers (relay only)
    try:
        answer, u2 = _format_answer(client, question, engine_result)
        total_in += u2.input_tokens; total_out += u2.output_tokens
        total_cost += _usage_cost(u2)
    except anthropic.APIError as e:
        raise AssistantError(f"Sorry, I couldn't phrase the answer ({type(e).__name__}).")

    _record_request(user_key, total_in, total_out, total_cost)
    return {"answer": answer, "engine_result": engine_result, "params": params}
