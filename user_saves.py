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

def render_my_saves_page(user_id: int):
    """Render the My Saves page."""
    st.markdown("# 📋 My Saved Observatories & Sessions")

    tab1, tab2 = st.tabs(["Favorite Sites", "Observation Logs"])

    with tab1:
        st.markdown("### Your Favorite Observatories")

        saved_obs = get_saved_observatories(user_id)

        if not saved_obs:
            st.info("No saved observatories yet. Add one from the Live Weather Map!")
        else:
            for obs in saved_obs:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"**{obs['observatory_name']}**")
                        st.caption(f"📍 {obs['latitude']:.2f}°, {obs['longitude']:.2f}° · {obs['elevation']:.0f}m")
                        if obs['notes']:
                            st.markdown(f"*{obs['notes']}*")

                    with col2:
                        pass

                    with col3:
                        if st.button("❌", key=f"remove_{obs['id']}", help="Remove"):
                            remove_saved_observatory(user_id, obs['observatory_id'])
                            st.rerun()

    with tab2:
        st.markdown("### Your Observation Logs")

        sessions = get_observation_sessions(user_id)

        if not sessions:
            st.info("No observation logs yet. Create one to track your sessions!")
        else:
            for session in sessions:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        st.markdown(f"**{session['title']}**")
                        st.caption(f"🎯 Target: {session['target']} at {session['observatory_name']}")
                        st.caption(f"📅 {session['created_at']}")
                        if session['notes']:
                            st.markdown(f"*{session['notes']}*")

                    with col2:
                        if st.button("🗑️", key=f"delete_{session['id']}", help="Delete"):
                            delete_observation_session(user_id, session['id'])
                            st.rerun()
