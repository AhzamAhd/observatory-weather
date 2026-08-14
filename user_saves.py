import streamlit as st
import db
from datetime import datetime, timezone
import json

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

@st.cache_data(ttl=3600, show_spinner=False)
def get_observatory_id_by_name(name: str):
    """Resolve an observatory name to its database id (cached). Returns int or None."""
    row = db.fetch_one(
        "SELECT id FROM observatories WHERE name = %s",
        (name,)
    )
    return row["id"] if row else None

def render_save_button_by_name(user_id: int, observatory_name: str, key_suffix: str = ""):
    """
    Render a save/unsave toggle for an observatory identified by name.
    The dashboard's precomputed dataframe only carries the name, so we
    resolve the id here. No-op (with a hint) if the name can't be matched.
    """
    obs_id = get_observatory_id_by_name(observatory_name)
    if obs_id is None:
        st.caption("⭐ Save unavailable for this site")
        return

    saved = is_observatory_saved(user_id, obs_id)
    label = "★ Saved — click to remove" if saved else "⭐ Save Observatory"

    if st.button(label, key=f"save_toggle_{obs_id}_{key_suffix}", use_container_width=True):
        if saved:
            result = remove_saved_observatory(user_id, obs_id)
        else:
            result = save_observatory(user_id, obs_id, name=observatory_name)
        if result["success"]:
            st.toast(result["message"])
            st.rerun()
        else:
            st.error(result["message"])

def save_observatory(user_id: int, observatory_id: int, name: str = None, notes: str = None) -> dict:
    """Save a favorite observatory."""
    try:
        # Check if already saved
        existing = db.fetch_one(
            "SELECT id FROM saved_observatories WHERE user_id = %s AND observatory_id = %s",
            (user_id, observatory_id)
        )

        if existing:
            return {"success": False, "message": "Already saved"}

        db.execute(
            """INSERT INTO saved_observatories (user_id, observatory_id, name, notes, saved_at)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, observatory_id, name, notes, utcnow())
        )

        return {"success": True, "message": "Observatory saved!"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def remove_saved_observatory(user_id: int, observatory_id: int) -> dict:
    """Remove a saved observatory."""
    try:
        db.execute(
            "DELETE FROM saved_observatories WHERE user_id = %s AND observatory_id = %s",
            (user_id, observatory_id)
        )
        return {"success": True, "message": "Removed from saves"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def get_saved_observatories(user_id: int) -> list:
    """Get all saved observatories for a user."""
    try:
        rows = db.fetch_all(
            """SELECT so.id, so.observatory_id, so.name, so.notes, so.saved_at,
                      o.name as observatory_name, o.latitude, o.longitude,
                      o.altitude_m as elevation
               FROM saved_observatories so
               JOIN observatories o ON so.observatory_id = o.id
               WHERE so.user_id = %s
               ORDER BY so.saved_at DESC""",
            (user_id,)
        )
        return rows
    except Exception as e:
        st.error(f"Error loading saves: {str(e)}")
        return []

def is_observatory_saved(user_id: int, observatory_id: int) -> bool:
    """Check if an observatory is saved by the user."""
    result = db.fetch_one(
        "SELECT id FROM saved_observatories WHERE user_id = %s AND observatory_id = %s",
        (user_id, observatory_id)
    )
    return result is not None

def update_observatory_notes(user_id: int, saved_id: int, notes: str) -> dict:
    """Update the notes on a saved observatory (ownership-checked)."""
    try:
        row = db.fetch_one(
            "SELECT user_id FROM saved_observatories WHERE id = %s",
            (saved_id,)
        )
        if not row or row["user_id"] != user_id:
            return {"success": False, "message": "Unauthorized"}

        db.execute(
            "UPDATE saved_observatories SET notes = %s WHERE id = %s",
            (notes, saved_id)
        )
        return {"success": True, "message": "Notes updated"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

# ── Saved searches ────────────────────────────────────────────────

def save_search(user_id: int, name: str, query_text: str = None,
                min_score: int = None, condition: str = None,
                map_style: str = None) -> dict:
    """Save a named Live Map search/filter."""
    name = (name or "").strip()
    if not name:
        return {"success": False, "message": "Give the search a name"}
    try:
        db.execute(
            """INSERT INTO saved_searches
               (user_id, name, query_text, min_score, condition, map_style, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, name, query_text or None, min_score, condition,
             map_style, utcnow())
        )
        return {"success": True, "message": "Search saved!"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def get_saved_searches(user_id: int) -> list:
    """Get all saved searches for a user."""
    try:
        return db.fetch_all(
            """SELECT id, name, query_text, min_score, condition, map_style, created_at
               FROM saved_searches
               WHERE user_id = %s
               ORDER BY created_at DESC""",
            (user_id,)
        )
    except Exception as e:
        st.error(f"Error loading searches: {str(e)}")
        return []

def delete_saved_search(user_id: int, search_id: int) -> dict:
    """Delete a saved search (ownership-checked)."""
    try:
        row = db.fetch_one(
            "SELECT user_id FROM saved_searches WHERE id = %s",
            (search_id,)
        )
        if not row or row["user_id"] != user_id:
            return {"success": False, "message": "Unauthorized"}

        db.execute("DELETE FROM saved_searches WHERE id = %s", (search_id,))
        return {"success": True, "message": "Search deleted"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def save_observation_session(user_id: int, title: str, target: str,
                             observatory_id: int, notes: str,
                             data: dict = None) -> dict:
    """Save an observation session/log."""
    try:
        db.execute(
            """INSERT INTO observation_sessions (user_id, title, target, observatory_id, notes, data, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (user_id, title, target, observatory_id, notes, json.dumps(data) if data else None, utcnow())
        )
        return {"success": True, "message": "Session saved!"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def get_observation_sessions(user_id: int) -> list:
    """Get all observation sessions for a user."""
    try:
        rows = db.fetch_all(
            """SELECT os.id, os.title, os.target, os.observatory_id, os.notes, os.created_at,
                      o.name as observatory_name
               FROM observation_sessions os
               JOIN observatories o ON os.observatory_id = o.id
               WHERE os.user_id = %s
               ORDER BY os.created_at DESC""",
            (user_id,)
        )
        return rows
    except Exception as e:
        st.error(f"Error loading sessions: {str(e)}")
        return []

def delete_observation_session(user_id: int, session_id: int) -> dict:
    """Delete an observation session."""
    try:
        # Verify ownership
        session = db.fetch_one(
            "SELECT user_id FROM observation_sessions WHERE id = %s",
            (session_id,)
        )

        if not session or session["user_id"] != user_id:
            return {"success": False, "message": "Unauthorized"}

        db.execute(
            "DELETE FROM observation_sessions WHERE id = %s",
            (session_id,)
        )
        return {"success": True, "message": "Session deleted"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

def render_my_saves_page(user_id: int, observatory_names: list = None):
    """
    Render the My Saves page.

    observatory_names: optional list of all observatory names (from the
    dashboard df) used to populate the observation-log site picker.
    """
    st.markdown("# 📋 My Saves")

    tab_sites, tab_searches, tab_logs = st.tabs(
        ["⭐ Favorite Sites", "🔍 Saved Searches", "📝 Observation Logs"])

    # ── Favorite sites ────────────────────────────────────
    with tab_sites:
        st.markdown("### Your Favorite Observatories")

        saved_obs = get_saved_observatories(user_id)

        if not saved_obs:
            st.info("No saved observatories yet. Add one from the Live Weather "
                    "Map or an Observatory Detail page.")
        else:
            for obs in saved_obs:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{obs['observatory_name']}**")
                        st.caption(
                            f"📍 {obs['latitude']:.2f}°, {obs['longitude']:.2f}° "
                            f"· {obs['elevation']:.0f}m")
                    with col2:
                        if st.button("❌ Remove", key=f"remove_{obs['id']}",
                                     use_container_width=True):
                            remove_saved_observatory(user_id, obs['observatory_id'])
                            st.rerun()

                    with st.expander("📝 Notes"):
                        _notes = st.text_area(
                            "Your notes for this site",
                            value=obs['notes'] or "",
                            key=f"notes_{obs['id']}",
                            label_visibility="collapsed")
                        if st.button("Save notes", key=f"savenotes_{obs['id']}"):
                            r = update_observatory_notes(user_id, obs['id'], _notes)
                            if r["success"]:
                                st.toast(r["message"])
                                st.rerun()
                            else:
                                st.error(r["message"])

                    if st.button("🔬 View live detail",
                                 key=f"viewdetail_{obs['id']}"):
                        # Jump to the Observatory Detail page for this site.
                        st.session_state["nav_page"] = "Observatory Detail"
                        st.session_state["detail_obs"] = obs['observatory_name']
                        st.session_state["detail_sub"] = "Live detail"
                        st.rerun()

    # ── Saved searches ────────────────────────────────────
    with tab_searches:
        st.markdown("### Your Saved Searches")

        searches = get_saved_searches(user_id)

        if not searches:
            st.info("No saved searches yet. Build a filter on the Live Weather "
                    "Map and click **Save this search**.")
        else:
            for s in searches:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{s['name']}**")
                        _bits = []
                        if s['query_text']:
                            _bits.append(f"search: “{s['query_text']}”")
                        if s['map_style']:
                            _bits.append(f"{s['map_style']} map")
                        st.caption(" · ".join(_bits) if _bits else "All sites")
                    with col2:
                        if st.button("▶ Run", key=f"runsearch_{s['id']}",
                                     use_container_width=True):
                            # Push filter values into the Live Map widgets.
                            st.session_state["nav_page"] = "Live Weather Map"
                            st.session_state["map_obs_search"] = s['query_text'] or ""
                            if s['map_style']:
                                st.session_state["main_map_style"] = s['map_style']
                            st.rerun()
                    with col3:
                        if st.button("❌", key=f"delsearch_{s['id']}",
                                     use_container_width=True):
                            delete_saved_search(user_id, s['id'])
                            st.rerun()

    # ── Observation logs ──────────────────────────────────
    with tab_logs:
        st.markdown("### Your Observation Logs")

        with st.expander("➕ New observation log", expanded=False):
            _title = st.text_input("Title", key="newlog_title",
                                    placeholder="e.g. M31 imaging run")
            _target = st.text_input("Target", key="newlog_target",
                                    placeholder="e.g. Andromeda Galaxy")
            _names = observatory_names or []
            _site = st.selectbox("Observatory", _names,
                                 key="newlog_site") if _names else None
            _notes = st.text_area("Notes", key="newlog_notes",
                                  placeholder="Conditions, equipment, results…")
            if st.button("Save log", key="newlog_save"):
                if not _title:
                    st.error("Give the log a title")
                elif not _site:
                    st.error("Pick an observatory")
                else:
                    _oid = get_observatory_id_by_name(_site)
                    if _oid is None:
                        st.error("Could not match that observatory")
                    else:
                        r = save_observation_session(
                            user_id, _title, _target, _oid, _notes)
                        if r["success"]:
                            st.toast(r["message"])
                            st.rerun()
                        else:
                            st.error(r["message"])

        sessions = get_observation_sessions(user_id)

        if not sessions:
            st.info("No observation logs yet. Use the form above to add one.")
        else:
            for session in sessions:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{session['title']}**")
                        st.caption(
                            f"🎯 Target: {session['target'] or '—'} "
                            f"at {session['observatory_name']}")
                        st.caption(f"📅 {session['created_at']}")
                        if session['notes']:
                            st.markdown(f"*{session['notes']}*")
                    with col2:
                        if st.button("🗑️", key=f"delete_{session['id']}",
                                     help="Delete", use_container_width=True):
                            delete_observation_session(user_id, session['id'])
                            st.rerun()
