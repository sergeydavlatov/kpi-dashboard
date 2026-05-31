import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# CONFIG
# ==========================================

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1EWT1qzyyutsfclz9RK_lcjJRqi6W9dodTBpXEQUPN1E/edit?gid=1111412918#gid=1111412918"

TARGET_TAB = "Raw data Stats"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ==========================================
# GOOGLE AUTH
# ==========================================

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)
worksheet = spreadsheet.worksheet(TARGET_TAB)

# ==========================================
# UI
# ==========================================

st.title("Google Sheet Duplicate Cleaner")

if st.button("🧹 Clean Duplicates from Google Sheet"):

    with st.spinner("Reading all rows from Google Sheet..."):
        values = worksheet.get_all_values()

    if len(values) <= 1:
        st.warning("Sheet is empty or has only a header.")
        st.stop()

    header = values[0]
    rows = values[1:]

    st.write(f"📊 Total rows before cleaning: **{len(rows)}**")

    # Deduplicate keeping first occurrence, based on Date + Creator (cols 0 and 1)
    seen = set()
    unique_rows = []
    duplicate_count = 0

    for row in rows:
        # Use full row as key to only remove truly identical rows
        key = tuple(v.strip().lower() for v in row)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        unique_rows.append(row)

    st.write(f"🗑️ Duplicate rows found: **{duplicate_count}**")
    st.write(f"✅ Unique rows to keep: **{len(unique_rows)}**")

    if duplicate_count == 0:
        st.success("No duplicates found — sheet is already clean!")
        st.stop()

    # Clear sheet and rewrite with deduplicated data
    with st.spinner("Clearing sheet and rewriting clean data..."):
        worksheet.clear()

        # Rewrite header + unique rows in batches
        all_rows = [header] + unique_rows
        batch_size = 1000

        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i + batch_size]
            worksheet.append_rows(
                batch,
                value_input_option="USER_ENTERED",
            )
            st.write(f"  Written {min(i + batch_size, len(all_rows))}/{len(all_rows)} rows...")

    st.success(f"✅ Done! Removed **{duplicate_count}** duplicates. Sheet now has **{len(unique_rows)}** data rows.")
