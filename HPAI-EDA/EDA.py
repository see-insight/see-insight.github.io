"""
Exploratory Data Analysis for the early detection of HPAI in cows
using robotic milking project
Data is collected by the DRIVE Lab from videos into Excel spreadsheets
Contributions by Brendan Daly
"""

# Load in necessary libraries
from pathlib import Path
import re
from datetime import datetime, date
import numpy as np
import pandas as pd
import os
from IPython.display import display
import matplotlib.pyplot as plt
import seaborn as sns

# Handles the export irregularities: tab names that vary between cows,
# two-row headers, 12- vs 14-column Quality layouts, AVG/SUM/SUU summary
# rows, OCR-corrupted dates ('10/S/2024', '202-4', '10/15/202410:09 AM'),
# implausible years (0202, 3034, 1900), and 'h:mm'/'mm:ss' durations.

# Translation table for OCR letter/digit mistakes
# (S read for 5, O for 0, l/I for 1, ? as a stray mark)
_OCR_CHAR_FIXES = str.maketrans({"S": "5", "O": "0", "o": "0", "l": "1", "I": "1", "?": ""})

def repair_date_string(s):
    """Fix common OCR corruption in date strings ('10/S/2024' -> '10/5/2024')."""
    # Leave non-text values alone
    if not isinstance(s, str):
        return s
    s = s.strip()
    # Only repair tokens that look like a date with a few bad characters
    if re.fullmatch(r"[0-9SsOolI?/\-\.A-Za-z]{6,12}", s):
        head = s
        # Repair digit-like tokens (no long words inside), e.g. '10/S/2024'
        if re.search(r"\d", s) and not re.search(r"[A-Za-z]{3,}", s):
            head = s.translate(_OCR_CHAR_FIXES)
        return head
    return s

def parse_date(val):
    """Parse a date/datetime from datetime objects or the many string formats.

    Handles: datetime, '10/1/2024' (m/d/y), '15-Oct-24', '24 Aug 2024',
    concatenated datetimes ('10/15/202410:09 AM'), OCR-corrupted variants.
    Returns pd.Timestamp (time attached when present) or NaT.
    """
    # Already a datetime/Timestamp from Excel — just check the year is sane
    if isinstance(val, (datetime, pd.Timestamp)):
        ts = pd.Timestamp(val)
        return ts if 2014 <= ts.year <= 2026 else pd.NaT
    if isinstance(val, date):
        ts = pd.Timestamp(val)
        return ts if 2014 <= ts.year <= 2026 else pd.NaT
    # Empty cell -> missing date
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return pd.NaT

    # Clean the text and fix OCR mistakes
    s = repair_date_string(str(val).strip())
    if not s:
        return pd.NaT

    # Insert missing space in concatenated datetime: '10/15/202410:09 AM'
    s = re.sub(r"(\d{1,2}/\d{1,2}/\d{2,4})(\d{1,2}:\d{2})", r"\1 \2", s)
    # Repair OCR-split year: '9/25/202-4' -> '9/25/2024'
    s = re.sub(r"(\d{1,2}/\d{1,2}/\d{2,4})[-\.](\d{1,2})(?=\s|$|\d{2}:)",
               r"\1\2", s)

    # Try m/d/yyyy with optional time and AM/PM
    m = re.match(
        r"^(\d{1,2})/(\d{1,2})/(\d{2,4})"
        r"(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?)?", s)
    if m:
        mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Two-digit years mean 20xx
        if y < 100:
            y += 2000
        try:
            ts = pd.Timestamp(year=y, month=mo, day=d)
        except ValueError:
            return pd.NaT
        # Reject impossible years (OCR corruption like '0202' or '3034')
        if not (2014 <= ts.year <= 2026):
            return pd.NaT
        # Attach the time of day if the string had one
        if m.group(4):
            hh, mm = int(m.group(4)), int(m.group(5))
            # Convert 12-hour clock to 24-hour
            if m.group(7) and m.group(7).upper() == "PM" and hh < 12:
                hh += 12
            if m.group(7) and m.group(7).upper() == "AM" and hh == 12:
                hh = 0
            ts = ts + pd.Timedelta(hours=hh, minutes=mm,
                                   seconds=int(m.group(6) or 0))
        return ts

 # Try the text month formats: '15-Oct-24' / '24 Aug 2024'
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%d %b %Y", "%d %b %y"):
        try:
            ts = pd.Timestamp(datetime.strptime(s, fmt))
            if 2014 <= ts.year <= 2026:
                return ts
            return pd.NaT
        except ValueError:
            pass

    # Nothing worked -> missing date
    return pd.NaT

def to_duration_minutes(val, spec):
    """Convert 'h:mm'/'mm:ss' duration strings to minutes.

    spec='hours'  -> '6:55' means 6h55m (milking interval)
    spec='minutes'-> '5:28' means 5m28s (box/treat/milk times)
    """
    # Empty cell -> missing
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    # A bare number is not a duration we can interpret
    if isinstance(val, (int, float)):
        return np.nan
    # Fix OCR mistakes inside the duration ('U:U8' -> '0:08')
    s = str(val).strip().translate(str.maketrans({"U": "0", "u": "0", "O": "0", "?": "0"}))
    # Match h:mm or h:mm:ss
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", s)
    if not m:
        return np.nan
    a, b = int(m.group(1)), int(m.group(2))
    # Convert to minutes depending on what the column means
    if spec == "hours":
        return a * 60 + b
    return a + b / 60

def to_num(val):
    """Coerce a cell to float, handling OCR artifacts, '%' and stray text."""
    # Empty cell -> missing
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    # Already a number
    if isinstance(val, (int, float)):
        return float(val)
    # Strip % signs and thousands separators
    s = str(val).strip().replace("%", "").replace(",", "")
    # Common placeholder strings for missing values
    if s in ("", "-", "NaN", "nan"):
        return np.nan
    # Fix OCR-corrupted digits, e.g. '6?' or '1O.2'
    if re.search(r"\d", s) and not re.search(r"[A-Za-z]{2,}", s):
        s = s.translate(_OCR_CHAR_FIXES)
    try:
        return float(s)
    except ValueError:
        return np.nan

def _norm_cols(df):
    """Column-name normalization: nbsp -> space, collapse whitespace."""
    df.columns = (
        df.columns.astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return df

def _drop_summary_rows(df, first_col):
    """Remove AVG/SUM/AVC/SUU/TOTAL summary rows (first column holds the marker)."""
    # These rows sit at the top of each tab and are not real daily records
    mask = (df[first_col].astype(str).str.strip().str.upper()
            .str.match(r"^(AV[GCSU]?|SU[MNU]?|TOTA?L?)$"))
    return df[~mask].copy()

def _read_raw(path, sheet, nrows=None):
    # header=None: the real header rows are handled manually per tab type
    return pd.read_excel(path, sheet_name=sheet, header=None, nrows=nrows)

def fingerprint_sheets(path):
    """Map sheet name -> table type by header content (tab names vary)."""
    # Read only the first 2 rows of every tab to identify it
    sig = pd.read_excel(path, sheet_name=None, header=None, nrows=2)
    mapping = {}
    for name, df in sig.items():
        # Join all header text into one string to search for signatures
        text = " | ".join(str(x) for x in df.values.flatten() if pd.notna(x))
        ncol = df.shape[1]
        if "Milk Yield Expected" in text and "Device Name" not in text:
            kind = "quality"
        elif "Device Name" in text:
            kind = "visits"
        elif "Failures Avg." in text:
            kind = "daily_milk"
        elif "Predicted Production" in text:
            kind = "lactation"
        elif "Rest Feed" in text and ncol <= 6:
            kind = "feed"
        else:
            kind = "events"
        mapping[name] = kind
    return mapping

"""Clean Columns"""
def _raw_daily_milk(path, sheet):
    df = _read_raw(path, sheet, nrows=None)
    # Keep the first 16 columns and give them standard names
    df = _norm_cols(df.iloc[:, :16].copy())
    df.columns = ["date", "lactation_days", "programmed_rest_feed", "rest_feed",
                  "day_production", "day_production_dev", "isk", "milkings",
                  "refusals", "failures", "milkings_avg", "refusals_avg",
                  "failures_avg", "fat_indication", "protein_indication",
                  "lactose_indication"]
    return df.reset_index(drop=True)

def _quality_column_names(raw):
    """Naming logic for the two Quality layout variants (two-row header with
    quarter labels vs single-row header). Conductivity/color-code columns get
    quarter suffixes from labels when present, else positionally (export
    order is always LF, RF, LR, RR)."""
    # Large exports have a single header row that says 'Conductivity'
    first = " ".join(str(x) for x in raw.iloc[0].tolist() if pd.notna(x))
    if "conductivity" in first.lower():
        header_rows = [raw.iloc[0].tolist()]
        body_start = 1
    else:
        # Small exports have a quarter-label row above the real header
        header_rows = [raw.iloc[0].tolist(), raw.iloc[1].tolist()]
        body_start = 2

    names, current_q = [], None
    cond_idx = 0
    quarter_order = ["lf", "rf", "lr", "rr"]
    # Walk the columns and build a standard name for each one
    for col_i in range(raw.shape[1]):
        a = str(header_rows[0][col_i]).strip() if col_i < len(header_rows[0]) and pd.notna(header_rows[0][col_i]) else ""
        b = str(header_rows[1][col_i]).strip() if len(header_rows) > 1 and col_i < len(header_rows[1]) and pd.notna(header_rows[1][col_i]) else ""
        single = len(header_rows) == 1
        label = b if not single else a
        # Quarter labels (LF/RF/LR/RR) sit above the conductivity columns
        if not single and a.upper() in ("LF", "RF", "LR", "RR"):
            current_q = a.lower()
        ll = label.lower()
        if ll.startswith("date"):
            names.append("datetime")
        elif ll.startswith("conductivity"):
            # No labels in the single-row layout -> assign quarters in order
            if single:
                current_q = quarter_order[min(cond_idx, 3)]
                cond_idx += 1
            names.append(f"conductivity_{current_q}" if current_q else "conductivity")
        elif "color" in ll:
            names.append(f"color_code_{current_q}" if current_q else "color_code")
        elif "temp" in ll:
            names.append("temp_milk")
        elif "milk yield" in ll and "expect" not in ll:
            names.append("milk_yield")
        elif "expect" in ll:
            names.append("milk_yield_expected")
        elif "address" in ll:
            names.append("address")
        elif "failure" in ll:
            names.append("failure")
        else:
            # Unknown column -> keep it with a placeholder name
            names.append(f"extra_{len(names)}")
    return names, body_start

def _raw_quality(path, sheet):
    raw = _read_raw(path, sheet, nrows=None)
    names, body_start = _quality_column_names(raw)
    # Drop the header rows, keep the data rows
    body = raw.iloc[body_start:].copy()
    # Tolerate extra/missing trailing columns between cows
    n = min(body.shape[1], len(names))
    body = body.iloc[:, :n]
    body.columns = names[:n]
    return body.reset_index(drop=True)

def _raw_visits(path, sheet):
    raw = _read_raw(path, sheet, nrows=None)
    # Visits always has a 2-row header (group labels + real names)
    body = raw.iloc[2:].copy()
    quarters = ["lf", "rf", "lr", "rr"]
    names = (["datetime", "device_name", "milk_yield", "milk_yield_expect",
              "visit_result", "milk_speed", "milk_speed_max", "interv",
              "box_time", "treat_time", "temp_milk"]
             + [f"dead_milk_time_{q}" for q in quarters]
             + [f"milk_time_{q}" for q in quarters]
             + [f"attachments_{q}" for q in quarters]
             + ["milk_destin", "routing_direction", "bottle_num"])
    # Robust to extra/missing trailing columns (e.g., a stray 27th empty col)
    n = min(body.shape[1], len(names))
    body = body.iloc[:, :n]
    body.columns = names[:n]
    return body.reset_index(drop=True)

def _raw_lactation(path, sheet):
    df = _read_raw(path, sheet, nrows=None)
    # One row per lactation, 19 columns
    df = _norm_cols(df.iloc[:, :19].copy())
    df.columns = ["lactation_number", "calving_date", "lactation_production",
                  "predicted_production_305d", "milk_separated", "lactation_days",
                  "day_production", "milkings", "milk_speed", "refusals", "failures",
                  "amount_total", "rest_feed_total", "fat_pct", "protein_pct",
                  "lactose_pct", "fat_indication", "protein_indication",
                  "lactose_indication"]
    return df.reset_index(drop=True)

# Event-type patterns: match the text after OCR fixes
_EVENT_TYPE_PATTERNS = [
    (r"^\s*heat\b", "heat"),
    (r"^\s*health\b", "health"),
    (r"^\s*dry off\b", "dry_off"),
    (r"^\s*calving\b", "calving"),
    (r"^\s*pregnancy check\b", "pregnancy_check"),
    (r"^\s*insemination\b", "insemination"),
    (r"^\s*transfer in\b", "transfer_in"),
    (r"^\s*reminder\b", "reminder"),
]

def _raw_events(path, sheet):
    """Event log: section rows ('Lactation 4') + event rows. Structural
    parsing here; dates/details stay raw for the ANALYZE stage."""
    raw = _read_raw(path, sheet, nrows=None)
    rows = []
    current_lact = np.nan
    for _, r in raw.iterrows():
        c0 = str(r.iloc[0]).strip() if pd.notna(r.iloc[0]) else ""
        # A row starting with 'Lactation N' starts a new section
        lact_m = re.match(r"^\s*Lactation\s*(\d+)", c0, flags=re.I)
        if lact_m:
            current_lact = int(lact_m.group(1))
            continue
        # Skip completely empty rows
        if r.dropna().empty:
            continue
        desc = str(r.iloc[1]) if pd.notna(r.iloc[1]) else ""
        # Match the event type against the known patterns
        event_type = None
        for pat, name in _EVENT_TYPE_PATTERNS:
            if re.match(pat, desc, flags=re.I):
                event_type = name
                break
        if event_type is None:
            # OCR typo fallback: 'Heit 74 ...' -> heat
            if re.match(r"^\s*H[aeu][io]?[tl]", desc, flags=re.I):
                event_type = "heat"
            else:
                event_type = "other"
        # Pull the lactation day out of the description text
        day_m = re.search(r"(\d+)\s*lactation days", desc, flags=re.I)
        rows.append({
            "date": r.iloc[0],  # RAW; parsed in clean stage
            "lactation_section": current_lact,
            "event_type": event_type,
            "lactation_day": day_m.group(1) if day_m else None,
            "detail_1": r.iloc[2] if len(r) > 2 else None,
            "detail_2": r.iloc[3] if len(r) > 3 else None,
            "detail_3": r.iloc[4] if len(r) > 4 else None,
            "detail_4": r.iloc[5] if len(r) > 5 else None,
            "raw_desc": desc,
        })
    return pd.DataFrame(rows)

def _raw_feed(path, sheet):
    df = _read_raw(path, sheet, nrows=None)
    # Feed is a small 5-column daily table
    df = _norm_cols(df.iloc[:, :5].copy())
    df.columns = ["date", "lactation_days", "day_production",
                  "programmed_feed", "rest_feed"]
    return df.reset_index(drop=True)

_RAW_PARSERS = {
    "daily_milk": _raw_daily_milk,
    "quality": _raw_quality,
    "visits": _raw_visits,
    "lactation": _raw_lactation,
    "events": _raw_events,
    "feed": _raw_feed,
}

"""Clean Data"""
def _clean_daily_milk(df):
    # Remove AVG/SUM rows first
    df = _drop_summary_rows(df, "date")
    # Parse all the date formats into real datetimes
    df["date"] = df["date"].apply(parse_date)
    # Coerce every other column to numbers
    for c in df.columns[1:]:
        df[c] = df[c].apply(to_num)
    # Drop rows without a usable date
    return df.dropna(subset=["date"]).reset_index(drop=True)

def _clean_quality(df):
    df = _drop_summary_rows(df, "datetime")
    df["datetime"] = df["datetime"].apply(parse_date)
    for c in df.columns[1:]:
        df[c] = df[c].apply(to_num)
    return df.dropna(subset=["datetime"]).reset_index(drop=True)

def _clean_visits(df):
    quarters = ["lf", "rf", "lr", "rr"]
    df = _drop_summary_rows(df, "datetime")
    df["datetime"] = df["datetime"].apply(parse_date)
    # Duration columns get special handling (they are 'h:mm' text)
    duration_cols = (["interv", "box_time", "treat_time"]
                     + [f"dead_milk_time_{q}" for q in quarters]
                     + [f"milk_time_{q}" for q in quarters])
    num_cols = [c for c in df.columns if c not in ("datetime", "device_name",
                                                   "visit_result", "milk_destin",
                                                   "routing_direction", *duration_cols)]
    for c in num_cols:
        df[c] = df[c].apply(to_num)
    # interv is h:mm (hours since last milking); the rest are mm:ss
    df["interv"] = df["interv"].apply(lambda v: to_duration_minutes(v, "hours"))
    for c in ["box_time", "treat_time"] + [f"dead_milk_time_{q}" for q in quarters] \
            + [f"milk_time_{q}" for q in quarters]:
        df[c] = df[c].apply(lambda v: to_duration_minutes(v, "minutes"))
    return df.dropna(subset=["datetime"]).reset_index(drop=True)

def _clean_lactation(df):
    df = _drop_summary_rows(df, "lactation_number")
    df["calving_date"] = df["calving_date"].apply(parse_date)
    df["lactation_number"] = df["lactation_number"].apply(to_num)
    for c in df.columns[2:]:
        df[c] = df[c].apply(to_num)
    return df.dropna(subset=["lactation_number"]).reset_index(drop=True)

def _clean_events(df):
    df = df.copy()
    df["date"] = df["date"].apply(parse_date)
    # Lactation day was captured as text -> make it numeric
    df["lactation_day"] = pd.to_numeric(df["lactation_day"], errors="coerce")
    # Detail columns mix text and numbers -> make them all text
    for c in ["detail_1", "detail_2", "detail_3", "detail_4"]:
        df[c] = df[c].map(lambda v: None if pd.isna(v) else str(v))
    return df.reset_index(drop=True)

def _clean_feed(df):
    df = _drop_summary_rows(df, "date")
    df["date"] = df["date"].apply(parse_date)
    for c in df.columns[1:]:
        df[c] = df[c].apply(to_num)
    return df.dropna(subset=["date"]).reset_index(drop=True)

_CLEANERS = {
    "daily_milk": _clean_daily_milk,
    "quality": _clean_quality,
    "visits": _clean_visits,
    "lactation": _clean_lactation,
    "events": _clean_events,
    "feed": _clean_feed,
}

def _make_cols_unique(df):
    """Ensure unique column names (dynamic parsers can emit duplicates)."""
    cols = pd.Series(df.columns.astype(str))
    for c in cols[cols.duplicated()].unique():
        hits = cols == c
        for n, i in enumerate(cols[hits].index[1:], start=2):
            cols[i] = f"{c}_{n}"
    df.columns = cols.tolist()
    return df

def _cow_id_from_path(path):
    # Cow ID comes from the file name: 'Robot Farm #<id>.xlsx'
    m = re.search(r"#\s*(\d+)", os.path.basename(path))
    return int(m.group(1)) if m else None

def parse_workbook_raw(path):
    """PARSE stage: one workbook -> (cow_id, {table_type: raw DataFrame})."""
    cow_id = _cow_id_from_path(path)
    # Identify what each tab is, then read it with standard column names
    sheets = fingerprint_sheets(path)
    tables = {}
    errors = {}
    for sheet_name, kind in sheets.items():
        try:
            tables[kind] = _make_cols_unique(_RAW_PARSERS[kind](path, sheet_name))
        except Exception as e:
            # Log the problem, never silently drop the file
            errors[kind] = f"{sheet_name}: {type(e).__name__}: {e}"
    return cow_id, tables, errors

def clean_table(kind, df):
    """CLEAN stage: apply all value cleaning to one raw table of `kind`."""
    return _CLEANERS[kind](df.copy())

"""Parse Data"""
# Folder containing 'Robot_dairy_results.xlsx' and 'Robot Farm #*.xlsx'
data_directory = Path(__file__).parent / "data"

# Read in the HPAI test results (cleaned later, in its own section)
HPAI_results = pd.read_excel(data_directory / "Robot_dairy_results.xlsx")

# Read every cow workbook into RAW tables.
# Column names are standardized, but values are untouched on purpose:
# dates are still text, durations are still 'h:mm' strings.
Robot_milking_data = {}   # {file_name: {table_type: raw DataFrame}}
for file_path in sorted(data_directory.glob("Robot Farm #*.xlsx")):
    print("Parsing:", file_path.name)
    cow_id, tables, errors = parse_workbook_raw(str(file_path))
    # Report any tab that failed to parse — never silently skip it
    if errors:
        print("  ISSUES:", errors)
    Robot_milking_data[file_path.name] = tables

print(f"\nParsed {len(Robot_milking_data)} workbooks")
# More initial data analysis
# HPAI Results pre-clean analysis
def analyze_HPAI_results(data_dict, label):
    print(f"\n##### {label} #####")
    # First 3 rows
    print(data_dict.head(3))
    # Last 3 rows
    print(data_dict.tail(3))
    print("\nNumber of rows:")
    print(len(data_dict))
    print("\nUnique values:")
    print(data_dict.nunique())
    print("\nDuplicates")
    HPAI_results_duplicates = data_dict[data_dict.duplicated()]
    print(HPAI_results_duplicates)
    print("\nNumber of duplicate rows:", data_dict.duplicated().sum())

analyze_HPAI_results(HPAI_results, "PRE-CLEAN")
# Robotic milking data pre-clean analysis
# Tables are keyed by table type: 'daily_milk', 'quality', 'visits',
# 'lactation', 'events', 'feed'. Data is still RAW here: expect '10/S/2024'-
# style dates, '5:28' durations, and AVG/SUM rows. That is intentional.

def analyze_robot_data(data_dict, label):
    total_files = len(data_dict)
    total_tabs = sum(len(sheets) for sheets in data_dict.values())
    print(f"\n##### {label} #####")
    print("\nNumber of files:", total_files)
    print("\nNumber of tabs:", total_tabs)

    for file_name, sheets in data_dict.items():

        # Separate files with lines
        print("\n" + "=" * 60)
        print("File:", file_name)
        print("=" * 60)

        for sheet_name, df in sheets.items():

            # Separate tabs with lines
            print("\n" + "-" * 40)
            print("Tab:", sheet_name)
            print("-" * 40)

            print("\nFirst 3 rows:")
            print(df.head(3))

            print("\nLast 3 rows:")
            print(df.tail(3))

            print("\nUnique values:")
            print(df.nunique())

            duplicates = df[df.duplicated()]
            print("\nDuplicates:")
            print(duplicates)

            print("\nNumber of duplicate rows:", df.duplicated().sum())

            print("\nNumber of NA:")
            print(df.isna().sum())

analyze_robot_data(Robot_milking_data, "PRE-CLEAN")

# Clean the data
# Clean HPAI Results
# Normalize whitespace in column names
HPAI_results.columns = (
    HPAI_results.columns
    .astype(str)
    .str.replace("\xa0", " ", regex=False)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# Rename columns
HPAI_results = HPAI_results.rename(columns={
    "Influenza A ELISA SN (S/N) Serum": "ELISA_SN",
    "Influenza A ELISA Interpretation Serum 05/22/25": "ELISA_Interpretation"
})

# Make classification column for ML with simple numbers
HPAI_results["ELISA_Classification"] = HPAI_results["ELISA_Interpretation"].map({
    "Negative": 0,
    "Suspect": 1,
    "Positive": 2
})

# Make and keep cow IDs as strings
HPAI_results["Cow_ID"] = HPAI_results["Cow_ID"].astype(str).str.strip()

# Keep ELISA SN as numeric
HPAI_results["ELISA_SN"] = pd.to_numeric(
    HPAI_results["ELISA_SN"],
    errors="coerce"
)

# Normalize whitespace in this column
HPAI_results["ELISA_Interpretation"] = (
    HPAI_results["ELISA_Interpretation"]
    .astype(str)
    .str.strip()
    .str.title()
)

# Keep the date as a separate column for now
HPAI_results["Test_Date"] = pd.to_datetime("2025-05-22")

# Check for missing values again
print("Number of NA:", HPAI_results.isna().sum())

# Check for duplicates again
print("Exact duplicate rows:", HPAI_results.duplicated().sum())

display(HPAI_results)

# Clean Robotic Milking Data
# Clean every raw table: OCR date repair, numeric coercion, duration ->
# minutes, AVG/SUM row removal, dedup. Same result as one-call parsing.
Robot_milking_data_clean = {}
for file_name, tables in Robot_milking_data.items():
    cleaned = {}
    for kind, raw_df in tables.items():
        try:
            cleaned[kind] = clean_table(kind, raw_df)
        except Exception as e:
            print(f"CLEAN FAILED: {file_name} {kind}: {e}")
    Robot_milking_data_clean[file_name] = cleaned

# Data analysis with clean data
# HPAI Results Data Analysis
analyze_HPAI_results(HPAI_results, "POST-CLEAN")

# Robotic Milking Data Analysis
analyze_robot_data(Robot_milking_data_clean, "POST-CLEAN")

# Rename columns/features for ease of use
RENAME_MAP = {
    # ---- daily_milk / feed ----
    "date": "Date",
    "datetime": "Date Time",
    "lactation_days": "Lactation Days",
    "programmed_rest_feed": "Programmed Rest Feed",
    "rest_feed": "Rest Feed",
    "day_production": "Day Production",
    "day_production_dev": "Day Production Dev",
    "isk": "ISK",
    "milkings": "Milkings",
    "refusals": "Refusals",
    "failures": "Failures",
    "milkings_avg": "Milkings Avg",
    "refusals_avg": "Refusals Avg",
    "failures_avg": "Failures Avg",
    "fat_indication": "Fat Indication",
    "protein_indication": "Protein Indication",
    "lactose_indication": "Lactose Indication",
    # ---- quality / visits ----
    "address": "Address",
    "failure": "Failure",
    "milk_yield": "Milk Yield",
    "milk_yield_expected": "Milk Yield Expected",
    "milk_yield_expect": "Milk Yield Expected",
    "conductivity_lf": "Conductivity LF",
    "conductivity_rf": "Conductivity RF",
    "conductivity_lr": "Conductivity LR",
    "conductivity_rr": "Conductivity RR",
    "color_code_lf": "Color Code LF",
    "color_code_rf": "Color Code RF",
    "color_code_lr": "Color Code LR",
    "color_code_rr": "Color Code RR",
    "temp_milk": "Milk Temperature",
    "device_name": "Device Name",
    "visit_result": "Visit Result",
    "milk_speed": "Milk Speed",
    "milk_speed_max": "Milk Speed Max",
    "interv": "Milking Interval (min)",
    "box_time": "Box Time (min)",
    "treat_time": "Treat Time (min)",
    "dead_milk_time_lf": "Dead Milk Time LF (min)",
    "dead_milk_time_rf": "Dead Milk Time RF (min)",
    "dead_milk_time_lr": "Dead Milk Time LR (min)",
    "dead_milk_time_rr": "Dead Milk Time RR (min)",
    "milk_time_lf": "Milk Time LF (min)",
    "milk_time_rf": "Milk Time RF (min)",
    "milk_time_lr": "Milk Time LR (min)",
    "milk_time_rr": "Milk Time RR (min)",
    "attachments_lf": "Attachments LF",
    "attachments_rf": "Attachments RF",
    "attachments_lr": "Attachments LR",
    "attachments_rr": "Attachments RR",
    "milk_destin": "Milk Destination",
    "routing_direction": "Routing Direction",
    "bottle_num": "Bottle Num",
    # ---- lactation ----
    "lactation_number": "Lactation Number",
    "calving_date": "Calving Date",
    "lactation_production": "Lactation Production",
    "predicted_production_305d": "Predicted Production 305d",
    "milk_separated": "Milk Separated",
    "amount_total": "Amount Total",
    "rest_feed_total": "Rest Feed Total",
    "fat_pct": "Fat %",
    "protein_pct": "Protein %",
    "lactose_pct": "Lactose %",
    # ---- events ----
    "event_type": "Event Type",
    "lactation_section": "Lactation Section",
    "lactation_day": "Lactation Day",
    "raw_desc": "Event Description",
}

def apply_rename(tables_dict, rename_map):
    # Apply the same rename to every table of every cow
    renamed = {}
    for file_name, tables in tables_dict.items():
        renamed[file_name] = {
            kind: df.rename(columns=rename_map) for kind, df in tables.items()
        }
    return renamed

Robot_milking_data_renamed = apply_rename(Robot_milking_data_clean, RENAME_MAP)

# Correlation Matrix
# Stack every cow's clean daily-milk table into one big table
daily_all = pd.concat(
    [t["daily_milk"] for t in Robot_milking_data_clean.values()
     if "daily_milk" in t],
    ignore_index=True,
)
# Correlate the main daily signals with each other
corr_columns = ["day_production", "fat_indication", "protein_indication",
                "milkings", "refusals", "failures", "isk"]
corr = daily_all[corr_columns].corr()
print("\nCorrelation matrix (daily milk signals):")
display(corr.round(2))

# Plots
# Correlation Matrix plot
# Make the figure bigger so the labels fit
plt.figure(figsize=(8, 6))

# Heatmap of the correlation matrix
sns.heatmap(
    corr,                      # the matrix you already computed
    annot=True,                # print the numbers in each cell
    fmt=".2f",                 # 2 decimal places
    cmap="RdBu_r",             # red = negative, blue = positive
    vmin=-1, vmax=1,           # fix the color scale so colors are comparable
    center=0,                  # 0 is white
    square=True,               # square cells look cleaner
    linewidths=0.5,
    cbar_kws={"label": "Correlation (r)"}
)

# Title and layout
plt.title("Correlation of Daily Milk Signals")
plt.tight_layout()

# Save as PNG (don't commit png please)
plt.savefig("correlation_matrix.png", dpi=300)

# Show it in PyCharm
plt.show()

# Conclusion
# Cleaning the robotic milking data was very complex and required many complex functions.
# Our correlation matrix doesn't have any strong daily signals features.
# Because we only had 1 farm ELISA test for this timeframe, an unsupervised model
# will be by far the superior choice, unless there is lost results we can find.
# All non-redundant features will be used in our future model.
# Literature shows that HPAI is often less severe in cows than poultry, and other
# methods include cameras to see cow facial behavior, thermal cameras, and internal chips.
# Cow parameters having to do with lactation, pregnancy, and other variables likely
# have more impact on their milk quality than HPAI would, making predictions complex.
# Cows with HPAI will have less milk that is thicker and colostrum-like, appetite loss,
# and a fever, along with other symptoms that can't be included in our model.