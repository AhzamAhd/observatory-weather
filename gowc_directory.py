"""
GOWC object directory — the assistant's "concierge" lookup.

The assistant doesn't need its own object catalog: GOWC already knows the
objects. This module indexes the objects GOWC ALREADY has and, for any name a
user types, says which existing GOWC page handles it (and coordinates when
available). No LLM, no new catalog, no external API.

Sources indexed:
  - Object Visibility catalogue (object_visibility.OBJECTS): 300+ planets,
    galaxies, nebulae, clusters, named stars, exoplanets.
  - Transient catalogue (transients): X-ray binaries + live alerts.
"""
from __future__ import annotations

import re


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


_DIR_INDEX = None   # normalised token -> entry dict


def _entry(display, page, kind, ra=None, dec=None, ov_key=None):
    return {"display": display, "page": page, "kind": kind,
            "ra_deg": ra, "dec_deg": dec, "ov_key": ov_key}


def build_directory():
    """Index every object GOWC already knows. Cached. Tolerant of import
    failures (each source is optional)."""
    global _DIR_INDEX
    if _DIR_INDEX is not None:
        return _DIR_INDEX

    idx = {}

    def add(tokens, entry):
        for tok in tokens:
            t = _norm(tok)
            if t and t not in idx:
                idx[t] = entry

    # ── Object Visibility catalogue ──────────────────────────────────
    try:
        from object_visibility import OBJECTS
        for key, meta in OBJECTS.items():
            kind = meta.get("type", "object")
            e = _entry(key, "Object Visibility", kind, ov_key=key)
            # index the full name and each part around the em-dash / hyphen
            names = [key] + re.split(r"[—\-–]", key)
            add(names, e)
    except Exception:
        pass

    # ── Transient catalogue (X-ray binaries + alerts) ────────────────
    try:
        import transients as T
        for cls in ("Neutron-star X-ray binaries (LMXB/HMXB)",
                    "Black-hole X-ray binaries"):
            for t in T.get_targets(cls):
                if t.get("ra_deg") is None:
                    continue
                e = _entry(t["name"], "Transient Follow-Up", t.get("kind", "X-ray binary"),
                           ra=t["ra_deg"], dec=t["dec_deg"])
                names = [t["name"]]
                if t.get("alt_name"):
                    names.append(t["alt_name"])
                add(names, e)
    except Exception:
        pass

    _DIR_INDEX = idx
    return idx


def lookup(name, limit=6):
    """Find GOWC objects matching a typed name.

    Returns a list of entries (best first): exact/normalised match, then
    substring, then fuzzy. Each entry says which GOWC page handles it and
    carries coordinates when GOWC has them. Empty if nothing plausible.
    """
    if not name:
        return []
    idx = build_directory()
    qn = _norm(name)

    # exact normalised
    if qn in idx:
        return [idx[qn]]

    out = []
    seen = set()

    def push(entry):
        if entry["display"] not in seen:
            seen.add(entry["display"])
            out.append(entry)

    # substring matches (typed token contained in an indexed token)
    for tok, entry in idx.items():
        if qn and (qn in tok or tok in qn):
            push(entry)
            if len(out) >= limit:
                return out

    # fuzzy
    import difflib
    for tok in difflib.get_close_matches(qn, list(idx.keys()), n=limit, cutoff=0.7):
        push(idx[tok])
        if len(out) >= limit:
            break
    return out
