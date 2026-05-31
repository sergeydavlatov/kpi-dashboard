import streamlit as st
import pandas as pd
import gspread
import hashlib
import time
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

def fetch_with_retry(fn, retries=5, delay=10):
    """Call a gspread function, retrying on 503."""
    for attempt in range(retries):
        try:
            return fn()
        except gspread.exceptions.APIError as e:
            if "503" in str(e) and attempt < retries - 1:
                st.write(f"⚠️ Google API unavailable, retrying in {delay}s... (attempt {attempt + 1}/{retries})")
                time.sleep(delay)
            else:
                raise


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
    Single API call to fetch all existing rows,
    returned as a set of hashes.
    """
    st.write("⏳ Reading existing rows from Google Sheet...")

    values = fetch_with_retry(lambda: ws.get_all_values())

    if not values or len(values) <= 1:
        st.write("ℹ️ Sheet is empty — all rows will be added.")
        return set(), len(values[0]) if values else 0

    headers = values[0]
    st.write(f"✅ Sheet has **{len(values) - 1}** existing rows, **{len(headers)}** columns.")

    existing_hashes = set()
    for row in values[1:]:
        normalized = tuple(v.strip().lower() for v in row)
        existing_hashes.add(hash_row(normalized))

    return existing_hashes, len(headers)


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
    existing_hashes, google_col_count = get_existing_hashes(ws)

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

            fetch_with_retry(lambda b=batch: ws.append_rows(
                b,
                value_input_option="USER_ENTERED",
            ))

    return len(rows_to_add)

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

        st.write(f"📄 Reading sheet: `{sheet_names[1]}`")

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
