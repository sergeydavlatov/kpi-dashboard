import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIG
# =========================

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1EWT1qzyyutsfclz9RK_lcjJRqi6W9dodTBpXEQUPN1E/edit?gid=0#gid=0"

RAW_TAB = "Raw data"
STATS_TAB = "Raw data Stats"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =========================
# GOOGLE AUTH
# =========================

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES,
)

client = gspread.authorize(creds)

spreadsheet = client.open_by_url(GOOGLE_SHEET_URL)

raw_ws = spreadsheet.worksheet(RAW_TAB)
stats_ws = spreadsheet.worksheet(STATS_TAB)

# =========================
# UI
# =========================

st.title("KPI Dashboard Upload")

uploaded_file = st.file_uploader(
    "Upload monthly Excel file",
    type=["xlsx"],
)

# =========================
# HELPERS
# =========================


def append_by_headers(df, worksheet):
    """
    Match dataframe columns to existing Google Sheet headers.
    Append rows.
    """

    headers = worksheet.row_values(1)

    # Build empty rows using Google Sheet column order
    rows_to_add = []

    for _, row in df.iterrows():
        output_row = []

        for header in headers:
            if header in df.columns:
                value = row[header]
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
# PROCESS FILE
# =========================

if uploaded_file:

    try:
        excel = pd.ExcelFile(uploaded_file)

        sheet_names = excel.sheet_names

        if len(sheet_names) < 2:
            st.error("Excel file must contain at least 2 sheets")
            st.stop()

        # first sheet
        df_raw = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[0],
        )

        # second sheet
        df_stats = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[1],
        )

        # append data
        append_by_headers(df_raw, raw_ws)
        append_by_headers(df_stats, stats_ws)

        st.success("Upload completed successfully")

    except Exception as e:
        st.error(f"Error: {e}")
        raise
