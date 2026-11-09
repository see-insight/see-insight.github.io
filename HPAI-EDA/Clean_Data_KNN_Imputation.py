"""
Pipeline: HPAI Robotic Milking Data Cleaning and Analysis
Project: SEE-Insight
Author: Brendan Daly
Date: November 2026

Description:
 Standalone, audited cleaning and analysis pipeline for robotic
 milking data collected from DRIVE Lab Excel spreadsheets.

 One script, no other files needed. It:
 1. Reads every per-cow workbook and the HPAI ELISA results file.
 2. Cleans all six worksheet types (explicit, manual logic, no regex).
 3. Removes clearly corrupted rows (duplicate cow-days, impossible dates)
    and columns that are missing MISSINGNESS_CUTOFF of their data.
 4. Fills remaining missing numeric values in daily_milk and quality with
    per-cow K-nearest-neighbor imputation (each cow is imputed from her
    OWN other days, because every cow has her own baseline and frequent
    value ranges). Every imputed cell is written to a log file.
 5. Runs basic analysis (shapes, summary statistics, missingness before
    and after) and saves everything.

 Outputs (all under data/clean/):
 - daily_milk.csv, quality.csv, visits.csv, lactation.csv, events.csv,
   feed.csv  (cleaned; daily_milk and quality are imputed)
 - hpai_labels.csv          (cleaned ELISA labels)
 - imputation_log.csv       (one row per imputed cell)
 - analysis_summary.txt     (the printed analysis, saved)

 Run:  python pipeline.py
 (in a Jupyter notebook cell:  %run pipeline.py)

 Next Steps: The method of imputation needs experimentation
 (ie. KNN is one method, median is another method)
 methods can be combined if applicable.
 Advanced models such as XGBoost don't require imputation
 Experiment with the parameters as well

 Edits can be done to improve and slightly alter than cleaning process

 Be careful with the extremely messy data structure, leave an audit trail and keep it reproducible
"""

# Imports and Global Configurations

# Libraries
from pathlib import Path
import warnings
from datetime import datetime
import openpyxl
import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer
from sklearn.neighbors import NearestNeighbors

# Directory configuration (everything hangs off the folder this file
# lives in, so the pipeline is portable between machines)
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR
CLEAN_DATA_DIR = DATA_DIR / "clean"

# Pipeline configuration

# Deterministic settings. KNN itself has no randomness, but the seed is
# set so any future numpy randomness is reproducible too.
RANDOM_SEED = 42

# Columns missing this fraction or more of their values are REMOVED
# (too sparse to impute reliably). Columns below the cutoff keep their
# missing values and get KNN-imputed (daily_milk and quality only).
MISSINGNESS_CUTOFF = 0.50

# Number of neighbors for KNN imputation (within the same cow).
KNN_NEIGHBORS = 5

# Tables that get KNN imputation. Text is left as-is everywhere.
IMPUTE_TABLES = ["daily_milk", "quality"]

# Remove duplicate (cow, date) rows, keeping the first occurrence.
# These are re-sent sensor records for the same cow-day.
DROP_DUPLICATE_ROWS = True

# Plausible year windows per (worksheet, date column). Rows whose date
# falls outside the window are clearly corrupted (OCR century errors
# like 2034 for 2024) and are removed. Calving dates go back further
# because older lactations are real history, not errors.
DATE_WINDOWS = {
    # Sensor tables: the study period is 2024-2026 (data collection ran
    # Jan-Dec 2024). Rows outside are out of scope -- this also removes
    # a few stray source rows with 2021/2023 dates and OCR-corrupted
    # years like 2034 or 1900.
    ("daily_milk", "Date"): (2024, 2026),
    ("quality", "Date Time"): (2024, 2026),
    ("visits", "Date Time"): (2024, 2026),
    # Calving dates legitimately reach back years (real history:
    # 2017-2024 in this data), so this window stays wide
    ("lactation", "Calving Date"): (2010, 2026),
    ("feed", "Date"): (2024, 2026),
}

# Worksheet translation dictionary

# Every worksheet name seen in the 97 workbooks, mapped to its standard
# category. Kept explicit (one entry per name) so a new export with an
# unknown name is flagged instead of silently guessed.

TAB_TRANSLATION_MAP = {
    # "Daily Milk #1": "daily_milk",
    # "Quality #1": "quality",
    "Daily milk #85": "daily_milk", "Daily Milk #1": "daily_milk", "Daily milk #10": "daily_milk",
    "MD #102": "daily_milk", "MD #103": "daily_milk", "MD #104": "daily_milk", "MD #105": "daily_milk",
    "MD #106": "daily_milk", "MD #109": "daily_milk", "Daily milk #11": "daily_milk",
    "MD #111": "daily_milk", "MD #112": "daily_milk", "MD #113": "daily_milk", "MD #115": "daily_milk",
    "MD #118": "daily_milk", "Daily milk #12": "daily_milk", "Daily milk#12": "daily_milk", "MD #122": "daily_milk",
    "MD #123": "daily_milk", "MD #125": "daily_milk", "MD #128": "daily_milk", "MD #129": "daily_milk",
    "MD #130": "daily_milk", "MD #134": "daily_milk", "MD #137": "daily_milk", "MD #139": "daily_milk",
    "Daily milk #14": "daily_milk", "MD #141": "daily_milk", "MD #143": "daily_milk",
    "MD #144": "daily_milk", "MD #145": "daily_milk", "MD #146": "daily_milk", "MD #147": "daily_milk",
    "MD #148": "daily_milk", "Daily milk #15": "daily_milk", "MD #151": "daily_milk",
    "MD #152": "daily_milk", "MD #154": "daily_milk", "MD #156": "daily_milk", "MD #157": "daily_milk",
    "MD #158": "daily_milk", "Daily milk #16": "daily_milk", "MD #162": "daily_milk",
    "MD #163": "daily_milk", "MD #164": "daily_milk", "MD #165": "daily_milk", "MD #166": "daily_milk",
    "MD #167": "daily_milk", "MD #168": "daily_milk", "Daily milk #18": "daily_milk",
    "Daily milk #19": "daily_milk", "Daily milk #2": "daily_milk", "Daily milk #21": "daily_milk",
    "Daily milk #23": "daily_milk", "Daily milk #26": "daily_milk", "Daily milk #27": "daily_milk",
    "Daily milk #28": "daily_milk", "Daily milk #3": "daily_milk", "Daily milk #32": "daily_milk",
    "Daily milk #33": "daily_milk", "Daily milk #34": "daily_milk", "Daily milk #35": "daily_milk",
    "Daily Milk #36": "daily_milk", "Daily milk#40": "daily_milk", "Daily milk #41": "daily_milk",
    "Daily Milk #47": "daily_milk", "Daily milk #49": "daily_milk", "Daily Milk #53": "daily_milk",
    "Daily milk #54": "daily_milk", "Daily Milk #55": "daily_milk", "Daily milk #57": "daily_milk",
    "Daily milk #58": "daily_milk", "Daily milk #60": "daily_milk", "Daily milk #62": "daily_milk",
    "Daily milk #63": "daily_milk", "Daily milk #64": "daily_milk", "Daily milk #66": "daily_milk",
    "Daily milk #67": "daily_milk", "Daily milk #69": "daily_milk", "Daily milk #7": "daily_milk",
    "Daily milk #72": "daily_milk", "Daily milk #73": "daily_milk", "Daily milk #74": "daily_milk",
    "Daily milk #76": "daily_milk", "Daily milk #77": "daily_milk", "Daily milk #78": "daily_milk",
    "Daily mik #8": "daily_milk", "Daily milk #80": "daily_milk", "Daily milk #81": "daily_milk",
    "Daily milk #82": "daily_milk", "Daily milk #86": "daily_milk", "Daily milk #87": "daily_milk",
    "Daily Milk": "daily_milk",

    "Quality #85": "quality", "Quality #1": "quality", "Quality #10": "quality",
    "MQ #102": "quality", "MQ #103": "quality", "MQ #104": "quality", "MQ #105": "quality",
    "MQ #106": "quality", "MQ #109": "quality", "Quality #11": "quality", "MQ #111": "quality",
    "MQ #112": "quality", "MQ #113": "quality", "MQ #115": "quality", "MQ #118": "quality",
    "Quality #12": "quality", "MQ #122": "quality", "MQ #123": "quality", "MQ #125": "quality",
    "MQ #128": "quality", "MQ #129": "quality", "MQ #130": "quality", "MQ #134": "quality",
    "MQ #137": "quality", "MQ #139": "quality", "Quality #14": "quality", "MQ #141": "quality",
    "MQ #143": "quality", "MQ #144": "quality", "MQ #145": "quality", "MQ #146": "quality",
    "MQ #147": "quality", "MQ #148": "quality", "Quality #15": "quality", "MQ #151": "quality",
    "MQ #152": "quality", "MQ #154": "quality", "MQ #156": "quality", "MQ #157": "quality",
    "MQ #158": "quality", "Quality #16": "quality", "MQ #162": "quality", "MQ #163": "quality",
    "MQ #164": "quality", "MQ #165": "quality", "MQ #166": "quality", "MQ #167": "quality",
    "MQ #168": "quality", "Quality #18": "quality", "Quality #19": "quality", "Quality #2": "quality",
    "Quality #21": "quality", "Quality #23": "quality", "Quality #26": "quality",
    "Quality #27": "quality", "Quality #28": "quality", "Quality #3": "quality",
    "Quality #32": "quality", "Quality #33": "quality", "Quality #34": "quality",
    "Quality #35": "quality", "Quality #36": "quality", "Quality #40": "quality",
    "Quality #41": "quality", "Quality #47": "quality", "Quality #49": "quality",
    "Quality #53": "quality", "Quality #54": "quality", "Quality #55": "quality",
    "Quality #57": "quality", "Quality #58": "quality", "Quality #60": "quality",
    "Quality #62": "quality", "Quality #63": "quality", "Quality #64": "quality",
    "Quality #66": "quality", "Quality #67": "quality", "Quality #69": "quality",
    "Quality #7": "quality", "Quality #72": "quality", "Quality #73": "quality",
    "Quality #74": "quality", "Quality #76": "quality", "Quality #77": "quality",
    "Quality #78": "quality", "Quality #8": "quality", "Quality #80": "quality",
    "Quality #81": "quality", "Quality #82": "quality", "Quality #86": "quality",
    "Quality #87": "quality", "Quality": "quality", "Quality#35": "quality",

    "Visits #85": "visits", "Visits #1": "visits", "Visits #10": "visits",
    "MV #102": "visits", "MV #103": "visits", "MV #104": "visits", "MV #105": "visits",
    "MV #106": "visits", "MV #109": "visits", "Visits #11": "visits", "MV #111": "visits",
    "MV #112": "visits", "MV #113": "visits", "MV #115": "visits", "MV #118": "visits",
    "Visits #12": "visits", "MV #122": "visits", "MV #123": "visits", "MV #125": "visits",
    "MV #128": "visits", "MV #129": "visits", "MV #130": "visits", "MV #134": "visits",
    "MV #137": "visits", "MV #139": "visits", "Visits #14": "visits", "MV #141": "visits",
    "MV #143": "visits", "MV #144": "visits", "MV #145": "visits", "MV #146": "visits",
    "MV #147": "visits", "MV #148": "visits", "Visits #15": "visits", "MV #151": "visits",
    "MV #152": "visits", "MV #154": "visits", "MV #156": "visits", "MV #157": "visits",
    "MV #158": "visits", "Visits #16": "visits", "MV #162": "visits", "MV #163": "visits",
    "MV #164": "visits", "MV #165": "visits", "MV #166": "visits", "MV #167": "visits",
    "MV #168": "visits", "Visits #18": "visits", "Visits #19": "visits", "Visits #2": "visits",
    "Visits #21": "visits", "Visits #23": "visits", "Visits #26": "visits",
    "Visits #27": "visits", "Visits #28": "visits", "Visits #3": "visits",
    "Visits #32": "visits", "Visits #33": "visits", "Visits #34": "visits",
    "Visits #35": "visits", "Visits #36": "visits", "Visits #40": "visits",
    "Visits #41": "visits", "Visits #47": "visits", "Visits #49": "visits",
    "Visits #53": "visits", "Visits #54": "visits", "Visits #55": "visits",
    "Visits #57": "visits", "Visits #58": "visits", "Visits #60": "visits",
    "Visits #62": "visits", "Visits #63": "visits", "Visits #64": "visits",
    "Visits #66": "visits", "Visits #67": "visits", "Visits #69": "visits",
    "Visits #7": "visits", "Visits #72": "visits", "Visits #73": "visits",
    "Visits #74": "visits", "Visits #76": "visits", "Visits #77": "visits",
    "Visits #78": "visits", "Visits #8": "visits", "Visits #80": "visits",
    "Visits #81": "visits", "Visits #82": "visits", "Visits #86": "visits",
    "Visits #87": "visits", "Visit": "visits", "MV": "visits",

    "Lactation #85": "lactation", "Lactation #1": "lactation", "Lactation #10": "lactation",
    "LAC #102": "lactation", "LAC #103": "lactation", "LAC #104": "lactation",
    "LAC #105": "lactation", "LAC #106": "lactation", "LAC #109": "lactation",
    "Lactation #11": "lactation", "LAC #111": "lactation", "LAC #112": "lactation",
    "LAC #113": "lactation", "LAC #115": "lactation", "LAC #118": "lactation",
    "Lactation #12": "lactation", "LAC #122": "lactation", "LAC #123": "lactation",
    "LAC #125": "lactation", "LAC #128": "lactation", "LAC #129": "lactation",
    "LAC #130": "lactation", "LAC #134": "lactation", "LAC #137": "lactation",
    "LAC #139": "lactation", "Lactation #14": "lactation", "LAC #141": "lactation",
    "LAC #143": "lactation", "LAC #144": "lactation", "LAC #145": "lactation",
    "LAC #146": "lactation", "LAC #147": "lactation", "LAC #148": "lactation",
    "Lactation #15": "lactation", "LAC #151": "lactation", "LAC #152": "lactation",
    "LAC #154": "lactation", "LAC #156": "lactation", "LAC #157": "lactation",
    "LAC #158": "lactation", "Lactation #16": "lactation", "LAC #162": "lactation",
    "LAC #163": "lactation", "LAC #164": "lactation", "LAC #165": "lactation",
    "LAC #166": "lactation", "LAC #167": "lactation", "LAC #168": "lactation",
    "Lactation #18": "lactation", "Lactation #19": "lactation", "Lactation #2": "lactation",
    "Lactation #21": "lactation", "Lactation #23": "lactation", "Lactation #26": "lactation",
    "Lactation #27": "lactation", "Lactation #28": "lactation", "Lactation #3": "lactation",
    "Lactation #32": "lactation", "Lactation #33": "lactation", "Lactation #34": "lactation",
    "Lactation #35": "lactation", "Lactation #36": "lactation", "Lactation #40": "lactation",
    "Lactation #41": "lactation", "Lactation #47": "lactation", "Lactation #49": "lactation",
    "Lactation #53": "lactation", "Lactation #54": "lactation", "Lactation #55": "lactation",
    "Lactation #57": "lactation", "Lactation #58": "lactation", "Lactation #60": "lactation",
    "Lactation #62": "lactation", "Lactation #63": "lactation", "Lactation #64": "lactation",
    "Lactation #66": "lactation", "Lactation #67": "lactation", "Lactation #69": "lactation",
    "Lactation #7": "lactation", "Lactation #72": "lactation", "Lactation #73": "lactation",
    "Lactation #74": "lactation", "Lactation #76": "lactation", "Lactation #77": "lactation",
    "Lactation #78": "lactation", "Lactation #8": "lactation", "Lactation #80": "lactation",
    "Lactation #81": "lactation", "Lactation #82": "lactation", "Lactation #86": "lactation",
    "Lactation #87": "lactation", "Lactation": "lactation", "LAC": "lactation",

    "Events #85": "events", "Events #1": "events", "Events #10": "events",
    "EVENTS #102": "events", "EVENTS #103": "events", "EVENTS #104": "events",
    "EVENTS #105": "events", "EVENTS #106": "events", "EVENTS #109": "events",
    "Events #11": "events", "EVENTS #111": "events", "EVENTS #112": "events",
    "EVENTS #113": "events", "EVENTS #115": "events", "EVENTS #118": "events",
    "Events #12": "events", "EVENTS #122": "events", "EVENTS #123": "events",
    "EVENTS #125": "events", "EVENTS #128": "events", "EVENTS #129": "events",
    "EVENTS #130": "events", "EVENTS #134": "events", "EVENTS #137": "events",
    "EVENTS #139": "events", "Events #14": "events", "EVENTS #141": "events",
    "EVENTS #143": "events", "EVENTS #144": "events", "EVENTS #145": "events",
    "EVENTS #146": "events", "EVENTS #147": "events", "EVENTS #148": "events",
    "Events #15": "events", "EVENTS #151": "events", "EVENTS #152": "events",
    "EVENTS #154": "events", "EVENTS #156": "events", "EVENTS #157": "events",
    "EVENTS #158": "events", "Events #16": "events", "EVENTS #162": "events",
    "EVENTS #163": "events", "EVENTS #164": "events", "EVENTS #165": "events",
    "EVENTS #166": "events", "EVENTS #167": "events", "EVENTS #168": "events",
    "Events #18": "events", "Events #19": "events", "Events #2": "events",
    "Events #21": "events", "Events #23": "events", "Events #26": "events",
    "Events #27": "events", "Events #28": "events", "Events #3": "events",
    "Events #32": "events", "Events #33": "events", "Events #34": "events",
    "Events #35": "events", "Events #36": "events", "Events #40": "events",
    "Events #41": "events", "Events #47": "events", "Events #49": "events",
    "Events #53": "events", "Events #54": "events", "Events #55": "events",
    "Events #57": "events", "Events #58": "events", "Events #60": "events",
    "Events #62": "events", "Events #63": "events", "Events #64": "events",
    "Events #66": "events", "Events #67": "events", "Events #69": "events",
    "Events #7": "events", "Events #72": "events", "Events #73": "events",
    "Events #74": "events", "Events #76": "events", "Events #77": "events",
    "Events #78": "events", "Events #8": "events", "Events #80": "events",
    "Events #81": "events", "Events #82": "events", "Events #86": "events",
    "Events #87": "events", "Event": "events", "Events": "events",

    "Feed #85": "feed", "Feed #1": "feed", "Feed #10": "feed",
    "FD #102": "feed", "FD #103": "feed", "FD #104": "feed", "FD #105": "feed",
    "FD #106": "feed", "FD #109": "feed", "Feed #11": "feed", "FD #111": "feed",
    "FD #112": "feed", "FD #113": "feed", "FD #115": "feed", "FD #118": "feed",
    "Feed #12": "feed", "FD #122": "feed", "FD #123": "feed", "FD #125": "feed",
    "FD #128": "feed", "FD #129": "feed", "FD #130": "feed", "FD #134": "feed",
    "FD #137": "feed", "FD #139": "feed", "Feed #14": "feed", "FD #141": "feed",
    "FD #143": "feed", "FD #144": "feed", "FD #145": "feed", "FD #146": "feed",
    "FD #147": "feed", "FD #148": "feed", "Feed #15": "feed", "FD #151": "feed",
    "FD #152": "feed", "FD #154": "feed", "FD #156": "feed", "FD #157": "feed",
    "FD #158": "feed", "Feed #16": "feed", "FD #162": "feed", "FD #163": "feed",
    "FD #164": "feed", "FD #165": "feed", "FD #166": "feed", "FD #167": "feed",
    "FD #168": "feed", "Feed #18": "feed", "Feed #19": "feed", "Feed #2": "feed",
    "Feed #21": "feed", "Feed #23": "feed", "Feed #26": "feed", "Feed #27": "feed",
    "Feed #28": "feed", "Feed #3": "feed", "Feed #32": "feed", "Feed #33": "feed",
    "Feed #34": "feed", "Feed #35": "feed", "Feed #36": "feed", "Feed #40": "feed",
    "Feed #41": "feed", "Feed #47": "feed", "Feed #49": "feed", "Feed #53": "feed",
    "Feed #54": "feed", "Feed #55": "feed", "Feed #57": "feed", "Feed #58": "feed",
    "Feed #60": "feed", "Feed #62": "feed", "Feed #63": "feed", "Feed #64": "feed",
    "Feed #66": "feed", "Feed #67": "feed", "Feed #69": "feed", "Feed #7": "feed",
    "Feed #72": "feed", "Feed #73": "feed", "Feed #74": "feed", "Feed #76": "feed",
    "Feed #77": "feed", "Feed #78": "feed", "Feed #8": "feed", "Feed #80": "feed",
    "Feed #81": "feed", "Feed #82": "feed", "Feed #86": "feed", "Feed #87": "feed",
    "Feed": "feed", "FD": "feed", "MD": "daily_milk", "MQ": "quality",
    "Feed#14": "feed", "Feed#23": "feed"
}

# Column translation dictionaries

# Standardized column names and their variants. One dictionary per
# worksheet: keys are the raw (OCR-corrupted) header texts found in the
# workbooks, values are the standardized names. Matching in
# rename_columns() is case-insensitive. To add a new variant, add a
# "Raw Header Text": "Standard Name" entry to the relevant worksheet's
# dictionary.

COLUMN_TRANSLATION_MAPS = {
    "daily_milk": {
        "Date": "Date",
        "Date \u00bb": "Date",
        "Date \u25bc": "Date",
        "Lactation Days": "Lactation Days",
        "Location Days": "Lactation Days",
        "Total Programmed": "Programmed Rest Feed",
        "Programmed": "Programmed Rest Feed",
        "Rest Feed": "Rest Feed",
        "Rest Peed": "Rest Feed",
        "Rest Reed": "Rest Feed",
        "Day Production": "Day Production",
        "Day production Dev": "Day Production Dev",
        "production Dev": "Day Production Dev",
        "ISK": "ISK",
        "I5K": "ISK",
        "lSK": "ISK",
        "1SK": "ISK",
        "Milkings": "Milkings",
        "Refusals": "Refusals",
        "Failures": "Failures",
        "Milkings Avg": "Milkings Avg",
        "Refusals Avg": "Refusals Avg",
        "Failures Avg": "Failures Avg",
        "Fat indication": "Fat Indication",
        "Fai Indication": "Fat Indication",
        "Protein indication": "Protein Indication",
        "Lactose indication": "Lactose Indication",
    },
    "quality": {
        "Date Time": "Date Time",
        "Date time": "Date Time",
        "Address": "Address",
        "Addre55": "Address",
        "Failure": "Failure",
        "Milk Yield": "Milk Yield",
        "Milk field": "Milk Yield",
        "Milk Yield Expected": "Milk Yield Expected",
        "Temperature milk": "Milk Temperature",
        "Temperature": "Milk Temperature",
        "Temperature Milk": "Milk Temperature",
        "Temperature of milk": "Milk Temperature",
        "Temp milk": "Milk Temperature",
        "Date Time v": "Date Time",
    },
    "visits": {
        "Date Time": "Date Time",
        "Date": "Date Time",
        "Device Name": "Device Name",
        "Milk Yield": "Milk Yield",
        "Milk Yield Expect": "Milk Yield Expected",
        "Milk Yield Expecl": "Milk Yield Expected",
        "Milk Yield Expert": "Milk Yield Expected",
        "Mdk Yield Expect": "Milk Yield Expected",
        "Visit Result": "Visit Result",
        "Milk Speed": "Milk Speed",
        "Milk Spend": "Milk Speed",
        "Milk Speed max": "Milk Speed Max",
        "Milk speed max,": "Milk Speed Max",
        "Intervi": "Milking Interval (min)",
        "Interv": "Milking Interval (min)",
        "Interv;": "Milking Interval (min)",
        "Interva": "Milking Interval (min)",
        "Interval": "Milking Interval (min)",
        "Intervr": "Milking Interval (min)",
        "Inters": "Milking Interval (min)",
        "lnterv": "Milking Interval (min)",
        "interv:": "Milking Interval (min)",
        "Box Time": "Box Time (min)",
        "Bex Time": "Box Time (min)",
        "Treat Time": "Treat Time (min)",
        "Trearn Time": "Treat Time (min)",
        "Treata Time": "Treat Time (min)",
        "Treatm Time": "Treat Time (min)",
        "Treatn Time": "Treat Time (min)",
        "Treatnr Time": "Treat Time (min)",
        "Treatrr Time": "Treat Time (min)",
        "Troarn Time": "Treat Time (min)",
        "Tempe milk": "Milk Temperature",
        "Tempt milk": "Milk Temperature",
        "Temp milk": "Milk Temperature",
        "Milk Destin": "Milk Destination",
        "Milk Dest": "Milk Destination",
        "Milk Destina": "Milk Destination",
        "Milk Destination": "Milk Destination",
        "Routing Direction": "Routing Direction",
        "Bottle Num": "Bottle Num",
        "Botti Num": "Bottle Num",
        "Botti* Num": "Bottle Num",
        "Botti-Num": "Bottle Num",
        "Bottl Num": "Bottle Num",
        "Bottl-Num": "Bottle Num",
        "Bottl. Num": "Bottle Num",
        "Bottb Num": "Bottle Num",
        "Botth Num": "Bottle Num",
        "Bottu Num": "Bottle Num",
        "Bottli Num": "Bottle Num",
        "Bottli Num!": "Bottle Num",
        "Bonk Num": "Bottle Num",
        "Bottle Numb": "Bottle Num",
        "Bottle Number": "Bottle Num",
    },
    "lactation": {
        "Lactation": "Lactation Number",
        "Lactation No.": "Lactation Number",
        "Lactation No": "Lactation Number",
        "Calving Date": "Calving Date",
        "Caking Date": "Calving Date",
        "Lactation Production": "Lactation Production",
        "Lactation prodcution": "Lactation Production",
        "Lactation-Production": "Lactation Production",
        "Predicted Production": "Predicted Production 305d",
        "Predicted Production (305 days)": "Predicted Production 305d",
        "Predicted Production 305 days)": "Predicted Production 305d",
        "Predicted production (305 days)": "Predicted Production 305d",
        "Milk Separated": "Milk Separated",
        "Milk seperated": "Milk Separated",
        "Lactation Days": "Lactation Days",
        "Day Production": "Day Production",
        "Milkings": "Milkings",
        "Milk Speed": "Milk Speed",
        "Refusals": "Refusals",
        "Failures": "Failures",
        "Amount Total": "Amount Total",
        "Rest Feed Total": "Rest Feed Total",
        "Fat %": "Fat %",
        "Protein %": "Protein %",
        "Lactose %": "Lactose %",
        "Fat indication": "Fat Indication",
        "Protein indication": "Protein Indication",
        "Lactose indication": "Lactose Indication",
        "Fat indication %": "Fat Indication",
        "Protein indication Percentage": "Protein Indication",
        "Protein indication %": "Protein Indication",
        "Protein indication percentage": "Protein Indication",
        "Protein indications": "Protein Indication",
        "Lactose ind cation": "Lactose Indication",
        "Lactose indication %": "Lactose Indication",
    },
    "feed": {
        "Date": "Date",
        "Lactation Days": "Lactation Days",
        "Day Production": "Day Production",
        "Day production": "Day Production",
        "Total Programmed": "Programmed Rest Feed",
        "Iota! Programmed": "Programmed Rest Feed",
        "Rest Feed": "Rest Feed",
        "Rest feed": "Rest Feed",
    },
}

# SUMMARY FILE
# report() prints for the console AND keeps the line so the same text is
# saved to data/analysis_summary.txt at the end of the run.

SUMMARY_LINES = []


def report(text=""):
    """Print a line and keep it for the analysis summary file."""
    print(text)
    SUMMARY_LINES.append(text)


# SHARED CLEANING HELPER FUNCTIONS

# Header normalization

OCR_JUNK = " .'*’»▼;!,"

# Common OCR digit-for-letter substitutions, used only for header row
# matching ('Addre55' -> 'address', 'Dev1ce' -> 'device')
OCR_DIGIT_FOR_LETTER = str.maketrans({
    "5": "s", "0": "o", "1": "i", "8": "b", "4": "a", "3": "e", "7": "t",
})


def normalize_header_text(text):
    """
    Normalize worksheet column headers.

    - Remove excess whitespace
    - Remove OCR artifacts
    - Standardize header text
    """
    text = " ".join(str(text).split())
    return text.strip(OCR_JUNK)


def find_header_row(raw_df, keyword):
    """
    Locate the actual header row in worksheets with inconsistent layouts.
    """
    keyword = keyword.lower()
    for row_number in range(min(10, len(raw_df))):
        row_text = " ".join(str(x) for x in raw_df.iloc[row_number].tolist())
        if keyword in row_text.lower():
            return row_number
    # Second pass with OCR-tolerant matching, because the header keyword
    # itself can be corrupted ('Addre55' for 'Address' in cow #63)
    for row_number in range(min(10, len(raw_df))):
        row_text = " ".join(str(x) for x in raw_df.iloc[row_number].tolist())
        if keyword in row_text.lower().translate(OCR_DIGIT_FOR_LETTER):
            report(f"  NOTE: header keyword '{keyword}' found via OCR-tolerant "
                   f"match at row {row_number} (corrupted header text)")
            return row_number
    # Default to the first row if the keyword is never found
    return 0


def drop_duplicate_columns(clean_df):
    """Remove duplicate-named columns while retaining the first occurrence."""
    return clean_df.loc[:, ~clean_df.columns.duplicated()].copy()


def rename_columns(clean_df, rename_map):
    """Rename inconsistent column variants to standardized names."""
    # Matching is case-insensitive ('Milk yield Expect' vs 'Milk Yield Expect')
    lookup = {key.lower(): value for key, value in rename_map.items()}
    clean_df.columns = [lookup.get(str(c).lower(), c) for c in clean_df.columns]
    return clean_df


def remove_summary_rows(clean_df):
    """
    Identify and remove spreadsheet summary rows.

    Indicators: Total, Sum, Average, AVG, and OCR-corrupted variants.
    """
    is_summary = clean_df.astype(str).apply(
        lambda col: col.str.lower().str.strip().isin(['total', 'sum', 'average', 'avg', 'avc', 'suu', 'avg sum', '5um'])).any(axis=1)
    return clean_df[~is_summary]

# Date and time cleaning


def looks_like_valid_date(text):
    """Determine whether text resembles a valid date."""
    parts = text.split("/")
    if len(parts) != 3:
        return False
    month, day, year = parts
    if not (month.isdigit() and day.isdigit() and year.isdigit()):
        return False
    if len(year) != 4:
        return False
    return 2014 <= int(year) <= 2026 and 1 <= int(month) <= 12 and 1 <= int(day) <= 31


def looks_like_valid_time(text):
    """Determine whether text resembles a valid time."""
    parts = text.split(":")
    if len(parts) != 2:
        return False
    hour, minute = parts
    if not (hour.isdigit() and minute.isdigit()):
        return False
    return 1 <= int(hour) <= 12 and 0 <= int(minute) <= 59


def clean_datetime_text(value):
    """
    Repair OCR-corrupted date/time strings.

    - Remove invalid characters
    - Repair AM/PM markers
    - Restore missing colons
    - Merge split digits
    - Repair split years
    - Separate combined date/time values
    """
    if not isinstance(value, str):
        return value
    # Remove invalid characters (keeps only characters a datetime can
    # contain; drops OCR junk like the 'T' in '9:2 T AM')
    allowed_characters = "0123456789/: -apAPmM"
    text = ""
    for character in value.strip():
        if character in allowed_characters:
            text = text + character
    # Spaces around slashes are never real ('10/ 4/2024' -> '10/4/2024')
    text = text.replace("/ ", "/").replace(" /", "/")
    # Work word by word (split on spaces)
    words = text.split()
    # Repair AM/PM markers ('All' -> 'AM', 'P1' -> 'PM', 'A4' -> 'AM',
    # 'A-' -> 'AM')
    fixed_words = []
    for word in words:
        upper_word = word.upper()
        if upper_word.startswith("A") and len(upper_word) <= 3:
            fixed_words.append("AM")
        elif upper_word.startswith("P") and len(upper_word) <= 3:
            fixed_words.append("PM")
        else:
            fixed_words.append(word)
    words = fixed_words
    # Restore missing colons in the time ('334 PM' -> '3:34 PM',
    # '938 AM' -> '9:38 AM'): the last two digits are the minutes
    for index in range(len(words) - 1):
        word = words[index]
        if word.isdigit() and len(word) in (3, 4) and words[index + 1] in ("AM", "PM"):
            words[index] = word[:-2] + ":" + word[-2:]
    # Merge split digits ('2 024' -> '2024', '9:2 5' -> '9:25')
    merged_words = []
    for word in words:
        if word.isdigit() and merged_words and merged_words[-1][-1:].isdigit():
            merged_words[-1] = merged_words[-1] + word
        else:
            merged_words.append(word)
    words = merged_words
    # Repair split years ('9/25/202-4' -> '9/25/2024'); dates never
    # contain a real dash
    words = [word.replace("-", "") if "/" in word else word for word in words]
    # Separate combined date/time values ('10/15/202410:09' ->
    # '10/15/2024' + '10:09'): the hour is 1 or 2 digits before the
    # colon, so try both and keep the split where the date and the time
    # are both valid
    separated_words = []
    for word in words:
        if "/" in word and ":" in word:
            colon_index = word.index(":")
            best_split = None
            for hour_length in (1, 2):
                date_part = word[:colon_index - hour_length]
                time_part = word[colon_index - hour_length:]
                if looks_like_valid_date(date_part) and looks_like_valid_time(time_part):
                    best_split = (date_part, time_part)
                    break
            if best_split:
                separated_words.extend(best_split)
            else:
                separated_words.append(word)
        else:
            separated_words.append(word)
    words = separated_words
    # Put the words back together
    text = " ".join(words)
    # Values with no digits left are OCR fragments ('A', 'M') -> missing
    if not any(character.isdigit() for character in text):
        return None
    return text

# Duration conversion


def duration_to_minutes(value, spec):
    """
    Convert duration strings into minutes.

    Specifications:
    - hours: h:mm
    - minutes: mm:ss
    """
    # Empty cells stay empty
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    # Already a number, nothing to convert
    if isinstance(value, (int, float)):
        return float(value)
    # Fix OCR mistakes in the duration text ('U:U8' -> '0:08')
    text = str(value).strip()
    text = text.replace("U", "0").replace("u", "0").replace("O", "0").replace("?", "0")
    # Split on the colon
    parts = text.split(":")
    try:
        if len(parts) == 2:
            first = int(parts[0])
            second = int(parts[1])
        elif len(parts) == 3:
            first = int(parts[0])
            second = int(parts[1])
        else:
            return np.nan
    except ValueError:
        # Unreadable OCR garbage ('i2', 'S7', '03.13 03') counts as missing
        return np.nan
    # Convert to minutes depending on what the column means
    if spec == "hours":
        return first * 60 + second
    else:
        return first + second / 60

# Data type conversion


def convert_data_types(clean_df, date_columns, text_columns,
                       duration_spec=None):
    """
    Convert worksheet columns into appropriate data types.

    - Repair and convert dates
    - Preserve specified text columns
    - Coerce numeric columns
    - Convert duration columns into minutes
    - Preserve missing values as NaN
    """
    # Repair and convert dates
    for column in date_columns:
        if column in clean_df.columns:
            clean_df[column] = clean_df[column].map(clean_datetime_text)
            # pandas prints a warning here because the column mixes
            # date-only and date+time strings, so it cannot guess one
            # format for the whole column. That is expected for this data;
            # the per-element parsing it falls back to is exactly what we
            # want, so the warning is silenced.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                warnings.simplefilter("ignore", FutureWarning)
                clean_df[column] = pd.to_datetime(clean_df[column], errors="coerce")
    # Coerce every column to numbers EXCEPT dates, known text columns, and
    # duration columns (most number columns are stored as text by Excel,
    # so they must be coerced by name, not by pandas dtype)
    for column in clean_df.columns:
        if column in date_columns or column in text_columns:
            continue
        if duration_spec is not None and column in duration_spec:
            continue
        clean_df[column] = pd.to_numeric(clean_df[column], errors="coerce")
    # Convert duration columns from 'h:mm'/'mm:ss' text to minutes
    if duration_spec is not None:
        for column, spec in duration_spec.items():
            if column in clean_df.columns:
                clean_df[column] = clean_df[column].apply(lambda v: duration_to_minutes(v, spec))
    return clean_df

# METADATA EXTRACTION


def cow_id_from_file_name(file_name_string):
    """
    Extract cow ID from the robotic milking workbook filename.

    - Extract numeric characters
    - Return integer ID when available
    - Return 'Unknown ID/Special Case' otherwise
    """
    filename = Path(file_name_string).name
    # Collect number characters
    number_characters = ""
    for character in filename:
        if character.isdigit():
            number_characters = number_characters + character
    if number_characters:
        return int(number_characters)
    else:
        return "Unknown ID/Special Case"

# EXCEL WORKSHEET IDENTIFICATION


def fingerprint_tabs(file_name):
    """
    Identify and standardize inconsistent Excel worksheet names.

    Standard worksheet categories:
    - daily_milk, quality, visits, lactation, events, feed
    """
    # Load workbook using openpyxl
    data = openpyxl.load_workbook(file_name, read_only=True)
    tab_names = data.sheetnames
    # Normalize worksheet names and match against TAB_TRANSLATION_MAP
    normalized_map = {
        key.strip().lower(): value
        for key, value in TAB_TRANSLATION_MAP.items()
    }
    fingerprints = {}
    for tab_name in tab_names:
        tab_rename = tab_name.strip().lower()
        if tab_rename in normalized_map:
            fingerprints[tab_name] = normalized_map[tab_rename]
        # Flag unknown worksheets
        else:
            fingerprints[tab_name] = f"unknown_{tab_name}"
    return fingerprints

# RAW DATA EXTRACTION / INGESTION


def parse_robotic_milking_data(file_name):
    """
    Parse an individual robotic milking workbook.

    1. Extract Cow_ID.
    2. Identify worksheet names.
    3. Read each worksheet independently.
    4. Preserve original worksheet layout (header=None).
    5. Attach Cow_ID to each DataFrame.
    6. Record parsing errors.
    7. Return structured data.
    """
    # Extract Cow_ID
    cow_ID = cow_id_from_file_name(file_name)
    # Identify worksheet names
    tab_fingerprints = fingerprint_tabs(file_name)
    tables = {}
    errors = {}
    # Read each worksheet independently
    for sheet_name, standard_name in tab_fingerprints.items():
        try:
            # header=None: header rows are handled manually in the clean
            # functions, because Quality/Visits have TWO header rows and
            # some Lactation tabs have blank rows above the header
            raw_df = pd.read_excel(file_name, sheet_name=sheet_name, header=None)
            raw_df["cow_ID"] = cow_ID
            tables[standard_name] = raw_df
        except Exception as e:
            # Record parsing errors
            errors[standard_name] = f"failed on tab '{sheet_name}': {str(e)}"
    return cow_ID, tables, errors


def load_robotic_milking_data():
    """
    Read all robotic milking Excel workbooks.

    Return structure:

    {
        filename: {
            "daily_milk": DataFrame,
            "quality": DataFrame,
            "visits": DataFrame,
            "lactation": DataFrame,
            "events": DataFrame,
            "feed": DataFrame
        }
    }
    """
    robot_milking_data = {}
    # Discover workbooks using sorted file paths
    workbook_paths = sorted(RAW_DATA_DIR.glob("Robot Farm #*.xlsx"))
    report(f"Discovered {len(workbook_paths)} workbooks in {RAW_DATA_DIR}")
    # Parse each workbook
    for file_path in workbook_paths:
        cow_id, tables, errors = parse_robotic_milking_data(str(file_path))
        if errors:
            report(f"  WARNING: {file_path.name}: parse issues {errors}")
        robot_milking_data[file_path.name] = tables
    total_tabs = sum(len(sheets) for sheets in robot_milking_data.values())
    report(f"Loaded {len(robot_milking_data)} workbooks, {total_tabs} worksheets total")
    return robot_milking_data

# WORKSHEET-SPECIFIC CLEANING FUNCTIONS

# IMPORTANT:
# Keep these functions independent.
# Each worksheet has different header structures and data types.

# Daily milk


def clean_daily_milk(df):
    """
    Clean daily milk production data.

    - Locate Lactation Days header
    - Normalize headers
    - Remove unnamed columns
    - Restore Cow_ID
    - Rename OCR-corrupted columns
    - Remove duplicate columns
    - Remove summary rows
    - Convert dates and numeric values
    """
    clean_df = df.copy()
    # Set the cow ID aside; it gets re-attached at the end
    cow_id_value = clean_df["cow_ID"].iloc[0]
    clean_df = clean_df.drop(columns=["cow_ID"])
    # The header is the first row, data starts on the second row
    header_row = find_header_row(clean_df, "Lactation Days")
    raw_headers = clean_df.iloc[header_row].tolist()
    clean_df = clean_df.iloc[header_row + 1:].copy()
    clean_df.columns = [normalize_header_text(x) for x in raw_headers]
    # Remove unnamed columns (extra cells with no header name)
    clean_df = clean_df.drop(columns=["nan"], errors="ignore")
    clean_df["cow_ID"] = cow_id_value
    # Rename OCR-corrupted columns (raw header text -> standardized names)
    clean_df = rename_columns(clean_df, COLUMN_TRANSLATION_MAPS["daily_milk"])
    # Remove duplicate columns
    clean_df = drop_duplicate_columns(clean_df)
    # Remove summary rows
    clean_df = remove_summary_rows(clean_df)
    # Convert dates and numeric values
    # NAs are left as NA here: they are filled by KNN imputation later
    clean_df = convert_data_types(clean_df,
                                  date_columns=["Date"],
                                  text_columns=["cow_ID", "source_file"])
    return clean_df

# Quality


def clean_quality(df):
    """
    Clean milk quality data.

    - Reconstruct two-row headers
    - Combine quarter labels (LF/RF/LR/RR)
    - Standardize conductivity and color code columns
    - Rename inconsistent headers
    - Remove duplicate columns and summary rows
    - Convert dates and numeric values
    """
    clean_df = df.copy()
    # Set the cow ID aside; it gets re-attached at the end
    cow_id_value = clean_df["cow_ID"].iloc[0]
    clean_df = clean_df.drop(columns=["cow_ID"])
    # Quality has TWO header rows: row 1 has quarter labels (LF/RF/LR/RR)
    # sitting above the Conductivity/Color Code columns in row 2
    name_row_number = find_header_row(clean_df, "Address")
    # The names row is the one containing 'Address'; the quarter labels
    # (LF/RF/LR/RR) sit one row above it
    quarter_row = clean_df.iloc[name_row_number - 1].tolist()
    name_row = clean_df.iloc[name_row_number].tolist()
    clean_df = clean_df.iloc[name_row_number + 2:].copy()
    # Combine the two header rows into one name per column
    # ('Conductivity' + 'LF' -> 'Conductivity LF'); a quarter label carries
    # forward to the next columns until a new label appears
    new_columns = []
    current_quarter = ""
    for quarter_label, name in zip(quarter_row, name_row):
        name = normalize_header_text(name)
        if str(quarter_label).strip().upper() in ("LF", "RF", "LR", "RR"):
            current_quarter = str(quarter_label).strip().upper()
        if name.lower() in ("conductivity", "color code") and current_quarter:
            new_columns.append(f"{name} {current_quarter}")
        else:
            new_columns.append(name)
    clean_df.columns = new_columns
    # Remove unnamed columns (extra cells with no header name)
    clean_df = clean_df.drop(columns=["nan"], errors="ignore")
    clean_df["cow_ID"] = cow_id_value
    # Rename inconsistent headers
    clean_df = rename_columns(clean_df, COLUMN_TRANSLATION_MAPS["quality"])
    # Remove duplicate columns
    clean_df = drop_duplicate_columns(clean_df)
    # Remove summary rows
    clean_df = remove_summary_rows(clean_df)
    # Convert dates and numeric values
    # Address and Failure are text, everything else numeric
    clean_df = convert_data_types(clean_df,
                                  date_columns=["Date Time"],
                                  text_columns=["Address", "Failure", "cow_ID", "source_file"])
    return clean_df

# Visits


def clean_visits(df):
    """
    Clean individual milking visit data.

    - Reconstruct two-row headers
    - Combine group and quarter labels
    - Standardize milk yield, speed, and interval columns
    - Convert duration measurements into minutes
    - Convert dates and numeric values
    """
    clean_df = df.copy()
    # Set the cow ID aside; it gets re-attached at the end
    cow_id_value = clean_df["cow_ID"].iloc[0]
    clean_df = clean_df.drop(columns=["cow_ID"])
    # Visits has TWO header rows: row 1 has group names ('Dead Milk Time',
    # 'Milk Time', 'Attachments'), row 2 has quarter labels (LF/RF/LR/RR)
    # under the groups and the real column names everywhere else
    name_row_number = find_header_row(clean_df, "Device Name")
    # The names row is the one containing 'Device Name'; the group names
    # ('Dead Milk Time', 'Milk Time', 'Attachments') sit one row above it
    group_row = clean_df.iloc[name_row_number - 1].tolist()
    name_row = clean_df.iloc[name_row_number].tolist()
    clean_df = clean_df.iloc[name_row_number + 2:].copy()
    # Combine the two header rows into one name per column
    # ('Dead Milk Time' + 'LF' -> 'Dead Milk Time LF')
    new_columns = []
    current_group = ""
    for group_label, name in zip(group_row, name_row):
        name = normalize_header_text(name)
        if str(group_label) not in ("nan", ""):
            current_group = normalize_header_text(group_label)
        if str(name).strip().upper() in ("LF", "RF", "LR", "RR") and current_group:
            new_columns.append(f"{current_group} {str(name).strip().upper()}")
        else:
            new_columns.append(name)
    clean_df.columns = new_columns
    # Remove unnamed columns (extra cells with no header name)
    clean_df = clean_df.drop(columns=["nan"], errors="ignore")
    clean_df["cow_ID"] = cow_id_value
    # Rename inconsistent headers
    clean_df = rename_columns(clean_df, COLUMN_TRANSLATION_MAPS["visits"])
    # Remove duplicate columns
    clean_df = drop_duplicate_columns(clean_df)
    # Remove summary rows
    clean_df = remove_summary_rows(clean_df)
    # Convert dates and numeric values
    # Durations are 'h:mm'/'mm:ss' text: interval is hours:minutes,
    # the rest are minutes:seconds, all converted to minutes
    duration_spec = {
        "Milking Interval (min)": "hours",
        "Box Time (min)": "minutes",
        "Treat Time (min)": "minutes",
        "Dead Milk Time LF": "minutes", "Dead Milk Time RF": "minutes",
        "Dead Milk Time LR": "minutes", "Dead Milk Time RR": "minutes",
        "Milk Time LF": "minutes", "Milk Time RF": "minutes",
        "Milk Time LR": "minutes", "Milk Time RR": "minutes",
    }
    clean_df = convert_data_types(clean_df,
                                  date_columns=["Date Time"],
                                  text_columns=["Device Name", "Visit Result",
                                                "Milk Destination", "Routing Direction", "cow_ID", "source_file"],
                                  duration_spec=duration_spec)
    return clean_df

# Lactation


def clean_lactation(df):
    """
    Clean lactation history data.

    - Locate Calving header
    - Standardize lactation columns
    - Rename inconsistent headers
    - Remove duplicate columns and summary rows
    - Convert dates and numeric values
    """
    clean_df = df.copy()
    # Set the cow ID aside; it gets re-attached at the end
    cow_id_value = clean_df["cow_ID"].iloc[0]
    clean_df = clean_df.drop(columns=["cow_ID"])
    # The header row moves around between files (some tabs have blank
    # rows first), so find it by looking for 'Calving'
    header_row = find_header_row(clean_df, "Calving")
    raw_headers = clean_df.iloc[header_row].tolist()
    clean_df = clean_df.iloc[header_row + 1:].copy()
    clean_df.columns = [normalize_header_text(x) for x in raw_headers]
    # Remove unnamed columns (extra cells with no header name)
    clean_df = clean_df.drop(columns=["nan"], errors="ignore")
    clean_df["cow_ID"] = cow_id_value
    # Rename inconsistent headers
    clean_df = rename_columns(clean_df, COLUMN_TRANSLATION_MAPS["lactation"])
    # Remove duplicate columns
    clean_df = drop_duplicate_columns(clean_df)
    # Remove summary rows
    clean_df = remove_summary_rows(clean_df)
    # Convert dates and numeric values
    clean_df = convert_data_types(clean_df,
                                  date_columns=["Calving Date"],
                                  text_columns=["cow_ID", "source_file"])
    return clean_df

# Events


def clean_events(df):
    """
    Clean event history data.

    - Assign column names by position
    - Preserve event descriptions as text
    - Retain lactation section rows for later evaluation
    - Restore Cow_ID
    """
    clean_df = df.copy()
    # Set the cow ID aside; it gets re-attached at the end
    cow_id_value = clean_df["cow_ID"].iloc[0]
    clean_df = clean_df.drop(columns=["cow_ID"])
    # Events has NO header row: the first row is a 'Lactation N' section
    # row, so column names are assigned manually by position
    event_columns = ["Date", "Event Description", "Detail 1", "Detail 2",
                     "Detail 3", "Detail 4", "Detail 5", "Detail 6"]
    # Some cow files have extra detail columns; name them Detail 7, 8, ...
    while len(event_columns) < clean_df.shape[1]:
        event_columns.append(f"Detail {len(event_columns) - 1}")
    clean_df.columns = event_columns[:clean_df.shape[1]]
    clean_df["cow_ID"] = cow_id_value
    # Preserve event descriptions as raw text, including the 'Lactation N'
    # section rows (filter them out later by checking if Date is a real
    # datetime). Everything stays text: no type conversion here.
    return clean_df

# Feed


def clean_feed(df):
    """
    Clean feed-related data.

    - Locate Lactation Days header
    - Normalize headers
    - Rename inconsistent columns
    - Remove duplicate columns and summary rows
    - Convert dates and numeric values
    """
    clean_df = df.copy()
    # Set the cow ID aside; it gets re-attached at the end
    cow_id_value = clean_df["cow_ID"].iloc[0]
    clean_df = clean_df.drop(columns=["cow_ID"])
    # The header is the first row, data starts on the second row
    header_row = find_header_row(clean_df, "Lactation Days")
    raw_headers = clean_df.iloc[header_row].tolist()
    clean_df = clean_df.iloc[header_row + 1:].copy()
    clean_df.columns = [normalize_header_text(x) for x in raw_headers]
    # Remove unnamed columns (extra cells with no header name)
    clean_df = clean_df.drop(columns=["nan"], errors="ignore")
    clean_df["cow_ID"] = cow_id_value
    # Rename inconsistent columns
    clean_df = rename_columns(clean_df, COLUMN_TRANSLATION_MAPS["feed"])
    # Remove duplicate columns
    clean_df = drop_duplicate_columns(clean_df)
    # Remove summary rows
    clean_df = remove_summary_rows(clean_df)
    # Convert dates and numeric values
    clean_df = convert_data_types(clean_df,
                                  date_columns=["Date"],
                                  text_columns=["cow_ID", "source_file"])
    return clean_df

# CLEANING ORCHESTRATION

# Cleaning function registry

CLEAN_FUNCTIONS = {
    "daily_milk": clean_daily_milk,
    "quality": clean_quality,
    "visits": clean_visits,
    "lactation": clean_lactation,
    "events": clean_events,
    "feed": clean_feed,
}


def clean_all_robot_data(robot_milking_data):
    """
    Apply the appropriate cleaning function to each worksheet.

    1. Iterate through workbooks.
    2. Iterate through worksheets.
    3. Skip empty worksheets.
    4. Identify the corresponding cleaning function.
    5. Execute the cleaning function.
    6. Record cleaning errors.
    7. Store successful results.
    """
    robot_milking_data_clean = {}
    failed_cleaning = []
    unknown_tabs = []
    # Iterate through workbooks
    for file_name, sheets in robot_milking_data.items():
        cleaned_sheets = {}
        # Iterate through worksheets
        for sheet_name, raw_df in sheets.items():
            # Skip empty worksheets (a few cows have them)
            if raw_df.empty or raw_df.shape[1] < 2:
                report(f"  EMPTY TAB SKIPPED: {file_name} {sheet_name}")
                continue
            # Identify the corresponding cleaning function
            if sheet_name in CLEAN_FUNCTIONS:
                try:
                    # Execute the cleaning function
                    cleaned_df = CLEAN_FUNCTIONS[sheet_name](raw_df)
                    # Preserve the source filename on every row
                    cleaned_df["source_file"] = file_name
                    # Store successful results
                    cleaned_sheets[sheet_name] = cleaned_df
                except Exception as e:
                    # Record cleaning errors
                    report(f"  CLEAN FAILED: {file_name} {sheet_name}: {e}")
                    failed_cleaning.append(f"{file_name} {sheet_name}: {e}")
            else:
                report(f"  UNKNOWN TAB SKIPPED: {file_name} {sheet_name}")
                unknown_tabs.append(f"{file_name} {sheet_name}")
        robot_milking_data_clean[file_name] = cleaned_sheets
    report(f"Cleaning finished: {len(failed_cleaning)} failures, "
           f"{len(unknown_tabs)} unknown tabs")
    return robot_milking_data_clean, failed_cleaning, unknown_tabs


def combine_cleaned_tables(robot_milking_data_clean):
    """
    Combine every cow's cleaned worksheet into one table per tab type.
    """
    combined_tables = {}
    for tab in CLEAN_FUNCTIONS:
        # Combine every cow's table of this type into one frame
        frames = [sheets[tab] for sheets in robot_milking_data_clean.values() if tab in sheets]
        if not frames:
            continue
        combined_tables[tab] = pd.concat(frames, ignore_index=True)
        report(f"Combined {tab}: {combined_tables[tab].shape[0]} rows x "
               f"{combined_tables[tab].shape[1]} columns from {len(frames)} cows")
    return combined_tables

# ROW CLEANUP: DUPLICATES AND CORRUPTED DATES


def drop_duplicate_cow_days(combined_tables):
    """
    Remove duplicate (cow, date) rows, keeping the first occurrence.

    These are re-sent sensor records for the same cow-day. Only applied
    to tables with a date column; the removed count is reported.
    """
    if not DROP_DUPLICATE_ROWS:
        return combined_tables
    key_columns = {
        "daily_milk": ["cow_ID", "Date"],
        "quality": ["cow_ID", "Date Time"],
        "visits": ["cow_ID", "Date Time"],
        "lactation": ["cow_ID", "Calving Date", "Lactation Number"],
        "feed": ["cow_ID", "Date"],
    }
    for tab, keys in key_columns.items():
        if tab not in combined_tables:
            continue
        combined = combined_tables[tab]
        if not all(column in combined.columns for column in keys):
            continue
        rows_before = combined.shape[0]
        # Only rows with a REAL date can be called duplicates of another
        # row: pandas treats two missing dates as equal, so deduping over
        # NaT rows would wrongly collapse distinct unparseable records.
        date_keys = [column for column in keys if column in ("Date", "Date Time", "Calving Date")]
        if date_keys:
            has_date = combined[date_keys].notna().all(axis=1)
        else:
            has_date = pd.Series(True, index=combined.index)
        dated_keep = combined.loc[combined.index[has_date]] \
            .drop_duplicates(keys, keep="first").index
        # Undated rows are all kept (they cannot be checked for duplication)
        keep_indices = sorted(list(dated_keep) + list(combined.index[~has_date]))
        combined_tables[tab] = combined.loc[keep_indices].reset_index(drop=True)
        rows_removed = rows_before - combined_tables[tab].shape[0]
        report(f"{tab}: removed {rows_removed} duplicate cow-day rows "
               f"(kept first occurrence) -> shape {combined_tables[tab].shape}")
    return combined_tables


def drop_corrupted_date_rows(combined_tables):
    """
    Remove rows whose date falls outside the plausible year window.

    These are OCR century errors (2034 for 2024, 1900 for 2019): the
    measurement values may be real, but the day cannot be placed in
    time, so the row is unusable for a time-ordered analysis. Only a
    handful of rows are affected; every removal is reported below.
    """
    for (tab, date_column), (low_year, high_year) in DATE_WINDOWS.items():
        if tab not in combined_tables:
            continue
        combined = combined_tables[tab]
        if date_column not in combined.columns:
            continue
        years = combined[date_column].dt.year
        # NaT dates are NOT removed here: they can be a blank cell or
        # unreadable OCR, and there is no way to tell those apart. They
        # are reported in the analysis instead.
        corrupted = years.notna() & ((years < low_year) | (years > high_year))
        if corrupted.any():
            affected_cows = sorted(str(c) for c in combined.loc[corrupted, "cow_ID"].unique())
            report(f"{tab}: removing {int(corrupted.sum())} row(s) with impossible "
                   f"dates outside [{low_year}, {high_year}] "
                   f"(cows: {affected_cows})")
            combined_tables[tab] = combined[~corrupted].reset_index(drop=True)
            report(f"{tab}: shape after removal {combined_tables[tab].shape}")
    return combined_tables

# COLUMN CLEANUP: MISSINGNESS CUTOFF


def drop_sparse_columns(combined_tables):
    """
    Remove columns missing MISSINGNESS_CUTOFF or more of their values.

    Columns this sparse cannot be imputed reliably. The dropped and kept
    columns are reported per table. Identifier, date, and text columns
    are never dropped by this rule.
    """
    for tab, combined in combined_tables.items():
        # Never drop IDs, dates, or the text columns left as-is
        protected = ["cow_ID", "source_file", "Date", "Date Time", "Calving Date",
                     "Address", "Failure", "Device Name", "Visit Result",
                     "Milk Destination", "Routing Direction", "Event Description"]
        missing_fraction = combined.isna().mean()
        sparse_columns = [
            column for column in combined.columns
            if column not in protected and missing_fraction[column] >= MISSINGNESS_CUTOFF
        ]
        kept_columns = [column for column in combined.columns if column not in sparse_columns]
        report(f"{tab}: dropping {len(sparse_columns)} column(s) missing >= "
               f"{MISSINGNESS_CUTOFF:.0%} of values")
        if sparse_columns:
            report(f"  dropped: {sparse_columns}")
        report(f"  kept: {len(kept_columns)} of {combined.shape[1]} columns")
        combined_tables[tab] = combined[kept_columns].copy()
        report(f"{tab}: shape after column cutoff {combined_tables[tab].shape}")
    return combined_tables

# KNN IMPUTATION (PER-COW)


def impute_table_per_cow(table, tab_name, imputation_log):
    """
    Fill missing numeric values with KNN imputation, one cow at a time.

    Each cow is imputed from her OWN other days, because every cow has
    her own baseline and frequent value ranges. The KNN distance uses
    ALL numeric columns at once (multivariate): a missing value is
    filled from this cow's most similar days, where similarity is
    measured across every measurement, not just the filled column.
    Before KNN, each numeric column is standardized within the cow
    (z-score, using nan-aware mean and std) so large-unit columns do
    not dominate the distance; values are unscaled afterwards. Every
    imputed cell is appended to imputation_log. Text and date columns
    are left untouched.
    """
    report(f"KNN imputation for {tab_name} (per cow, multivariate, K={KNN_NEIGHBORS})")
    # Numeric columns only: identifiers, dates, and text stay as-is
    text_and_date_columns = ["cow_ID", "source_file", "Date", "Date Time",
                             "Calving Date", "Address", "Failure", "Device Name",
                             "Visit Result", "Milk Destination", "Routing Direction"]
    numeric_columns = [
        column for column in table.columns
        if column not in text_and_date_columns and pd.api.types.is_numeric_dtype(table[column])
    ]
    report(f"  imputing {len(numeric_columns)} numeric column(s): {numeric_columns}")
    missing_before = table[numeric_columns].isna().sum()
    imputed_table = table.copy()
    for cow_id in sorted(table["cow_ID"].unique()):
        cow_mask = imputed_table["cow_ID"] == cow_id
        cow_table = imputed_table.loc[cow_mask, numeric_columns]
        cow_values = cow_table.to_numpy(dtype=float)
        # Column-by-column preprocessing, then one multivariate KNN fit:
        # - a column with NO real values for this cow cannot be imputed
        #   from her own days and stays missing (reported)
        # - a constant column (zero variance) cannot be z-scored; its
        #   missing cells are filled with the constant directly
        imputable_columns = []
        constant_fills = {}
        for column_index, column in enumerate(numeric_columns):
            column_values = cow_values[:, column_index]
            if np.isnan(column_values).all():
                report(f"  cow {cow_id}: column '{column}' has no values at all "
                       f"for this cow; left as missing")
                continue
            column_std = np.nanstd(column_values)
            if column_std == 0:
                constant_fills[column_index] = np.nanmean(column_values)
            else:
                imputable_columns.append(column_index)
        # Standardize the imputable columns into one matrix so the KNN
        # distance uses every measurement, then impute in one fit
        if imputable_columns:
            matrix = cow_values[:, imputable_columns].copy()
            column_means = np.nanmean(matrix, axis=0)
            column_stds = np.nanstd(matrix, axis=0)
            matrix = (matrix - column_means) / column_stds
            imputer = KNNImputer(n_neighbors=KNN_NEIGHBORS)
            imputed_matrix = imputer.fit_transform(matrix)
            restored = imputed_matrix * column_stds + column_means
            cow_values[:, imputable_columns] = restored
        for column_index, fill_value in constant_fills.items():
            column_values = cow_values[:, column_index]
            column_values[np.isnan(column_values)] = fill_value
        # Write the imputed cow back into the table and log every cell
        cow_row_indices = imputed_table.index[cow_mask]
        for column_index, column in enumerate(numeric_columns):
            original_values = table.loc[cow_mask, column].to_numpy(dtype=float)
            new_values = cow_values[:, column_index]
            newly_imputed = np.isnan(original_values) & ~np.isnan(new_values)
            if not newly_imputed.any():
                continue
            # Write ONLY the imputed cells (real measurements are never
            # touched), rounded to 4 decimals to remove float artifacts
            # from the unscaling arithmetic (e.g. -1.4e-17 instead of 0)
            date_column = "Date" if "Date" in imputed_table.columns else \
                "Date Time" if "Date Time" in imputed_table.columns else None
            for row_position in np.where(newly_imputed)[0]:
                row = cow_row_indices[row_position]
                imputed_table.loc[row, column] = round(float(new_values[row_position]), 4)
            for row_position in np.where(newly_imputed)[0]:
                row = cow_row_indices[row_position]
                imputation_log.append({
                    "table": tab_name,
                    "cow_ID": str(cow_id),
                    "date": str(imputed_table.loc[row, date_column]) if date_column else "",
                    "column": column,
                    "imputed_value": round(float(new_values[row_position]), 4),
                    "method": f"KNN (K={KNN_NEIGHBORS}, per-cow, multivariate, z-scored)"
                        if column_index in imputable_columns
                        else "constant (cow-level mean, zero variance)",
                })
    missing_after = imputed_table[numeric_columns].isna().sum()
    report("  imputed cell counts per column (per-cow stage):")
    for column in numeric_columns:
        filled = int(missing_before[column] - missing_after[column])
        still_missing = int(missing_after[column])
        if still_missing > 0:
            report(f"    {column}: {filled} imputed per cow, "
                   f"{still_missing} left for the herd stage")
        else:
            report(f"    {column}: {filled} imputed, column complete")
    report(f"{tab_name}: shape after imputation {imputed_table.shape}")
    return imputed_table, imputation_log


def impute_remaining_from_herd(table, tab_name, imputation_log):
    """
    Second imputation stage: fill what the per-cow stage could not.

    The per-cow stage leaves a column missing entirely for cows that
    never record it (there is nothing in her own days to learn from).
    For those cells, KNN now uses the HERD: every numeric column is
    first standardized within each cow (deviation from her own
    baseline), so days are compared by how unusual they are, not by
    which cow they belong to. A missing value is then filled with the
    mean of the K most similar cow-days of other cows. This conditions
    the fill on the day's other measurements, which is stronger than a
    herd median (the same value for every missing cell).

    For the similarity search, a missing predictor is treated as "no
    deviation from the cow's baseline" (z = 0), an explicit assumption
    so that a day with a blank sensor reading still counts as a normal
    day rather than being excluded.
    """
    report(f"Herd-level KNN for {tab_name} (filling what per-cow could not)")
    text_and_date_columns = ["cow_ID", "source_file", "Date", "Date Time",
                             "Calving Date", "Address", "Failure", "Device Name",
                             "Visit Result", "Milk Destination", "Routing Direction"]
    numeric_columns = [column for column in table.columns
                       if column not in text_and_date_columns
                       and pd.api.types.is_numeric_dtype(table[column])]

    # Standardize every numeric column within each cow:
    # z = (value - cow mean) / cow std, computed from her observed days only
    standardized_table = table[["cow_ID"] + numeric_columns].copy()
    for column in numeric_columns:
        for cow_id in sorted(table["cow_ID"].unique()):
            cow_mask = standardized_table["cow_ID"] == cow_id
            values = standardized_table.loc[cow_mask, column].to_numpy(dtype=float)
            observed = ~np.isnan(values)
            if not observed.any():
                continue  # nothing to standardize; stays missing
            mean = values[observed].mean()
            std = values[observed].std()
            if std == 0:
                values[observed] = 0.0  # every observed value is exactly at the baseline
            else:
                values[observed] = (values[observed] - mean) / std
            standardized_table.loc[cow_mask, column] = values

    for target_column in numeric_columns:
        original_values = table[target_column].to_numpy(dtype=float)
        missing_mask = np.isnan(original_values)
        if not missing_mask.any():
            continue

        # Donor days: all cow-days where the target column was observed.
        # Similarity is computed on the cow-standardized predictors, with
        # a missing predictor set to z = 0 (at the cow's baseline).
        predictor_columns = [column for column in numeric_columns if column != target_column]
        donor_mask = ~missing_mask
        donor_matrix = standardized_table.loc[donor_mask, predictor_columns].to_numpy(dtype=float)
        donor_matrix[np.isnan(donor_matrix)] = 0.0
        donor_targets = original_values[donor_mask]

        # Days to fill: the still-missing cells, same treatment of predictors
        fill_matrix = standardized_table.loc[missing_mask, predictor_columns].to_numpy(dtype=float)
        fill_matrix[np.isnan(fill_matrix)] = 0.0

        neighbor_search = NearestNeighbors(n_neighbors=KNN_NEIGHBORS).fit(donor_matrix)
        _, neighbor_indices = neighbor_search.kneighbors(fill_matrix)
        new_values = donor_targets[neighbor_indices].mean(axis=1)

        # Write ONLY the imputed cells (real measurements are never
        # touched), rounded to 4 decimals to remove float artifacts
        date_column = "Date" if "Date" in table.columns else \
            "Date Time" if "Date Time" in table.columns else None
        missing_positions = np.where(missing_mask)[0]
        for fill_index, row_position in enumerate(missing_positions):
            row = table.index[row_position]
            table.loc[row, target_column] = round(float(new_values[fill_index]), 4)
            imputation_log.append({
                "table": tab_name,
                "cow_ID": str(table.loc[row, "cow_ID"]),
                "date": str(table.loc[row, date_column]) if date_column else "",
                "column": target_column,
                "imputed_value": round(float(new_values[fill_index]), 4),
                "method": f"herd KNN (K={KNN_NEIGHBORS}, similarity from cow-standardized days)",
            })
        report(f"    {target_column}: {int(missing_mask.sum())} imputed from herd")

    still_missing = table[numeric_columns].isna().sum()
    for column in numeric_columns:
        if still_missing[column] > 0:
            report(f"    {column}: {int(still_missing[column])} still missing "
                   f"(no comparable donor days)")
    return table, imputation_log


def drop_unfillable_columns(table, tab_name):
    """
    Final completeness guarantee: after the per-cow and herd KNN
    stages, a numeric column that STILL has missing cells is not a
    feature we can track for every cow, so it is removed from the
    table entirely. For this dataset this removes nothing (both stages
    fill every numeric cell); it is a guardrail so the guarantee
    'imputed tables have complete numeric columns' can never silently
    break in a future run.
    """
    text_and_date_columns = ["cow_ID", "source_file", "Date", "Date Time",
                             "Calving Date", "Address", "Failure", "Device Name",
                             "Visit Result", "Milk Destination", "Routing Direction"]
    numeric_columns = [column for column in table.columns
                       if column not in text_and_date_columns
                       and pd.api.types.is_numeric_dtype(table[column])]
    unfillable = [column for column in numeric_columns if table[column].isna().any()]
    for column in unfillable:
        report(f"  {tab_name}: DROPPING column '{column}' -- still missing after "
               f"per-cow and herd KNN (not a trackable feature)")
        table = table.drop(columns=[column])
    if not unfillable:
        report(f"  {tab_name}: all numeric columns complete after imputation")
    return table


def set_impossible_values_missing(tables, imputation_log):
    """
    Set physically impossible values to missing so imputation replaces
    them. Every threshold is several times beyond the highest value a
    cow could plausibly produce, so nothing that could be real is
    removed. Unusual-but-possible values (high conductivity from
    mastitis, >1000 Lactation Days, high refusal counts from a
    persistent cow) are REAL and are exactly the signal this project
    is hunting, so they stay. Most caught values are decimal-shift
    corruption (e.g. 17.33 entered as 1733) and often contradict the
    row's own other columns (e.g. Day Production 1307 with a normal
    Day Production Dev of -10.8).
    """
    report("CORRUPTED VALUES SET MISSING")
    # (column, rule text, predicate on the value)
    impossible_value_rules = [
        ("Milk Temperature", ">150 F (milk is ~body temperature, ~100 F)",
         lambda v: v > 150),
        ("Day Production", ">200 lbs (a dairy cow maxes out around 150)",
         lambda v: v > 200),
        ("Day Production Dev", "beyond +/-200 lbs (implies impossible production)",
         lambda v: v.abs() > 200),
        ("Programmed Rest Feed", ">100 (herd 99.9th percentile is 20)",
         lambda v: v > 100),
        ("Rest Feed", ">25 (herd 99.9th percentile is 8)",
         lambda v: v > 25),
        ("ISK", ">600 (observed herd maximum is 445)",
         lambda v: v > 600),
        ("Milkings Avg", ">15 (a robot allows at most ~6 milkings/day)",
         lambda v: v > 15),
        ("Fat Indication", ">15% (milk fat never exceeds ~9%)",
         lambda v: v > 15),
        ("Protein Indication", ">15% (milk protein never exceeds ~6%)",
         lambda v: v > 15),
        ("Milk Yield", ">200 lbs in one milking (impossible)",
         lambda v: v > 200),
        ("Milk Yield Expected", ">200 lbs expected in one milking (impossible)",
         lambda v: v > 200),
    ]
    for tab_name in ["daily_milk", "quality"]:
        table = tables.get(tab_name)
        if table is None:
            continue
        date_column = "Date" if "Date" in table.columns else \
            "Date Time" if "Date Time" in table.columns else None
        for column, rule_text, is_impossible in impossible_value_rules:
            if column not in table.columns:
                continue
            values = table[column].to_numpy(dtype=float)
            impossible = ~np.isnan(values) & is_impossible(pd.Series(values)).to_numpy()
            for row_position in np.where(impossible)[0]:
                row = table.index[row_position]
                imputation_log.append({
                    "table": tab_name,
                    "cow_ID": str(table.loc[row, "cow_ID"]),
                    "date": str(table.loc[row, date_column]) if date_column else "",
                    "column": column,
                    "imputed_value": "",
                    "method": f"corrupted value set missing ({values[row_position]}: {rule_text})",
                })
                table.loc[row, column] = np.nan
            if impossible.any():
                report(f"  {tab_name}: {int(impossible.sum())} impossible {column} "
                       f"value(s) set missing (logged, then imputed)")
        tables[tab_name] = table
    return tables, imputation_log


# HPAI RESULTS / LABEL PROCESSING


def load_HPAI_results():
    """Load original HPAI ELISA classification results."""
    hpai_results = pd.read_excel(DATA_DIR / "Robot_dairy_results.xlsx")
    report(f"Loaded HPAI results: {hpai_results.shape[0]} rows x {hpai_results.shape[1]} columns")
    return hpai_results


def clean_HPAI_results(df):
    """
    Clean HPAI results.

    - Normalize column headers
    - Rename ELISA columns
    - Normalize classification text
    - Convert ELISA interpretation into binary labels
    - Preserve Cow_ID as a string
    - Convert ELISA_SN to numeric
    - Add Test_Date
    """
    cleaned = df.copy()
    # Fix column names and remove invisible spaces
    cleaned = cleaned.rename(columns=lambda x: " ".join(str(x).split()))
    # Rename columns
    cleaned = cleaned.rename(columns={
        "Influenza A ELISA SN (S/N) Serum": "ELISA_SN",
        "Influenza A ELISA Interpretation Serum 05/22/25": "ELISA_Interpretation",
    })
    # Normalize the original classification column before mapping
    cleaned["ELISA_Interpretation"] = (
        cleaned["ELISA_Interpretation"]
        .astype("string")
        .str.strip()
        .str.title()
    )
    # Binary classification:
    # Negative = 0
    # Suspect and Positive = 1
    cleaned["ELISA_Classification"] = (
        cleaned["ELISA_Interpretation"].map({
            "Negative": 0,
            "Suspect": 1,
            "Positive": 1,
        }).astype("Int64")
    )
    # Make and keep cow IDs as strings
    cleaned["Cow_ID"] = cleaned["Cow_ID"].astype(str).str.strip()
    # Keep ELISA SN as numeric
    cleaned["ELISA_SN"] = pd.to_numeric(cleaned["ELISA_SN"], errors="coerce")
    # Keep the date as a separate column for now
    cleaned["Test_Date"] = pd.to_datetime("2025-05-22")
    report(f"HPAI results cleaned: shape {cleaned.shape}")
    return cleaned

# BASIC ANALYSIS


def analyze_table(tab_name, combined):
    """
    Basic analysis for one cleaned table: shape, columns, missingness,
    and summary statistics for the key numeric columns.
    """
    report(f"--- {tab_name}: {combined.shape[0]} rows x {combined.shape[1]} columns ---")
    report(f"  columns: {list(combined.columns)}")
    # Missingness after all cleaning and imputation, split by column
    # type; numeric columns of the imputed tables are guaranteed
    # complete, text columns are left as-is by design
    numeric_columns = [column for column in combined.columns
                       if pd.api.types.is_numeric_dtype(combined[column])]
    text_columns = [column for column in combined.columns if column not in numeric_columns]
    numeric_missing = int(combined[numeric_columns].isna().sum().sum())
    text_missing = int(combined[text_columns].isna().sum().sum())
    report(f"  missing cells in NUMERIC columns: {numeric_missing} "
           f"({'COMPLETE' if numeric_missing == 0 else 'INCOMPLETE -- see imputation notes'})")
    report(f"  missing cells in TEXT columns (left as-is by design): {text_missing}")
    # Key numeric columns: summary statistics
    key_columns = {
        "daily_milk": ["Day Production", "Lactation Days", "Milkings", "Refusals", "Failures"],
        "quality": ["Milk Yield", "Milk Temperature", "Conductivity LF", "Conductivity RF",
                    "Conductivity LR", "Conductivity RR"],
        "visits": ["Milk Yield", "Milk Speed", "Milking Interval (min)"],
        "lactation": ["Lactation Number", "Lactation Production"],
        "feed": ["Day Production", "Rest Feed"],
        "events": [],
    }
    numeric_key_columns = [
        column for column in key_columns.get(tab_name, [])
        if column in combined.columns and pd.api.types.is_numeric_dtype(combined[column])
    ]
    if numeric_key_columns:
        stats = combined[numeric_key_columns].describe().round(2)
        report("  summary statistics (count / mean / std / min / 25% / 50% / 75% / max):")
        for column in numeric_key_columns:
            s = combined[column]
            report(f"    {column}: count={int(s.count())}, mean={round(float(s.mean()), 2)}, "
                   f"std={round(float(s.std()), 2)}, min={round(float(s.min()), 2)}, "
                   f"25%={round(float(s.quantile(0.25)), 2)}, 50%={round(float(s.quantile(0.5)), 2)}, "
                   f"75%={round(float(s.quantile(0.75)), 2)}, max={round(float(s.max()), 2)}")
    # Per-cow coverage for the daily table
    if tab_name == "daily_milk":
        days_per_cow = combined.groupby("cow_ID")["Date"].count()
        report(f"  days recorded per cow: min={days_per_cow.min()}, "
               f"median={int(days_per_cow.median())}, max={days_per_cow.max()}")


def analyze_elisa_labels(hpai_clean):
    """Basic analysis of the ELISA label table."""
    report("--- HPAI ELISA labels ---")
    counts = hpai_clean["ELISA_Interpretation"].value_counts()
    report(f"  interpretation counts: {dict(counts)}")
    report(f"  binary labels: Negative (0) = {int((hpai_clean['ELISA_Classification'] == 0).sum())}, "
           f"Suspect/Positive (1) = {int((hpai_clean['ELISA_Classification'] == 1).sum())}")
    report(f"  test date: {hpai_clean['Test_Date'].iloc[0].date()}")
    # Cow ID coverage: sensor cows with and without a label
    return counts

# OUTPUT


def save_outputs(combined_tables, hpai_clean, imputation_log,
                 failed_cleaning, unknown_tabs):
    """
    Save all outputs under data/clean/:

    - one CSV per worksheet type (daily_milk and quality imputed)
    - hpai_labels.csv
    - imputation_log.csv (one row per imputed cell)
    - analysis_summary.txt (everything report() printed)
    """
    CLEAN_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for tab, combined in combined_tables.items():
        output_path = CLEAN_DATA_DIR / f"{tab}.csv"
        combined.to_csv(output_path, index=False)
        report(f"Saved {tab}: {combined.shape[0]} rows -> {output_path}")
    # ELISA labels
    hpai_path = CLEAN_DATA_DIR / "hpai_labels.csv"
    hpai_clean.to_csv(hpai_path, index=False)
    report(f"Saved HPAI labels: {hpai_clean.shape[0]} rows -> {hpai_path}")
    # Imputation log (the scientist-facing record of every filled cell)
    imputation_log_path = CLEAN_DATA_DIR / "imputation_log.csv"
    imputation_log_table = pd.DataFrame(imputation_log)
    imputation_log_table.to_csv(imputation_log_path, index=False)
    report(f"Saved imputation log: {len(imputation_log)} imputed cells -> {imputation_log_path}")
    # Run metadata + summary text
    summary_path = CLEAN_DATA_DIR / "analysis_summary.txt"
    header_lines = [
        f"Analysis summary generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Cleaning failures: {len(failed_cleaning)}",
        f"Unknown worksheets: {len(unknown_tabs)}",
        "=" * 60,
    ]
    with open(summary_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(header_lines + SUMMARY_LINES) + "\n")
    report(f"Saved analysis summary -> {summary_path}")


# MAIN PIPELINE EXECUTION


def run():
    """
    Execute the complete cleaning and analysis pipeline.

    Order:
    1. Set deterministic settings and verify the input directory.
    2. Load and clean the HPAI ELISA results.
    3. Load and clean all robotic milking workbooks.
    4. Combine cleaned tables (one per worksheet type).
    5. Remove duplicate cow-days and corrupted-date rows.
    6. Remove columns missing >= MISSINGNESS_CUTOFF.
    7. KNN-impute daily_milk and quality (per cow), logging every cell.
    8. Run basic analysis.
    9. Save all outputs.
    """
    # 1. Deterministic settings
    pipeline_start = datetime.now()
    np.random.seed(RANDOM_SEED)
    report(f"Pipeline started (RANDOM_SEED={RANDOM_SEED})")
    if not RAW_DATA_DIR.exists():
        raise FileNotFoundError(f"Raw data directory not found: {RAW_DATA_DIR}")
    # 2. HPAI ELISA results
    hpai_raw = load_HPAI_results()
    hpai_clean = clean_HPAI_results(hpai_raw)
    analyze_elisa_labels(hpai_clean)
    # 3. Robotic milking workbooks
    robot_milking_data = load_robotic_milking_data()
    robot_milking_data_clean, failed_cleaning, unknown_tabs = clean_all_robot_data(robot_milking_data)
    # 4. Combine cleaned tables
    combined_tables = combine_cleaned_tables(robot_milking_data_clean)
    # 5. Row cleanup
    combined_tables = drop_duplicate_cow_days(combined_tables)
    combined_tables = drop_corrupted_date_rows(combined_tables)
    # 6. Column cleanup
    combined_tables = drop_sparse_columns(combined_tables)
    # 7. KNN imputation: stage 1 per cow (her own baselines), then
    #    stage 2 from the herd for columns her own days cannot fill.
    #    Impossible values are set missing first so they are imputed too.
    imputation_log = []
    combined_tables, imputation_log = set_impossible_values_missing(
        combined_tables, imputation_log)
    for tab_name in IMPUTE_TABLES:
        if tab_name in combined_tables:
            combined_tables[tab_name], imputation_log = impute_table_per_cow(
                combined_tables[tab_name], tab_name, imputation_log)
            combined_tables[tab_name], imputation_log = impute_remaining_from_herd(
                combined_tables[tab_name], tab_name, imputation_log)
            combined_tables[tab_name] = drop_unfillable_columns(
                combined_tables[tab_name], tab_name)
    # 8. Basic analysis
    report("")
    report("BASIC ANALYSIS")
    for tab_name, combined in combined_tables.items():
        analyze_table(tab_name, combined)
    # 9. Save outputs
    save_outputs(combined_tables, hpai_clean, imputation_log,
                 failed_cleaning, unknown_tabs)
    report(f"Pipeline finished in {datetime.now() - pipeline_start}")


# SCRIPT ENTRY POINT

if __name__ == "__main__":

    # Execute pipeline
    run()
