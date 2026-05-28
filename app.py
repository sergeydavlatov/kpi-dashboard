import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIG
# =========================

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1EWT1qzyyutsfclz9RK_lcjJRqi6W9dodTBpXEQUPN1E/edit?gid=1445258276#gid=1445258276"

TARGET_TAB = "Raw data Stats"

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

target_ws = spreadsheet.worksheet(TARGET_TAB)

# =========================
# UI
# =========================

st.title("Daily KPI Upload")

uploaded_file = st.file_uploader(
    "Upload monthly Excel file",
    type=["xlsx"],
)

# =========================
# HELPERS
# =========================

def normalize_date(value):
    """
    Converts date to comparable string.
    """
    if pd.isna(value):
        return ""

    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except:
        return str(value).strip()


def get_existing_dates(worksheet):
    """
    Reads existing dates from Google Sheet column A.
    Header stays ignored.
    """

    values = worksheet.col_values(1)

    if len(values) <= 1:
        return set()

    dates = set()

    for value in values[1:]:
        dates.add(normalize_date(value))

    return dates


def append_missing_rows(df, worksheet):
    """
    Append only rows whose Date Range
    does not already exist.
    """

    # Google header row
    sheet_headers = worksheet.row_values(1)
    num_cols = len(sheet_headers)

    # Existing dates
    existing_dates = get_existing_dates(worksheet)

    rows_to_add = []

    for _, row in df.iterrows():

        row_date = normalize_date(row.iloc[0])

        # Skip duplicate dates
        if row_date in existing_dates:
            continue

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

    return len(rows_to_add)

# =========================
# PROCESS FILE
# =========================

if uploaded_file:

    try:
        excel = pd.ExcelFile(uploaded_file)

        sheet_names = excel.sheet_names

        if len(sheet_names) < 2:
            st.error("Excel must contain at least 2 sheets")
            st.stop()

        # Read SECOND sheet from Excel
        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[1],
        )

        added_count = append_missing_rows(
            df,
            target_ws,
        )

        st.success(
            f"Upload completed. Added {added_count} new rows."
        )

    except Exception as e:
        st.error(f"Error: {e}")
        raise
