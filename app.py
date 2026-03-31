"""
FIRE Retirement Tracker -- Streamlit entry point.

Uses st.navigation() (Streamlit 1.36+) with st.Page() objects to
conditionally register pages based on authentication state.
"""

import logging

import streamlit as st

st.set_page_config(
    page_title="FIRE Retirement Tracker",
    page_icon="\U0001F525",  # fire emoji
    layout="wide",
)

# ---------------------------------------------------------------------------
# Responsive CSS for mobile devices
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Mobile-friendly metric cards */
@media (max-width: 768px) {
    /* Stack columns vertically on small screens */
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 0 100% !important;
        min-width: 100% !important;
    }

    /* Improve readability */
    .stMetric label { font-size: 0.8rem !important; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.3rem !important; }

    /* Make buttons touch-friendly */
    .stButton > button {
        min-height: 48px !important;
        font-size: 1rem !important;
    }

    /* Form inputs touch-friendly */
    .stTextInput input, .stNumberInput input, .stSelectbox select {
        min-height: 44px !important;
        font-size: 1rem !important;
    }

    /* Reduce padding */
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* Title sizing */
    h1 { font-size: 1.5rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1.1rem !important; }
}

/* Ensure dataframes scroll horizontally on small screens */
[data-testid="stDataFrame"] {
    overflow-x: auto !important;
}

/* Plotly charts responsive */
.js-plotly-plot {
    width: 100% !important;
}
</style>
""", unsafe_allow_html=True)
# SECURITY: Only hardcoded CSS above. No user-controlled data injected.

from auth import check_idle_timeout, check_session, is_authenticated, logout


# ---------------------------------------------------------------------------
# Restore session from browser localStorage (survives tab close/refresh)
# ---------------------------------------------------------------------------
if not is_authenticated():
    # Inject JS to read tokens from localStorage and pass via query params
    restore_js = """
    <script>
        const token = localStorage.getItem('fire_access_token');
        const refresh = localStorage.getItem('fire_refresh_token');
        const uid = localStorage.getItem('fire_user_id');
        const email = localStorage.getItem('fire_user_email');
        if (token && refresh && uid) {
            // Use a hidden iframe approach to pass data back to Streamlit
            const params = new URLSearchParams(window.location.search);
            if (!params.has('_restore')) {
                params.set('_restore', '1');
                params.set('_at', token);
                params.set('_rt', refresh);
                params.set('_uid', uid);
                params.set('_email', email || '');
                window.location.search = params.toString();
            }
        }
    </script>
    """
    # Check if we have restore params from the JS redirect
    params = st.query_params
    if params.get("_restore") == "1":
        access_token = params.get("_at", "")
        refresh_token = params.get("_rt", "")
        user_id = params.get("_uid", "")
        user_email = params.get("_email", "")

        if access_token and refresh_token and user_id:
            st.session_state["access_token"] = access_token
            st.session_state["refresh_token"] = refresh_token
            st.session_state["user_id"] = user_id
            st.session_state["user_email"] = user_email
            from datetime import datetime, timezone
            st.session_state["last_activity"] = datetime.now(timezone.utc)

            # Clear the restore params from URL
            st.query_params.clear()
            st.rerun()
    else:
        # Only inject the restore JS if we're not already restoring
        st.components.v1.html(restore_js, height=0)


# ---------------------------------------------------------------------------
# Login page (shown when not authenticated)
# ---------------------------------------------------------------------------

def login_page():
    """Render the login / signup form."""
    from gotrue.errors import AuthApiError

    st.title("\U0001F525 FIRE Retirement Tracker")
    st.subheader("Sign in to continue")

    tab_otp, tab_login, tab_signup = st.tabs(["Email OTP", "Password Login", "Sign Up"])

    # --- Tab 1: Email OTP (Magic Link) ---
    with tab_otp:
        if "otp_email_sent" not in st.session_state:
            st.session_state["otp_email_sent"] = False
            st.session_state["otp_email_address"] = ""

        if not st.session_state["otp_email_sent"]:
            # Step 1: Enter email and send OTP
            with st.form("otp_request_form"):
                otp_email = st.text_input("Email", key="otp_email")
                send_btn = st.form_submit_button("Send OTP to Email", use_container_width=True)

            if send_btn:
                if not otp_email:
                    st.error("Please enter your email.")
                else:
                    try:
                        from auth import send_otp
                        send_otp(otp_email)
                        st.session_state["otp_email_sent"] = True
                        st.session_state["otp_email_address"] = otp_email
                        st.success(f"OTP sent to {otp_email}. Check your inbox!")
                        st.rerun()
                    except Exception as exc:
                        logging.error(f"OTP send failed: {exc}")
                        st.error("Could not send OTP. Please try again.")
        else:
            # Step 2: Enter the OTP code
            st.info(f"OTP sent to **{st.session_state['otp_email_address']}**. Enter the code from your email below.")
            with st.form("otp_verify_form"):
                otp_code = st.text_input("Enter OTP Code", max_chars=8, key="otp_code")
                verify_btn = st.form_submit_button("Verify & Login", use_container_width=True)

            if verify_btn:
                if not otp_code or len(otp_code) < 6:
                    st.error("Please enter the 6-digit OTP code.")
                else:
                    try:
                        from auth import verify_otp
                        user_info = verify_otp(st.session_state["otp_email_address"], otp_code)
                        st.session_state["otp_email_sent"] = False
                        st.success(f"Welcome, {user_info['email']}!")
                        st.rerun()
                    except Exception as exc:
                        logging.error(f"OTP verify failed: {exc}")
                        st.error("Invalid OTP code. Please try again.")

            if st.button("Resend OTP", key="resend_otp"):
                try:
                    from auth import send_otp
                    send_otp(st.session_state["otp_email_address"])
                    st.success("OTP resent! Check your inbox.")
                except Exception as exc:
                    logging.error(f"OTP resend failed: {exc}")
                    st.error("Could not resend OTP.")

            if st.button("Use different email", key="change_otp_email"):
                st.session_state["otp_email_sent"] = False
                st.session_state["otp_email_address"] = ""
                st.rerun()

    # --- Tab 2: Password Login ---
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                if "login_failures" not in st.session_state:
                    st.session_state["login_failures"] = 0
                if st.session_state["login_failures"] >= 5:
                    st.error("Too many failed login attempts. Please wait and try again later.")
                else:
                    try:
                        from auth import login

                        user_info = login(email, password)
                        st.session_state["login_failures"] = 0
                        st.success(f"Welcome, {user_info['email']}!")
                        st.rerun()
                    except AuthApiError as exc:
                        st.session_state["login_failures"] += 1
                        logging.error(f"Login failed: {exc.message}")
                        st.error("Login failed. Please check your credentials and try again.")
                    except Exception as exc:
                        st.session_state["login_failures"] += 1
                        logging.error(f"Login failed: {exc}")
                        st.error("Login failed. Please check your credentials and try again.")

    with tab_signup:
        st.info(
            "Signup is for initial account creation only. "
            "After the first account is created, contact the admin for access."
        )
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            password_confirm = st.text_input(
                "Confirm password", type="password", key="signup_password_confirm"
            )
            submitted = st.form_submit_button("Create account", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            elif password != password_confirm:
                st.error("Passwords do not match.")
            elif len(password) < 12:
                st.error("Password must be at least 12 characters.")
            else:
                try:
                    from auth import signup

                    user_info = signup(email, password)
                    st.success(
                        f"Account created for {user_info['email']}. "
                        "You may now log in."
                    )
                except AuthApiError as exc:
                    logging.error(f"Signup failed: {exc.message}")
                    st.error("Signup failed. Please try again or contact the admin.")
                except Exception as exc:
                    logging.error(f"Signup failed: {exc}")
                    st.error("Signup failed. Please try again or contact the admin.")


# ---------------------------------------------------------------------------
# Idle timeout & session check
# ---------------------------------------------------------------------------

if is_authenticated():
    if not check_idle_timeout():
        st.warning("Your session has expired due to inactivity. Please log in again.")
        st.rerun()

    if not check_session():
        st.warning("Your session has expired. Please log in again.")
        st.rerun()


# ---------------------------------------------------------------------------
# Navigation setup
# ---------------------------------------------------------------------------

if not is_authenticated():
    # Unauthenticated: only show the login page.
    pg = st.navigation(
        [st.Page(login_page, title="Login", icon="\U0001F512")],
        position="hidden",
    )
else:
    # Authenticated: show full sidebar navigation.
    pg = st.navigation(
        [
            st.Page("pages/dashboard.py", title="Dashboard", icon="\U0001F4CA", default=True),
            st.Page("pages/income_expenses.py", title="Income & Expenses", icon="\U0001F4B0"),
            st.Page("pages/fire_settings.py", title="FIRE Settings", icon="\U0001F3AF"),
            st.Page("pages/fund_allocation.py", title="Fund Allocation", icon="\U0001F4C1"),
            st.Page("pages/growth_projection.py", title="Growth Projection", icon="\U0001F4C8"),
            st.Page("pages/retirement_analysis.py", title="Retirement Analysis", icon="\U0001F3D6\uFE0F"),
            st.Page("pages/sip_tracker.py", title="SIP Tracker", icon="\U0001F4DD"),
            st.Page("pages/settings_privacy.py", title="Settings & Privacy", icon="\U00002699\uFE0F"),
        ]
    )

    # Sidebar: user info and logout button.
    with st.sidebar:
        st.markdown(f"**{st.session_state.get('user_email', '')}**")
        if st.button("Logout", use_container_width=True):
            logout()
            st.rerun()

pg.run()
