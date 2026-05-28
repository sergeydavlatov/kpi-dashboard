import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1EWT1qzyyutsfclz9RK_lcjJRqi6W9dodTBpXEQUPN1E/edit?gid=0#gid=0"

RAW_TAB = "Raw data"
STATS_TAB = "Raw data Stats"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =========================
# HEADER MAPPING
# left = Google Sheet header
# right = Excel header
# =========================

COLUMN_ALIASES = {
    "date range": "Date/Time Africa/Monrovia",
    "creator": "Creator",
    "subscription gross": "Subscription Gross",
    "new subscriptions gross": "New subscriptions Gross",
    "recurring subscriptions gross": "Recurring subscriptions Gross",
    "tips gross": "Tips Gross",
    "total earnings gross": "Total earnings Gross",
    "contribution %": "Contribution %",
    "of ranking": "OF ranking",
    "following": "Following",
    "fans with renew on": "Fans with renew on",
    "renew on %": "Renew on %",
    "new fans": "New fans",
    "active fans": "Active fans",
    "change in expired fan count": "Change in expired fan count",
    "message gross": "Message Gross",
    "creator group": "Creator group",
    "avg spend per spender gross": "Avg spend per spender Gross",
    "avg spend per transaction gross": "Avg spend per transaction Gross",
    "avg earnings per fan gross": "Avg earnings per fan Gross",
    "avg subscription length": "Avg subscription length",
}

# =========================
# AUTH
# =========================

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(creds)

spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)

raw_ws = spreadsheet.worksheet(RAW_TAB)
stats_ws = spreadsheet.worksheet(STATS_TAB)

st.title("KPI Dashboard Upload")

uploaded_file = st.file_uploader(
    "Upload monthly Excel file",
    type=["xlsx"],
)

# =========================
# HELPERS
# =========================


def clean(text):
    return str(text).strip().lower()


def append_by_headers(df, worksheet):
    sheet_headers = worksheet.row_values(1)

    df_map = {
        clean(col): col
        for col in df.columns
    }

    rows_to_add = []

    for _, row in df.iterrows():
        output_row = []

        for gs_header in sheet_headers:
            gs_key = clean(gs_header)

            excel_header = COLUMN_ALIASES.get(gs_key, gs_header)

            excel_key = clean(excel_header)

            if excel_key in df_map:
                value = row[df_map[excel_key]]
            else:
                value = ""

            if pd.isna(value):
                value = ""

            output_row.append(value)

        rows_to_add.append(output_row)

    if rows_to_add:
        worksheet.append_rows(
            rows_to_add,
            value_input_option="USER_ENTERED",
        )


# =========================
# PROCESS
# =========================

if uploaded_file:
    try:
        excel = pd.ExcelFile(uploaded_file)

        df_raw = pd.read_excel(
            uploaded_file,
            sheet_name=excel.sheet_names[0],
        )

        df_stats = pd.read_excel(
            uploaded_file,
            sheet_name=excel.sheet_names[1],
        )

        append_by_headers(df_raw, raw_ws)
        append_by_headers(df_stats, stats_ws)

        st.success("Upload completed successfully")

    except Exception as e:
        st.error(f"Error: {e}")
        raise
