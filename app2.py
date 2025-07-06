import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from streamlit_lottie import st_lottie
import requests

# --- Page Configuration ---
st.set_page_config(page_title="💻 Asset Management System", layout="wide")

# --- Lottie Animation ---
def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except:
        return None

lottie_url = "https://assets4.lottiefiles.com/packages/lf20_mjlh3hcy.json"
lottie_json = load_lottie_url(lottie_url)
with st.container():
    st_lottie(lottie_json, height=200, key="header_anim")

# --- App Title ---
st.title("💻 Asset Management System")
st.caption("📊 Manage your laptop inventory efficiently - Built with Streamlit")

# --- Constants ---
DATA_PATH = "assets.csv"

# --- Auto-refresh every 10 seconds ---
st_autorefresh(interval=10 * 1000, key="refresh")

# --- Load Data ---
uploaded_file = st.file_uploader("📥 Upload CSV (temporary, won't overwrite file)", type=["csv"])

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
    # --- Filter/Search ---
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

    # --- KPI Cards ---
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
        st.metric("Expiring Soon (30 days)", len(expiring))
    with col4:
        expired = df[
            pd.to_datetime(df["Warranty End - EOL"], errors='coerce') < today
        ]
        st.metric("Expired Warranty", len(expired))

    # --- Charts ---
    st.subheader("📈 Analytics Dashboard")

    # Ensure warranty date is datetime
    df["Warranty End - EOL"] = pd.to_datetime(df["Warranty End - EOL"], errors='coerce')

    # Pie Chart: Brand Distribution
    brand_df = df["Brand"].value_counts().reset_index()
    brand_df.columns = ["Brand", "Count"]
    pie_fig = px.pie(brand_df, values="Count", names="Brand", title="Laptop Brands Distribution",
                     color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(pie_fig, use_container_width=True)

    # Filter by brand
    selected_brand = st.selectbox("🔎 Filter by Brand", options=["All"] + brand_df["Brand"].tolist())
    if selected_brand != "All":
        df = df[df["Brand"] == selected_brand]
        st.info(f"📌 Showing assets for brand: **{selected_brand}**")

    # Location Bar Chart
    loc_df = df["Location"].value_counts().reset_index()
    loc_df.columns = ["Location", "Assets"]
    loc_fig = px.bar(loc_df, x="Location", y="Assets", color="Location", title="Assets per Location")
    st.plotly_chart(loc_fig, use_container_width=True)

    # Warranty Expiry by Month (Fixed)
    df["Warranty Month"] = df["Warranty End - EOL"].dt.to_period("M").astype(str)
    month_df = df["Warranty Month"].value_counts().sort_index().reset_index()
    month_df.columns = ["Month", "Expiring Assets"]
    expiry_fig = px.line(month_df, x="Month", y="Expiring Assets", title="Monthly Warranty Expiry")
    st.plotly_chart(expiry_fig, use_container_width=True)

    # --- Asset Table ---
    st.subheader("📋 Asset Table")
    st.dataframe(df, use_container_width=True)

    # --- Delete Row ---
    st.subheader("❌ Delete Row")
    if not df.empty:
        del_index = st.number_input("Enter index to delete", min_value=0, max_value=len(df) - 1)
        if st.button("Delete Row"):
            st.session_state.df.drop(index=del_index, inplace=True)
            st.session_state.df.reset_index(drop=True, inplace=True)
            st.success(f"✅ Deleted row at index {del_index}")

            if not st.session_state.uploaded:
                st.session_state.df.to_csv(DATA_PATH, index=False)
                st.info("💾 Changes saved to assets.csv")
            else:
                st.warning("⚠️ Uploaded file — use download to retain changes")

            st.rerun()

    # --- Add Asset ---
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
                    st.info("💾 Changes saved to assets.csv")
                else:
                    st.warning("⚠️ Uploaded file — download updated version below")

                st.rerun()

    # --- Export / Save ---
    st.subheader("📤 Export / Save Changes")
    csv = st.session_state.df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download CSV", data=csv, file_name="assets_updated.csv", mime="text/csv")

    if not st.session_state.uploaded:
        if st.button("💾 Save to assets.csv"):
            st.session_state.df.to_csv(DATA_PATH, index=False)
            st.success("✅ Saved to assets.csv")
    else:
        st.info("ℹ️ Working with an uploaded file — download to save")

else:
    st.warning("📂 Please upload a CSV or ensure 'assets.csv' exists in your project folder.")

