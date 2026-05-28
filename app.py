import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIG
# =========================

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1EWT1qzyyutsfclz9RK_lcjJRqi6W9dodTBpXEQUPN1E/edit?gid=1111412918#gid=1111412918"

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

def clear_sheet_data(worksheet):
    """
    Clears all rows except row 1 (headers).
    """

    all_values = worksheet.get_all_values()

    if len(all_values) > 1:
        worksheet.batch_clear(["A2:ZZ100000"])


def append_by_index(df, worksheet):
    """
    Push data by column order:
    Excel col A -> Google col A
    Excel col B -> Google col B
    """

    sheet_headers = worksheet.row_values(1)
    num_cols = len(sheet_headers)

    rows_to_add = []

    for _, row in df.iterrows():
        output_row = []

        for i in range(num_cols):
            if i < len(df.columns):
                value = row.iloc[i]
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

        # Read tab 1
        df_raw = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[0],
        )

        # Read tab 2
        df_stats = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[1],
        )

        # Clear previous data
        clear_sheet_data(raw_ws)
        clear_sheet_data(stats_ws)

        # Push fresh data
        append_by_index(df_raw, raw_ws)
        append_by_index(df_stats, stats_ws)

        st.success("Upload completed successfully")

    except Exception as e:
        st.error(f"Error: {e}")
        raise
