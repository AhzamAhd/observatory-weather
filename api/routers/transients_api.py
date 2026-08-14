"""Transient-catalogue endpoints — wraps transients.py."""
from fastapi import APIRouter, HTTPException

import transients as T

router = APIRouter(prefix="/transients", tags=["transients"])


@router.get("/classes")
def classes():
    """Target classes grouped by science group, with which have live data."""
    groups = T.classes_by_group()
    return {
        "groups": {
            g: [{"name": c, "live": T.class_has_live_data(c)} for c in cls]
            for g, cls in groups.items()
        }
    }


@router.get("/targets")
def targets(target_class: str):
    """Targets for a class (curated catalogue + live alerts where available).
    Returns [] for a class with no live data."""
    if target_class not in T.TARGET_CLASSES:
        raise HTTPException(404, "Unknown target class")
    return {"target_class": target_class, "targets": T.get_targets(target_class)}
