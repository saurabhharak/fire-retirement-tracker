"""Settings & Privacy page for the FIRE Retirement Tracker.

Provides data export (JSON download) and account deletion functionality.
"""

import json

import streamlit as st

from auth import get_current_user_id, logout
from db import delete_all_user_data, export_all_data, log_audit


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Settings & Privacy")

user_id = get_current_user_id()

# ---------------------------------------------------------------------------
# Export My Data
# ---------------------------------------------------------------------------

st.subheader("Export My Data")
st.markdown(
    "Download all your data (FIRE settings, income entries, expenses, "
    "SIP logs, and audit log) as a JSON file."
)

if st.button("Prepare Data Export", use_container_width=True):
    with st.spinner("Exporting your data..."):
        data = export_all_data(user_id)
    if data is not None:
        log_audit(user_id, "export_data")
        st.session_state["_export_data"] = data
        st.success("Export ready! Click the download button below.")
    else:
        st.error("Could not export data. Please try again.")

# Show download button if export data is ready
if "_export_data" in st.session_state and st.session_state["_export_data"] is not None:
    json_str = json.dumps(st.session_state["_export_data"], indent=2, default=str)
    st.download_button(
        label="Download JSON",
        data=json_str,
        file_name="fire_tracker_data_export.json",
        mime="application/json",
        use_container_width=True,
    )

# ---------------------------------------------------------------------------
# Delete My Account
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Delete My Account")
st.warning(
    "This action is **permanent and irreversible**. All your data across "
    "every table will be deleted, and your account will be removed."
)

confirmation = st.text_input(
    'Type **DELETE** to confirm account deletion:',
    key="delete_confirmation",
    placeholder="DELETE",
)

if st.button("Delete My Account", type="primary", use_container_width=True):
    if confirmation != "DELETE":
        st.error("Please type DELETE exactly to confirm account deletion.")
    else:
        with st.spinner("Deleting your data..."):
            log_audit(user_id, "delete_account")
            success = delete_all_user_data(user_id)
        if success:
            st.success("Your account and all data have been deleted.")
            st.warning(
                "Your data has been deleted. Note: Your login credentials "
                "still exist in the auth system. To fully remove your "
                "account, contact the admin or delete the user from the "
                "Supabase dashboard."
            )
            logout()
            st.rerun()
        else:
            st.error(
                "Could not delete your account. Please try again or "
                "contact the administrator."
            )
