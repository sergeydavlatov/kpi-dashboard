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
    Robust normalization to prevent format-based
    false mismatches between Excel and Google Sheets.
    """
    if pd.isna(value):
        return ""

    # Date / datetime
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    # Float — round to 2dp to avoid float noise
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(round(value, 2))

    # String — strip and lowercase to avoid whitespace/case mismatches
    return str(value).strip().lower()


def get_existing_rows(ws):
    """
    Read all rows from Google Sheet (excluding header)
    and return as a set of normalized tuples.
    """
    values = ws.get_all_values()

    if len(values) <= 1:
        return set()

    existing = set()

    for row in values[1:]:
        normalized = tuple(
            v.strip().lower()
            for v in row
        )
        existing.add(normalized)

    return existing


def build_output_row(row, google_col_count):
    """
    Build a row list aligned to Google Sheet columns,
    with clean types ready for upload.
    """
    output = []

    for i in range(google_col_count):
        value = row.iloc[i] if i < len(row) else ""

        if pd.isna(value):
            output.append("")

        # Normalize date column
        elif i == 0 and isinstance(value, pd.Timestamp):
            output.append(value.strftime("%Y-%m-%d"))

        # Convert whole floats to int
        elif isinstance(value, float) and value.is_integer():
            output.append(int(value))

        else:
            output.append(value)

    return output


def append_missing_rows(df, ws):
    """
    Append only rows not already present in Google Sheet.
    Uses full-row normalization for deduplication.
    """
    headers = ws.row_values(1)
    google_col_count = len(headers)

    existing_rows = get_existing_rows(ws)

    rows_to_add = []

    for _, row in df.iterrows():
        output_row = build_output_row(row, google_col_count)

        normalized = tuple(
            normalize_value(v) for v in output_row
        )

        if normalized in existing_rows:
            continue

        rows_to_add.append(output_row)
        existing_rows.add(normalized)

    if rows_to_add:
        ws.append_rows(
            rows_to_add,
            value_input_option="USER_ENTERED",
        )

    return len(rows_to_add)


def deduplicate_dataframe(df):
    """
    Remove fully duplicate rows from the incoming
    Excel data before processing.
    """
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    dropped = before - after

    if dropped > 0:
        st.info(f"Removed **{dropped}** fully duplicate rows from the uploaded file before processing.")

    return df

# ==========================================
# PROCESS FILE
# ==========================================

if uploaded_file:

    try:
        excel = pd.ExcelFile(uploaded_file)
        sheet_names = excel.sheet_names

        if len(sheet_names) < 2:
            st.error("Excel file must contain at least 2 sheets.")
            st.stop()

        # Read SECOND Excel tab only
        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[1],
        )

        # Remove fully identical rows from source file
        df = deduplicate_dataframe(df)

        st.info(f"Found **{len(df)}** rows in the uploaded file after deduplication.")

        added_count = append_missing_rows(df, worksheet)

        if added_count > 0:
            st.success(f"Upload complete. Added **{added_count}** new rows.")
        else:
            st.warning("No new rows to add — all data already exists in the sheet.")

    except Exception as e:
        st.error(f"Error: {e}")
        raise
