"""
Data cleaning for the early detection of HPAI in cows
using robotic milking project
Human audited/coded data cleaning code, each Excel sheet was read manually
Data is collected by the DRIVE Lab from videos into Excel spreadsheets
Contributions by Brendan Daly
"""

# Load in necessary libraries
from pathlib import Path
import openpyxl
import re
from datetime import datetime, date
import numpy as np
import pandas as pd
import os
from IPython.display import display
import matplotlib.pyplot as plt

"""HPAI Results/Labels"""
# Read in HPAI results/classification for data cleaning
data_directory = Path(__file__).parent / "data"
HPAI_results = pd.read_excel(data_directory / "Robot_dairy_results.xlsx")

# Function to analyze HPAI data
def analyze_HPAI_results(data_dict, label):
    print(f"{label}")
    print(data_dict.head(3))
    print(data_dict.tail(3))
    print("Number of rows:", len(data_dict))
    print("Unique values:", data_dict.nunique())
    HPAI_results_duplicates = data_dict[data_dict.duplicated()]
    print("Duplicates:", HPAI_results_duplicates)
    print("Number of duplicate rows:", data_dict.duplicated().sum())

# Analyze the data before cleaning it
analyze_HPAI_results(HPAI_results, "PRE-CLEAN")

# Clean HPAI Results
# Fix column names and remove invisible spaces
HPAI_results = HPAI_results.rename(columns=lambda x: " ".join(str(x).split()))

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

# Display the cleaned data
clean_HPAI_results = HPAI_results
display(clean_HPAI_results)

"""Robotic Milking Data"""
# A function to extract the digits from the file name to obtain the cow ID
def cow_id_from_file_name(file_name_string):
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

# A function to
# A function to parse Excel files that contain Excel tabs within them
def fingerprint_tabs(file_name):
    # Find what tab maps to what data type
    data = openpyxl.load_workbook(file_name, read_only=True)
    tab_names = data.sheetnames
    # Tab name translation map, list all names used for a tab type to convert to a common name
    # Long code is necessary to properly read in files with unpredictable naming structure
    translation_map = {
        "Daily milk #85": "daily_milk",
        "Daily Milk #1": "daily_milk",
        "Daily milk #10": "daily_milk",
        "MD #102": "daily_milk",
        "MD #103": "daily_milk",
        "MD #104": "daily_milk",
        "MD #105": "daily_milk",
        "MD #106": "daily_milk",
        "MD #109": "daily_milk",
        "Daily milk #11": "daily_milk",
        "MD #111": "daily_milk",
        "MD #112": "daily_milk",
        "MD #113": "daily_milk",
        "MD #115": "daily_milk",
        "MD #118": "daily_milk",
        "Daily milk #12": "daily_milk",
        "MD #122": "daily_milk",
        "MD #123": "daily_milk",
        "MD #125": "daily_milk",
        "MD #128": "daily_milk",
        "MD #129": "daily_milk",
        "MD #130": "daily_milk",
        "MD #134": "daily_milk",
        "MD #137": "daily_milk",
        "MD #139": "daily_milk",
        "Daily milk #14": "daily_milk",
        "MD #141": "daily_milk",
        "MD #143": "daily_milk",
        "MD #144": "daily_milk",
        "MD #145": "daily_milk",
        "MD #146": "daily_milk",
        "MD #147": "daily_milk",
        "MD #148": "daily_milk",
        "Daily milk #15": "daily_milk",
        "MD #151": "daily_milk",
        "MD #152": "daily_milk",
        "MD #154": "daily_milk",
        "MD #156": "daily_milk",
        "MD #157": "daily_milk",
        "MD #158": "daily_milk",

        "Quality #85": "quality",
        "Quality #1": "quality",
        "Quality #10": "quality",
        "MQ #102": "quality",
        "MQ #103": "quality",
        "MQ #104": "quality",
        "MQ #105": "quality",
        "MQ #106": "quality",
        "MQ #109": "quality",
        "Quality #11": "quality",
        "MQ #111": "quality",
        "MQ #112": "quality",
        "MQ #113": "quality",
        "MQ #115": "quality",
        "MQ #118": "quality",
        "Quality #12": "quality",
        "MQ #122": "quality",
        "MQ #123": "quality",
        "MQ #125": "quality",
        "MQ #128": "quality",
        "MQ #129": "quality",
        "MQ #130": "quality",
        "MQ #134": "quality",
        "MQ #137": "quality",
        "MQ #139": "quality",
        "Quality #14": "quality",
        "MQ #141": "quality",
        "MQ #143": "quality",
        "MQ #144": "quality",
        "MQ #145": "quality",
        "MQ #146": "quality",
        "MQ #147": "quality",
        "MQ #148": "quality",
        "Quality #15": "quality",
        "MQ #151": "quality",
        "MQ #152": "quality",
        "MQ #154": "quality",
        "MQ #156": "quality",
        "MQ #157": "quality",
        "MQ #158": "quality",
        "Quality #16": "quality",

        "Visits #85": "visits",
        "Visits #1": "visits",
        "Visits #10": "visits",
        "MV #102": "visits",
        "MV #103": "visits",
        "MV #104": "visits",
        "MV #105": "visits",
        "MV #106": "visits",
        "MV #109": "visits",
        "Visits #11": "visits",
        "MV #111": "visits",
        "MV #112": "visits",
        "MV #113": "visits",
        "MV #115": "visits",
        "MV #118": "visits",
        "Visits #12": "visits",
        "MV #122": "visits",
        "MV #123": "visits",
        "MV #125": "visits",
        "MV #128": "visits",
        "MV #129": "visits",
        "MV #130": "visits",
        "MV #134": "visits",
        "MV #137": "visits",
        "MV #139": "visits",
        "Visits #14": "visits",
        "MV #141": "visits",
        "MV #143": "visits",
        "MV #144": "visits",
        "MV #145": "visits",
        "MV #146": "visits",
        "MV #147": "visits",
        "MV #148": "visits",
        "Visits #15": "visits",
        "MV #151": "visits",
        "MV #152": "visits",
        "MV #154": "visits",
        "MV #156": "visits",
        "MV #157": "visits",
        "MV #158": "visits",
        "Visits #16": "visits",

        "Lactation #85": "lactation",
        "Lactation #1": "lactation",
        "Lactation #10": "lactation",
        "LAC #102": "lactation",
        "LAC #103": "lactation",
        "LAC #104": "lactation",
        "LAC #105": "lactation",
        "LAC #106": "lactation",
        "LAC #109": "lactation",
        "Lactation #11": "lactation",
        "LAC #111": "lactation",
        "LAC #112": "lactation",
        "LAC #113": "lactation",
        "LAC #115": "lactation",
        "LAC #118": "lactation",
        "Lactation #12": "lactation",
        "LAC #122": "lactation",
        "LAC #123": "lactation",
        "LAC #125": "lactation",
        "LAC #128": "lactation",
        "LAC #129": "lactation",
        "LAC #130": "lactation",
        "LAC #134": "lactation",
        "LAC #137": "lactation",
        "LAC #139": "lactation",
        "Lactation #14": "lactation",
        "LAC #141": "lactation",
        "LAC #143": "lactation",
        "LAC #144": "lactation",
        "LAC #145": "lactation",
        "LAC #146": "lactation",
        "LAC #147": "lactation",
        "LAC #148": "lactation",
        "Lactation #15": "lactation",
        "LAC #151": "lactation",
        "LAC #152": "lactation",
        "LAC #154": "lactation",
        "LAC #156": "lactation",
        "LAC #157": "lactation",
        "LAC #158": "lactation",
        "Lactation #16": "lactation",

        "Events #85": "events",
        "Events #1": "events",
        "Events #10": "events",
        "EVENTS #102": "events",
        "EVENTS #103": "events",
        "EVENTS #104": "events",
        "EVENTS #105": "events",
        "EVENTS #106": "events",
        "EVENTS #109": "events",
        "Events #11": "events",
        "EVENTS #111": "events",
        "EVENTS #112": "events",
        "EVENTS #113": "events",
        "EVENTS #115": "events",
        "EVENTS #118": "events",
        "Events #12": "events",
        "EVENTS #122": "events",
        "EVENTS #123": "events",
        "EVENTS #125": "events",
        "EVENTS #128": "events",
        "EVENTS #129": "events",
        "EVENTS #130": "events",
        "EVENTS #134": "events",
        "EVENTS #137": "events",
        "EVENTS #139": "events",
        "Events #14": "events",
        "EVENTS #141": "events",
        "EVENTS #143": "events",
        "EVENTS #144": "events",
        "EVENTS #145": "events",
        "EVENTS #146": "events",
        "EVENTS #147": "events",
        "EVENTS #148": "events",
        "Events #15": "events",
        "EVENTS #151": "events",
        "EVENTS #152": "events",
        "EVENTS #154": "events",
        "EVENTS #156": "events",
        "EVENTS #157": "events",
        "EVENTS #158": "events",
        "Events #16": "events",

        "Feed #85": "feed",
        "Feed #1": "feed",
        "Feed #10": "feed",
        "FD #102": "feed",
        "FD #103": "feed",
        "FD #104": "feed",
        "FD #105": "feed",
        "FD #106": "feed",
        "FD #109": "feed",
        "Feed #11": "feed",
        "FD #111": "feed",
        "FD #112": "feed",
        "FD #113": "feed",
        "FD #115": "feed",
        "FD #118": "feed",
        "Feed #12": "feed",
        "FD #122": "feed",
        "FD #123": "feed",
        "FD #125": "feed",
        "FD #128": "feed",
        "FD #129": "feed",
        "FD #130": "feed",
        "FD #134": "feed",
        "FD #137": "feed",
        "FD #139": "feed",
        "Feed #14": "feed",
        "FD #141": "feed",
        "FD #143": "feed",
        "FD #144": "feed",
        "FD #145": "feed",
        "FD #146": "feed",
        "FD #147": "feed",
        "FD #148": "feed",
        "Feed #15": "feed",
        "FD #151": "feed",
        "FD #152": "feed",
        "FD #154": "feed",
        "FD #156": "feed",
        "FD #157": "feed",
        "FD #158": "feed",
        "Feed #16": "feed",
    }
    # Loop through the tabs in each file and translate them
    fingerprints = {}
    for tab_name in tab_names:
        tab_rename = tab_name.strip().lower()
        if tab_rename in translation_map:
            standard_name = translation_map[tab_rename]
            fingerprints[tab_name] = standard_name
            # Report errors
        else:
            fingerprints[tab_name] = f"unknown_{tab_name}"
    return fingerprints

# Function to parse raw hierarchical excel file data structure
def parse_robotic_milking_data(file_name):
    # Get cow ID using previous function
    cow_ID = cow_id_from_file_name(file_name)
    # Translate messy tab names to standard names using previous function
    tab_fingerprints = fingerprint_tabs(file_name)
    tables = {}
    errors = {}
    # Process all raw data from all tabs
    for sheet_name, standard_name in tab_fingerprints.items():
        try:
            raw_df = pd.read_excel(file_name, sheet_name=sheet_name)
            raw_df["cow_ID"] = cow_ID
            tables[standard_name] = raw_df
            # Report errors
        except Exception as e:
            errors[standard_name] = f" failed on tab '{sheet_name}': {str(e)}"
    return cow_ID, tables, errors

# Read in robot milking data for cleaning
robot_milking_data = {}
for file_name in sorted(data_directory.glob("Robot Farm #*.xlsx")):
    print("Parsing:", file_name.name)
    cow_id, tables, errors = parse_robotic_milking_data(str(file_name))
    # Report any tab that failed to parse
    if errors:
        print("ISSUES:", errors)
    robot_milking_data[file_name.name] = tables


