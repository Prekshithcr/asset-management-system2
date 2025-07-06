import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh
import plotly.express as px
from streamlit_lottie import st_lottie
import requests

# --- Page Config ---
st.set_page_config(page_title="Asset Manager", layout="wide")

# --- Lottie Animation ---
def load_lottie_url(url):
    return requests.get(url).json()

lottie = load_lottie_url("https://assets4.lottiefiles.com/packages/lf20_mjlh3hcy.json")
st_lottie(lottie, height=200)

st.title("💻 Asset Management System")
st.caption("Manage your laptop inventory efficiently")

# --- Constants ---
DATA_PATH = "assets.csv"

# --- Auto-refresh every 10 seconds ---
st_autorefresh(interval=10 * 1000, key="refresh")

# --- Load Data ---
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

# --- TABS ---
tabs = st.tabs(["📊 Dashboard", "📋 Table", "➕ Add Asset", "❌ Delete", "📤 Export"])

# === TAB 1: DASHBOARD ===
with tabs[0]:
    if not df.empty:
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
            st.metric("Expiring in 30 Days", len(expiring))
        with col4:
            expired = df[
                pd.to_datetime(df["Warranty End - EOL"], errors='coerce') < today
            ]
            st.metric("Expired Warranty", len(expired))

        st.subheader("🏷️ Brand Distribution")
        brand_df = df["Brand"].value_counts().reset_index()
        brand_df.columns = ["Brand", "Count"]
        st.plotly_chart(px.pie(brand_df, values="Count", names="Brand", title="Laptop Brands Distribution"), use_container_width=True)

        st.subheader("📍 Location Distribution")
        loc_df = df["Location"].value_counts().reset_index()
        loc_df.columns = ["Location", "Assets"]
        st.plotly_chart(px.bar(loc_df, x="Location", y="Assets", title="Assets per Location"), use_container_width=True)

        st.subheader("📅 Warranty Expiry Trend")
        df["Warranty End - EOL"] = pd.to_datetime(df["Warranty End - EOL"], errors='coerce')
        df["Warranty Month"] = df["Warranty End - EOL"].dt.to_period("M")
        month_df = df["Warranty Month"].value_counts().sort_index().reset_index()
        month_df.columns = ["Month", "Expiring Assets"]
        st.plotly_chart(px.line(month_df, x="Month", y="Expiring Assets", title="Monthly Warranty Expiry"), use_container_width=True)

# === TAB 2: TABLE ===
with tabs[1]:
    if not df.empty:
        st.subheader("🔍 Filter/Search")
        col1, col2 = st.columns(2)
        with col1:
            filter_col = st.selectbox("Filter by column", options=[""] + list(df.columns))
        with col2:
            filter_val = ""
            if filter_col:
                filter_val = st.selectbox("Select value", options=[""] + df[filter_col].astype(str).unique().tolist())

        if filter_col and filter_val:
            df = df[df[filter_col].astype(str) == filter_val]
            st.info(f"Filtered by {filter_col} = {filter_val}")

        st.subheader("📋 Asset Table")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("📂 Please upload a CSV file or ensure 'assets.csv' exists.")

# === TAB 3: ADD ASSET ===
with tabs[2]:
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
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
                st.success("✅ New asset added!")
                if not st.session_state.uploaded:
                    st.session_state.df.to_csv(DATA_PATH, index=False)
                st.rerun()

# === TAB 4: DELETE ASSET ===
with tabs[3]:
    st.subheader("❌ Delete Asset")
    if not df.empty:
        del_index = st.number_input("Enter index to delete", min_value=0, max_value=len(df) - 1)
        if st.button("Delete Row"):
            st.session_state.df.drop(index=del_index, inplace=True)
            st.session_state.df.reset_index(drop=True, inplace=True)
            st.success(f"✅ Deleted row at index {del_index}")
            if not st.session_state.uploaded:
                st.session_state.df.to_csv(DATA_PATH, index=False)
            st.rerun()
    else:
        st.warning("⚠️ No data to delete.")

# === TAB 5: EXPORT ===
with tabs[4]:
    st.subheader("📤 Export / Save Changes")
    if not df.empty:
        csv = st.session_state.df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Updated CSV", data=csv, file_name="assets_updated.csv", mime="text/csv")

        if not st.session_state.uploaded:
            if st.button("💾 Save to assets.csv"):
                st.session_state.df.to_csv(DATA_PATH, index=False)
                st.success("✅ Changes saved to assets.csv")
        else:
            st.info("🔁 You are working with an uploaded file. Use download button to save your version.")
    else:
        st.warning("📂 No data to export.")
