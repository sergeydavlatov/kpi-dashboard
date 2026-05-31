import streamlit as st
import pandas as pd
import gspread
import hashlib
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

# How many rows to fetch from the END of the sheet for dedup comparison.
# 365 days x 20 creators x 4 rows max = 29,200 — use 30,000 to be safe.
LOOKBACK_ROWS = 30000

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
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(round(value, 2))
    return str(value).strip().lower()


def hash_row(normalized_tuple):
    row_str = "|".join(normalized_tuple)
    return hashlib.md5(row_str.encode()).hexdigest()


def get_existing_hashes(ws):
    """
    Fetch only the last LOOKBACK_ROWS rows from Google Sheet.
    No need to scan older rows — upload file covers max 365 days.
    """
    st.write("⏳ Reading recent rows from Google Sheet...")

    try:
        total_rows = len(ws.col_values(1))  # Fast — only fetches column A
        st.write(f"📊 Google Sheet has **{total_rows}** total rows (including header).")

        if total_rows <= 1:
            st.write("ℹ️ Sheet is empty — all rows will be added.")
            return set()

        # Calculate start row — fetch last LOOKBACK_ROWS rows only
        start_row = max(2, total_rows - LOOKBACK_ROWS + 1)
        range_notation = f"A{start_row}:U{total_rows}"

        st.write(f"🔍 Fetching rows {start_row} to {total_rows} for comparison...")
        rows = ws.get(range_notation)

    except Exception as e:
        st.error(f"Failed to read Google Sheet: {e}")
        raise

    existing_hashes = set()
    for row in rows:
        normalized = tuple(v.strip().lower() for v in row)
        existing_hashes.add(hash_row(normalized))

    st.write(f"✅ Loaded **{len(existing_hashes)}** existing row hashes for comparison.")
    return existing_hashes


def build_output_row(row, google_col_count):
    output = []
    for i in range(google_col_count):
        value = row.iloc[i] if i < len(row) else ""
        if pd.isna(value):
            output.append("")
        elif i == 0 and isinstance(value, pd.Timestamp):
            output.append(value.strftime("%Y-%m-%d"))
        elif isinstance(value, float) and value.is_integer():
            output.append(int(value))
        else:
            output.append(value)
    return output


def append_missing_rows(df, ws):
    headers = ws.row_values(1)
    st.write(f"📋 Google Sheet columns ({len(headers)}): `{headers}`")
    google_col_count = len(headers)

    existing_hashes = get_existing_hashes(ws)

    rows_to_add = []

    for _, row in df.iterrows():
        output_row = build_output_row(row, google_col_count)
        normalized = tuple(normalize_value(v) for v in output_row)
        row_hash = hash_row(normalized)

        if row_hash in existing_hashes:
            continue

        rows_to_add.append(output_row)
        existing_hashes.add(row_hash)

    st.write(f"🔎 New rows to add: **{len(rows_to_add)}**")

    if rows_to_add:
        batch_size = 500
        total_batches = (len(rows_to_add) + batch_size - 1) // batch_size

        for i in range(0, len(rows_to_add), batch_size):
            batch = rows_to_add[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            st.write(f"⏳ Pushing batch {batch_num}/{total_batches} ({len(batch)} rows)...")
            try:
                ws.append_rows(
                    batch,
                    value_input_option="USER_ENTERED",
                )
            except Exception as e:
                st.error(f"Failed on batch {batch_num}: {e}")
                raise

        st.write("✅ All batches pushed successfully.")

    return len(rows_to_add)

# ==========================================
# PROCESS FILE
# ==========================================

if uploaded_file:

    try:
        excel = pd.ExcelFile(uploaded_file)
        sheet_names = excel.sheet_names
        st.write(f"📄 Sheets found: `{sheet_names}`")
        st.write(f"📄 Reading sheet: `{sheet_names[1]}`")

        if len(sheet_names) < 2:
            st.error("Excel file must contain at least 2 sheets.")
            st.stop()

        df = pd.read_excel(
            uploaded_file,
            sheet_name=sheet_names[1],
        )

        st.write(f"📊 Excel rows: **{len(df)}**, columns: **{len(df.columns)}**")
        st.write("Preview of first 3 rows:")
        st.dataframe(df.head(3))

        added_count = append_missing_rows(df, worksheet)

        if added_count > 0:
            st.success(f"✅ Upload complete. Added **{added_count}** new rows.")
        else:
            st.warning("No new rows to add — all data already exists in the sheet.")

    except Exception as e:
        st.error(f"Error: {e}")
        raise
