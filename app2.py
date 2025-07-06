import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_lottie import st_lottie
from streamlit_autorefresh import st_autorefresh
import requests
import yaml
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader

# --- Load Lottie Animation ---
def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

lottie = load_lottie_url("https://assets4.lottiefiles.com/packages/lf20_mjlh3hcy.json")

# --- Load YAML Config ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- Authenticator ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)

login_info = authenticator.login('Login', location='main')

if login_info:
    name, auth_status, username = login_info
else:
    name, auth_status, username = None, None, None

user_role = config['credentials']['usernames'].get(username, {}).get('role', 'viewer')

# --- Authentication Status ---
if auth_status == False:
    st.error("❌ Incorrect username or password")
elif auth_status == None:
    st.warning("⚠️ Please enter your credentials")
elif auth_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"👋 Welcome, {name} ({user_role})")

    # --- App Interface ---
    st.set_page_config(page_title="Asset Manager", layout="wide")
    st_lottie(lottie, height=200)

    st.title("💻 Asset Management System")
    st.caption("Manage your laptop inventory efficiently")

    DATA_PATH = "assets.csv"
    st_autorefresh(interval=10 * 1000, key="refresh")

    uploaded_file = st.file_uploader("📥 Upload CSV to work temporarily (won't overwrite file)", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.session_state.uploaded = True
    else:
        if "df" not in st.session_state:
            if os.path.exists(DATA_PATH):
                df = pd.read_csv(DATA_PATH)
                st.session_state.df = df
                st.session_state.uploaded = False
            else:
                st.session_state.df = pd.DataFrame()
                st.session_state.uploaded = False

    df = st.session_state.df

    if not df.empty:
        # --- Filter ---
        st.subheader("🔍 Filter/Search")
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            filter_col = st.selectbox("Filter by column", options=[""] + list(df.columns))
        with col2:
            if filter_col:
                filter_val = st.selectbox("Select value", options=[""] + df[filter_col].astype(str).unique().tolist())
            else:
                filter_val = ""
        with col3:
            if st.button("Clear Filters"):
                filter_col, filter_val = "", ""

        if filter_col and filter_val:
            df = df[df[filter_col].astype(str) == filter_val]

        # --- KPIs ---
        st.subheader("📊 Asset Summary")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Assets", len(df))
        with col2:
            active = df[df["Status"].astype(str).str.lower() == "active"]
            st.metric("Active Assets", len(active))
        with col3:
            today = datetime.today()
            expiring = df[
                pd.to_datetime(df["Warranty End - EOL"], errors='coerce') <= (today + timedelta(days=30))
            ]
            st.metric("Expiring Soon", len(expiring))
        with col4:
            expired = df[
                pd.to_datetime(df["Warranty End - EOL"], errors='coerce') < today
            ]
            st.metric("Expired Warranty", len(expired))

        # --- Visualizations ---
        df["Warranty End - EOL"] = pd.to_datetime(df["Warranty End - EOL"], errors='coerce')

        st.subheader("📈 Charts")

        brand_counts = df["Brand"].value_counts().reset_index()
        brand_counts.columns = ["Brand", "Count"]

        pie_fig = px.pie(brand_counts, names="Brand", values="Count", title="Brand Distribution")
        st.plotly_chart(pie_fig, use_container_width=True)

        location_counts = df["Location"].value_counts().reset_index()
        location_counts.columns = ["Location", "Assets"]
        loc_fig = px.bar(location_counts, x="Location", y="Assets", title="Assets per Location")
        st.plotly_chart(loc_fig, use_container_width=True)

        df["Warranty Month"] = df["Warranty End - EOL"].dt.to_period("M")
        month_df = df["Warranty Month"].value_counts().sort_index().reset_index()
        month_df.columns = ["Month", "Expiring Assets"]
        line_fig = px.line(month_df, x="Month", y="Expiring Assets", title="Monthly Warranty Expiry")
        st.plotly_chart(line_fig, use_container_width=True)

        # --- Table ---
        st.subheader("📋 Asset Table")
        st.dataframe(df, use_container_width=True)

        # --- Delete Asset (Admin Only) ---
        if user_role == "admin":
            st.subheader("❌ Delete Row")
            del_index = st.number_input("Enter index to delete", min_value=0, max_value=len(df) - 1)
            if st.button("Delete Row"):
                st.session_state.df.drop(index=del_index, inplace=True)
                st.session_state.df.reset_index(drop=True, inplace=True)
                st.success(f"✅ Deleted row at index {del_index}")

                if not st.session_state.uploaded:
                    st.session_state.df.to_csv(DATA_PATH, index=False)
                    st.info("💾 Saved to assets.csv")
                else:
                    st.warning("Uploaded file mode — changes not saved permanently")

                st.rerun()
        else:
            st.info("🔒 You don't have permission to delete assets.")

        # --- Add Asset (Admin Only) ---
        if user_role == "admin":
            st.subheader("➕ Add New Asset")
            with st.form("add_form", clear_on_submit=True):
                cols = st.columns(4)
                model = cols[0].text_input("Model")
                brand = cols[1].text_input("Brand")
                serial = cols[2].text_input("Serial No")
                status = cols[3].selectbox("Status", ["Active", "In Repair", "Expired", "Spare"])

                assign_to = st.text_input("Assigned To")
                location = st.text_input("Location")
                warranty = st.date_input("Warranty End - EOL", value=datetime.today() + timedelta(days=365))

                submitted = st.form_submit_button("Add Asset")
                if submitted:
                    if not model or not brand or not serial:
                        st.error("❌ Model, Brand, and Serial No are required.")
                    else:
                        new_row = {
                            "Model": model,
                            "Brand": brand,
                            "Serial No": serial,
                            "Status": status,
                            "Assigned To": assign_to,
                            "Location": location,
                            "Warranty End - EOL": warranty
                        }
                        st.session_state.df = pd.concat(
                            [st.session_state.df, pd.DataFrame([new_row])],
                            ignore_index=True
                        )
                        st.success("✅ Asset added!")

                        if not st.session_state.uploaded:
                            st.session_state.df.to_csv(DATA_PATH, index=False)
                            st.info("💾 Saved to assets.csv")
                        else:
                            st.warning("Uploaded file mode — not saved permanently")

                        st.rerun()
        else:
            st.info("🔒 You don't have permission to add assets.")

        # --- Export ---
        st.subheader("📤 Export / Save Changes")
        csv = st.session_state.df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv, file_name="assets_updated.csv", mime="text/csv")

        if not st.session_state.uploaded:
            if st.button("💾 Save to assets.csv"):
                st.session_state.df.to_csv(DATA_PATH, index=False)
                st.success("✅ Changes saved!")
        else:
            st.info("ℹ️ Uploaded file mode — use Download CSV to retain changes.")

    else:
        st.warning("📂 No data found. Please upload or ensure assets.csv exists.")

