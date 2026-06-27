# Adding Save Buttons to GOWC Pages

Now that the auth system is in place, you can easily add "Save Observatory" buttons to any page. Here are some examples.

## Example 1: Save Button in Live Weather Map (after marker click)

In `dashboard.py`, in the "Live Weather Map" section, after displaying observatory details:

```python
if is_logged_in():
    obs_id = selected_obs['id']  # or however you're getting the ID
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⭐ Save Observatory", key=f"save_{obs_id}"):
            from user_saves import save_observatory
            result = save_observatory(
                st.session_state.user_id,
                obs_id,
                name=selected_obs['name'],
                notes=f"Saved on {datetime.now().strftime('%Y-%m-%d')}"
            )
            if result['success']:
                st.success(result['message'])
            else:
                st.error(result['message'])
    
    with col2:
        from user_saves import is_observatory_saved
        if is_observatory_saved(st.session_state.user_id, obs_id):
            st.caption("✓ Already saved")
else:
    st.info("Log in to save observatories")
```

## Example 2: Save Button in Observatory Detail Page

```python
if selected_page == "Observatory Detail":
    # ... existing code ...
    
    obs_id = selected_observatory['id']
    
    if is_logged_in():
        from user_saves import is_observatory_saved, save_observatory, remove_saved_observatory
        
        is_saved = is_observatory_saved(st.session_state.user_id, obs_id)
        
        if st.button(
            "⭐ Remove from Saves" if is_saved else "⭐ Save Observatory",
            key=f"toggle_save_{obs_id}"
        ):
            if is_saved:
                result = remove_saved_observatory(st.session_state.user_id, obs_id)
            else:
                result = save_observatory(
                    st.session_state.user_id,
                    obs_id,
                    name=selected_observatory['name'],
                    notes=st.text_input("Add notes (optional):", key="save_notes")
                )
            
            if result['success']:
                st.success(result['message'])
                st.rerun()
            else:
                st.error(result['message'])
```

## Example 3: Save to Favorites from Site Comparison

```python
if selected_page == "Site Comparison":
    # ... comparison code ...
    
    st.markdown("### Save Your Comparison Sites")
    
    if is_logged_in():
        cols = st.columns(len(comparison_sites))
        
        for i, site in enumerate(comparison_sites):
            with cols[i]:
                from user_saves import save_observatory, is_observatory_saved
                
                is_saved = is_observatory_saved(st.session_state.user_id, site['id'])
                
                if st.button(
                    "☑️" if is_saved else "☐",
                    key=f"comp_save_{site['id']}",
                    help="Add to favorites"
                ):
                    if is_saved:
                        from user_saves import remove_saved_observatory
                        remove_saved_observatory(st.session_state.user_id, site['id'])
                    else:
                        save_observatory(st.session_state.user_id, site['id'], name=site['name'])
                    st.rerun()
    else:
        st.info("Log in to save your favorite comparison sites")
```

## Example 4: Log Observation Session

After a user performs an observation or completes a calculation:

```python
if is_logged_in():
    st.markdown("### 📝 Log This Observation")
    
    with st.form("observation_log_form"):
        session_title = st.text_input(
            "Session title",
            value=f"Observation at {selected_observatory['name']}"
        )
        target = st.text_input("Target object/region", value=str(observed_object))
        notes = st.text_area("Observation notes", placeholder="What did you see? Any interesting details?")
        
        submitted = st.form_submit_button("Log Observation")
        
        if submitted:
            from user_saves import save_observation_session
            
            result = save_observation_session(
                st.session_state.user_id,
                title=session_title,
                target=target,
                observatory_id=selected_observatory['id'],
                notes=notes,
                data={
                    'timestamp': datetime.now().isoformat(),
                    'conditions': observation_score,
                    'seeing': seeing_value,
                    'airmass': airmass_value
                }
            )
            
            if result['success']:
                st.success("✓ Observation logged! View it in My Saves → Observation Logs")
            else:
                st.error(f"Failed to log: {result['message']}")
```

## Example 5: Quick Save Badge

Add a small indicator next to any observatory name showing if it's saved:

```python
from user_saves import is_observatory_saved

def obs_name_with_badge(user_id, obs_id, obs_name):
    """Display observatory name with saved badge if logged in."""
    if user_id and is_observatory_saved(user_id, obs_id):
        return f"{obs_name} ⭐"
    return obs_name

# Usage:
st.markdown(f"### {obs_name_with_badge(st.session_state.user_id, obs['id'], obs['name'])}")
```

## Pattern: Re-usable Save Widget

Create a helper function to standardize save buttons across pages:

```python
# Add this to user_saves.py
def render_save_button(user_id, observatory_id, observatory_name, key_suffix=""):
    """Render a standardized save/unsave button."""
    from user_saves import is_observatory_saved, save_observatory, remove_saved_observatory
    
    is_saved = is_observatory_saved(user_id, observatory_id)
    
    if st.button(
        f"{'❌ Unsave' if is_saved else '⭐ Save Observatory'}",
        key=f"save_btn_{observatory_id}_{key_suffix}",
        use_container_width=True
    ):
        if is_saved:
            result = remove_saved_observatory(user_id, observatory_id)
        else:
            result = save_observatory(user_id, observatory_id, observatory_name)
        
        if result['success']:
            st.success(result['message'])
            st.rerun()
        else:
            st.error(result['message'])

# Then use it anywhere:
if is_logged_in():
    render_save_button(
        st.session_state.user_id,
        selected_obs['id'],
        selected_obs['name'],
        key_suffix="live_map"
    )
```

## Getting Saved Observatories

Display a user's saved sites on any page:

```python
if is_logged_in():
    from user_saves import get_saved_observatories
    
    saved = get_saved_observatories(st.session_state.user_id)
    
    if saved:
        st.markdown("### Your Saved Observatories")
        
        for obs in saved:
            with st.container(border=True):
                st.markdown(f"**{obs['observatory_name']}**")
                st.caption(f"📍 {obs['latitude']:.2f}°, {obs['longitude']:.2f}°")
                
                if st.button("View Details", key=f"view_{obs['id']}"):
                    st.session_state.selected_page = "Observatory Detail"
                    st.session_state.selected_obs_id = obs['observatory_id']
                    st.rerun()
    else:
        st.info("No saved observatories yet. Click ⭐ to save your favorites!")
```

---

## Quick Checklist for Adding Saves to a Page

1. Import at top: `from auth import is_logged_in`
2. Import at feature: `from user_saves import save_observatory, is_observatory_saved`
3. Wrap save button in `if is_logged_in():` block
4. Call `save_observatory(st.session_state.user_id, obs_id, ...)`
5. Handle success/error with `st.success()` / `st.error()`
6. Use `st.rerun()` if you need to refresh the UI

That's it! The database handles the rest.
