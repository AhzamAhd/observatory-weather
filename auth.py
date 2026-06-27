import streamlit as st
import bcrypt
import db
from datetime import datetime, timezone

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def user_exists(username: str) -> bool:
    """Check if a username already exists."""
    result = db.fetch_one(
        "SELECT id FROM users WHERE username = %s",
        (username,)
    )
    return result is not None

def register_user(username: str, password: str, email: str = None) -> dict:
    """
    Register a new user.
    Returns: {"success": bool, "message": str, "user_id": int or None}
    """
    username = username.strip().lower()

    if len(username) < 3:
        return {"success": False, "message": "Username must be at least 3 characters"}

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters"}

    if user_exists(username):
        return {"success": False, "message": "Username already taken"}

    hashed_password = hash_password(password)

    try:
        db.execute(
            """INSERT INTO users (username, password_hash, email, created_at)
               VALUES (%s, %s, %s, %s)""",
            (username, hashed_password, email, utcnow())
        )

        # Get the new user's ID
        user = db.fetch_one(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )

        return {
            "success": True,
            "message": "Account created successfully!",
            "user_id": user["id"] if user else None
        }
    except Exception as e:
        return {"success": False, "message": f"Registration failed: {str(e)}"}

def login_user(username: str, password: str) -> dict:
    """
    Login a user.
    Returns: {"success": bool, "message": str, "user_id": int or None, "username": str or None}
    """
    username = username.strip().lower()

    user = db.fetch_one(
        "SELECT id, username, password_hash FROM users WHERE username = %s",
        (username,)
    )

    if not user:
        return {"success": False, "message": "Invalid username or password"}

    if not verify_password(password, user["password_hash"]):
        return {"success": False, "message": "Invalid username or password"}

    return {
        "success": True,
        "message": "Logged in successfully!",
        "user_id": user["id"],
        "username": user["username"]
    }

def is_logged_in() -> bool:
    """Check if user is currently logged in."""
    return "user_id" in st.session_state and st.session_state.user_id is not None

def get_current_user() -> dict:
    """Get current logged-in user info."""
    if not is_logged_in():
        return None

    user = db.fetch_one(
        "SELECT id, username, email FROM users WHERE id = %s",
        (st.session_state.user_id,)
    )
    return user

def logout_user():
    """Logout the current user."""
    st.session_state.user_id = None
    st.session_state.username = None

def render_auth_sidebar():
    """Render login/register/logout in sidebar. Returns True if user is logged in."""
    if is_logged_in():
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Logged in as:** `{st.session_state.username}`")

        if st.sidebar.button("📋 My Saves", use_container_width=True):
            st.session_state.show_my_saves = True

        if st.sidebar.button("⚙️ Account Settings", use_container_width=True):
            st.session_state.show_account_settings = True

        if st.sidebar.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()

        return True
    else:
        st.sidebar.markdown("---")

        auth_tab1, auth_tab2 = st.sidebar.tabs(["Login", "Register"])

        with auth_tab1:
            st.markdown("**Login to GOWC**")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login", use_container_width=True, key="login_btn"):
                result = login_user(username, password)
                if result["success"]:
                    st.session_state.user_id = result["user_id"]
                    st.session_state.username = result["username"]
                    st.success(result["message"])
                    st.rerun()
                else:
                    st.error(result["message"])

        with auth_tab2:
            st.markdown("**Create Account**")
            new_username = st.text_input("Username", key="reg_username")
            new_email = st.text_input("Email (optional)", key="reg_email")
            new_password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")

            if st.button("Register", use_container_width=True, key="reg_btn"):
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                else:
                    result = register_user(new_username, new_password, new_email if new_email else None)
                    if result["success"]:
                        st.success(result["message"])
                        st.info("Now login with your new account!")
                    else:
                        st.error(result["message"])

        return False


def render_auth_main():
    """
    Render an always-visible auth control in the MAIN page area (not the
    sidebar, which collapses on mobile). Uses a right-aligned popover button.
    Returns True if user is logged in.
    """
    # Right-align the auth control so it sits unobtrusively at the top.
    _spacer, _auth_col = st.columns([4, 1])

    with _auth_col:
        if is_logged_in():
            with st.popover(f"👤 {st.session_state.username}", use_container_width=True):
                st.markdown(f"**Logged in as** `{st.session_state.username}`")

                if st.button("📋 My Saves", use_container_width=True, key="main_my_saves"):
                    st.session_state.show_my_saves = True
                    st.rerun()

                if st.button("🚪 Logout", use_container_width=True, key="main_logout"):
                    logout_user()
                    st.rerun()
            return True
        else:
            with st.popover("🔐 Login / Register", use_container_width=True):
                tab_login, tab_register = st.tabs(["Login", "Register"])

                with tab_login:
                    username = st.text_input("Username", key="main_login_username")
                    password = st.text_input("Password", type="password", key="main_login_password")

                    if st.button("Login", use_container_width=True, key="main_login_btn"):
                        result = login_user(username, password)
                        if result["success"]:
                            st.session_state.user_id = result["user_id"]
                            st.session_state.username = result["username"]
                            st.rerun()
                        else:
                            st.error(result["message"])

                with tab_register:
                    new_username = st.text_input("Username", key="main_reg_username")
                    new_email = st.text_input("Email (optional)", key="main_reg_email")
                    new_password = st.text_input("Password", type="password", key="main_reg_password")
                    confirm_password = st.text_input("Confirm Password", type="password", key="main_reg_confirm")

                    if st.button("Create Account", use_container_width=True, key="main_reg_btn"):
                        if new_password != confirm_password:
                            st.error("Passwords don't match")
                        else:
                            result = register_user(new_username, new_password, new_email if new_email else None)
                            if result["success"]:
                                st.success(result["message"])
                                st.info("Now log in with your new account.")
                            else:
                                st.error(result["message"])
            return False
