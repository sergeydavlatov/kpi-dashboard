import streamlit as st
import pandas as pd
import gspread

from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Monthly KPI Upload")

st.title("Monthly KPI Upload")

# -----------------------
# GOOGLE SHEETS AUTH
# -----------------------

scope = [
    "https://www.googleapis.com/auth/spreadsheets"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

sheet = client.open("KPI Dashboard")

raw_ws = sheet.worksheet("Raw_Data")
stats_ws = sheet.worksheet("Raw_Data_Stats")

# -----------------------
# HELPERS
# -----------------------

def clean_money(v):
    if pd.isna(v):
        return ""

    return (
        str(v)
        .replace("$", "")
        .replace(",", "")
    )


def clear_below_header(ws):
    rows = ws.row_count
    cols = ws.col_count

    ws.batch_clear([
        f"A2:{gspread.utils.rowcol_to_a1(rows, cols)}"
    ])


def upload_dataframe(ws, df):

    clear_below_header(ws)

    values = df.fillna("").values.tolist()

    if values:
        ws.update(
            f"A2",
            values
        )


# -----------------------
# FILE UPLOAD
# -----------------------

uploaded = st.file_uploader(
    "Upload monthly Excel file",
    type=["xlsx"]
)

if uploaded:

    # ==========================
    # SHEET 1: Creator Statistics
    # ==========================

    stats1 = pd.read_excel(
        uploaded,
        sheet_name="Creator Statistics"
    )

    date_col_1 = stats1.columns[0]

    mapped_1 = pd.DataFrame({
        "Date Range": stats1[date_col_1],
        "Creator": stats1["Creator"],
        "Subscription Gross": stats1["Subscription Gross"].apply(clean_money),
        "New subscriptions Gross": stats1["New subscriptions Gross"].apply(clean_money),
        "Recurring subscriptions Gross": stats1["Recurring subscriptions Gross"].apply(clean_money),
        "Tips Gross": stats1["Tips Gross"].apply(clean_money),
        "Total earnings Gross": stats1["Total earnings Gross"].apply(clean_money),
        "Contribution %": stats1["Contribution %"],
        "OF ranking": stats1["OF ranking"],
        "Following": stats1["Following"],
        "Fans with renew on": stats1["Fans with renew on"],
        "Renew on %": stats1["Renew on %"],
        "New fans": stats1["New fans"],
        "Active fans": stats1["Active fans"],
        "Change in expired fan count": stats1["Change in expired fan count"],
        "Message Gross": stats1["Message Gross"].apply(clean_money),
        "Creator group": stats1["Creator group"],
        "Avg spend per spender Gross": stats1["Avg spend per spender Gross"].apply(clean_money),
        "Avg spend per transaction Gross": stats1["Avg spend per transaction Gross"].apply(clean_money),
        "Avg earnings per fan Gross": stats1["Avg earnings per fan Gross"].apply(clean_money),
        "Avg subscription length": stats1["Avg subscription length"],
    })

    # ==========================
    # SHEET 2: Creator Statistics Detail
    # ==========================

    stats2 = pd.read_excel(
        uploaded,
        sheet_name="Creator Statistics Detail"
    )

    date_col_2 = stats2.columns[0]

    mapped_2 = stats2.copy()

    mapped_2.rename(
        columns={
            date_col_2: "Date Range"
        },
        inplace=True
    )

    # ==========================
    # PREVIEW
    # ==========================

    st.subheader("Raw_Data preview")
    st.dataframe(mapped_1.head())

    st.subheader("Raw_Data_Stats preview")
    st.dataframe(mapped_2.head())

    # ==========================
    # UPLOAD BUTTON
    # ==========================

    if st.button("Upload to Google Sheets"):

        upload_dataframe(
            raw_ws,
            mapped_1
        )

        upload_dataframe(
            stats_ws,
            mapped_2
        )

        st.success(
            "Uploaded successfully"
        )
