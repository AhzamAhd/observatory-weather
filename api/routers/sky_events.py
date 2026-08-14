"""Sky-events endpoints — meteor showers and eclipses.

Wraps meteor_showers.py and eclipses.py. Pure catalogue/ephemeris data, no LLM."""
from fastapi import APIRouter

import meteor_showers as ms
import eclipses as ec

router = APIRouter(prefix="/sky-events", tags=["sky-events"])


@router.get("/meteor-showers")
def meteor_showers():
    """Active and upcoming meteor showers."""
    try:
        active = ms.get_active_showers() or []
    except Exception:
        active = []
    try:
        upcoming = ms.get_upcoming_showers(60) or []
    except Exception:
        upcoming = []
    return {"active": active, "upcoming": upcoming}


@router.get("/eclipses")
def eclipses():
    """Upcoming eclipse events."""
    try:
        events = ec.get_upcoming_events() or []
    except Exception:
        events = []
    return {"count": len(events), "events": events}
