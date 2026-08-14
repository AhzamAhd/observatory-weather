"""
NASA ADS literature search.

Queries the NASA ADS API (adsabs.harvard.edu) and returns REAL papers, exactly
as ADS reports them. No LLM is involved anywhere in this module: every paper,
author, year, journal, and link comes verbatim from the ADS API response.
LLMs hallucinate citations, so the paper path must never touch one.

The ADS API token is read from the ADS_API_TOKEN environment variable, falling
back to Streamlit secrets. It is NEVER hardcoded or committed.
"""
from __future__ import annotations

import os
import urllib.parse

import requests

_ADS_URL = "https://api.adsabs.harvard.edu/v1/search/query"
_TIMEOUT = 20

# Fields we ask ADS to return. Everything shown to the user is built from these.
_FIELDS = "bibcode,title,author,year,pub,doi,citation_count,identifier"

SORT_OPTIONS = {
    "Relevance": "score desc",
    "Most cited": "citation_count desc",
    "Newest first": "date desc",
}


class ADSError(Exception):
    """User-facing ADS problem (missing token, API error, etc.)."""


def _get_token():
    token = os.environ.get("ADS_API_TOKEN")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("ADS_API_TOKEN")
        except Exception:
            token = None
    return token


def _best_link(doc):
    """Pick the most useful clickable link for a paper, in priority order:
    DOI -> arXiv -> the ADS abstract page. Always returns a real URL."""
    doi = doc.get("doi")
    if doi:
        d = doi[0] if isinstance(doi, list) else doi
        return f"https://doi.org/{d}", "DOI"

    # arXiv id lives in the identifier list, e.g. "arXiv:2401.01234"
    for ident in doc.get("identifier", []) or []:
        low = ident.lower()
        if low.startswith("arxiv:"):
            return f"https://arxiv.org/abs/{ident.split(':', 1)[1]}", "arXiv"
        if low.startswith("10.") and "/" in ident:  # a DOI in the identifier list
            return f"https://doi.org/{ident}", "DOI"

    # Fallback: the ADS abstract page (always exists, keyed by bibcode).
    bib = doc.get("bibcode")
    if bib:
        return (f"https://ui.adsabs.harvard.edu/abs/"
                f"{urllib.parse.quote(bib)}/abstract", "ADS")
    return None, None


def _format_authors(authors):
    """'Last, First' list -> 'Smith et al.' / 'Smith & Jones' / 'Smith'."""
    if not authors:
        return "Unknown author"
    first = authors[0].split(",")[0].strip()
    if len(authors) == 1:
        return first
    if len(authors) == 2:
        second = authors[1].split(",")[0].strip()
        return f"{first} & {second}"
    return f"{first} et al."


def search_papers(topic, rows=15, sort="Relevance",
                  year_min=None, year_max=None):
    """Search ADS for a topic and return a list of real papers.

    Returns a list of dicts:
      {title, authors, year, pub, citations, link, link_type, bibcode}
    Every field comes straight from the ADS response — nothing is invented.

    Raises ADSError for a missing token or an API failure; returns [] for a
    valid search with no matches.
    """
    topic = (topic or "").strip()
    if not topic:
        return []

    token = _get_token()
    if not token:
        raise ADSError("Literature search isn't configured (no ADS API token).")

    q = topic
    # Optional year filter via the ADS `year` field range syntax.
    if year_min or year_max:
        lo = year_min or "*"
        hi = year_max or "*"
        q = f"{topic} year:[{lo} TO {hi}]"

    params = {
        "q": q,
        "fl": _FIELDS,
        "rows": max(1, min(int(rows), 20)),   # hard cap at 20
        "sort": SORT_OPTIONS.get(sort, "score desc"),
    }

    try:
        resp = requests.get(
            _ADS_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ADSError(f"Couldn't reach NASA ADS ({type(e).__name__}). "
                       "Please try again.")

    if resp.status_code == 401:
        raise ADSError("NASA ADS rejected the API token. Check it's valid.")
    if resp.status_code == 429:
        raise ADSError("NASA ADS rate limit reached. Please wait and retry.")
    if resp.status_code >= 400:
        raise ADSError(f"NASA ADS returned an error (HTTP {resp.status_code}).")

    try:
        docs = resp.json().get("response", {}).get("docs", [])
    except ValueError:
        raise ADSError("NASA ADS returned an unexpected response.")

    papers = []
    for d in docs:
        link, link_type = _best_link(d)
        title = d.get("title")
        title = title[0] if isinstance(title, list) and title else (title or "Untitled")
        papers.append({
            "title": title,
            "authors": _format_authors(d.get("author")),
            "year": d.get("year"),
            "pub": d.get("pub"),
            "citations": d.get("citation_count", 0),
            "link": link,
            "link_type": link_type,
            "bibcode": d.get("bibcode"),
        })
    return papers
