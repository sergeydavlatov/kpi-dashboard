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

spreadsheet = client.open_by_url(
    GOOGLE_SHEET_URL
)

worksheet = spreadsheet.worksheet(
    TARGET_TAB
)

# ==========================================
# UI
# ==========================================

st.title("KPI Daily Raw Data Upload")

uploaded_file = st.file_uploader(
    "Upload Excel file",
    type=["xlsx"],
)

# ==========================================
# HELPERS
# ==========================================

def normalize_value(value):
    """
    Make values comparable
    between Excel + Google Sheets.
    """

    if pd.isna(value):
        return ""

    # Date / datetime
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    # Numbers
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value)

    return str(value).strip()


def get_existing_rows(ws):
    """
    Read Google Sheet rows
    excluding header.
    """

    values = ws.get_all_values()

    if len(values) <= 1:
        return set()

    existing = set()

    for row in values[1:]:

        normalized_row = tuple(
            normalize_value(v)
            for v in row
        )

        existing.add(normalized_row)

    return existing


def build_output_row(
    row,
    google_col_count,
):
    """
    Match Excel columns
    to Google columns by index.
    """

    output = []

    for i in range(
        google_col_count
    ):

        if i < len(row):
            value = row.iloc[i]
        else:
            value = ""

        if pd.isna(value):
            value = ""

        output.append(value)

    return output


def append_missing_rows(
    df,
    ws,
):
    """
    Append only rows
    not already present.
    """

    headers = ws.row_values(1)

    google_col_count = len(headers)

    existing_rows = get_existing_rows(
        ws
    )

    rows_to_add = []

    for _, row in df.iterrows():

        output_row = build_output_row(
            row,
            google_col_count,
        )

        normalized_row = tuple(
            normalize_value(v)
            for v in output_row
        )

        if normalized_row in existing_rows:
            continue

        rows_to_add.append(
            output_row
        )

        existing_rows.add(
            normalized_row
        )

    if rows_to_add:
        ws.append_rows(
            rows_to_add,
            value_input_option="USER_ENTERED",
        )

    return len(rows_to_add)

# ==========================================
# PROCESS FILE
# ==========================================

if uploaded_file:

    try:

        excel = pd.ExcelFile(
            uploaded_file
        )

        sheet_names = (
            excel.sheet_names
        )

        if len(sheet_names) < 2:
            st.error(
                "Excel file must contain at least 2 sheets"
            )
            st.stop()

        # Read SECOND Excel tab only
        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[1],
        )

        # Append only new rows
        added_count = append_missing_rows(
            df,
            worksheet,
        )

        st.success(
            f"Upload complete. Added {added_count} new rows."
        )

    except Exception as e:
        st.error(
            f"Error: {e}"
        )
        raise
