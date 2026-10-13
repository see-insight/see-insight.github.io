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
import pandas as pd
from IPython.display import display

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

# Analyze the data after cleaning it
analyze_HPAI_results(HPAI_results, "POST-CLEAN")

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
        "Daily milk #16": "daily_milk",
        "MD #162": "daily_milk",
        "MD #163": "daily_milk",
        "MD #164": "daily_milk",
        "MD #165": "daily_milk",
        "MD #166": "daily_milk",
        "MD #167": "daily_milk",
        "MD #168": "daily_milk",
        "Daily milk #18": "daily_milk",
        "Daily milk #19": "daily_milk",
        "Daily milk #2": "daily_milk",
        "Daily milk #21": "daily_milk",
        "Daily milk #23": "daily_milk",
        "Daily milk #26": "daily_milk",
        "Daily milk #27": "daily_milk",
        "Daily milk #28": "daily_milk",
        "Daily milk #3": "daily_milk",
        "Daily milk #32": "daily_milk",
        "Daily milk #33": "daily_milk",
        "Daily milk #34": "daily_milk",
        "Daily milk #35": "daily_milk",
        "Daily Milk #36": "daily_milk",
        "Daily milk#40": "daily_milk",
        "Daily milk #41": "daily_milk",
        "Daily Milk #47": "daily_milk",
        "Daily milk #49": "daily_milk",
        "Daily Milk #53": "daily_milk",
        "Daily milk #54": "daily_milk",
        "Daily Milk #55": "daily_milk",
        "Daily milk #57": "daily_milk",
        "Daily milk #58": "daily_milk",
        "Daily milk #60": "daily_milk",
        "Daily milk #62": "daily_milk",
        "Daily milk #63": "daily_milk",
        "Daily milk #64": "daily_milk",
        "Daily milk #66": "daily_milk",
        "Daily milk #67": "daily_milk",
        "Daily milk #69": "daily_milk",
        "Daily milk #7": "daily_milk",
        "Daily milk #72": "daily_milk",
        "Daily milk #73": "daily_milk",
        "Daily milk #74": "daily_milk",
        "Daily milk #76": "daily_milk",
        "Daily milk #77": "daily_milk",
        "Daily milk #78": "daily_milk",
        "Daily mik #8": "daily_milk",
        "Daily milk #80": "daily_milk",
        "Daily milk #81": "daily_milk",
        "Daily milk #82": "daily_milk",
        "Daily milk #86": "daily_milk",
        "Daily milk #87": "daily_milk",
        "Daily Milk": "daily_milk",
        "Daily Milk": "daily_milk",
        "Daily Milk": "daily_milk",
        "Daily Milk": "daily_milk",
        "Daily Milk": "daily_milk",
        "Daily Milk": "daily_milk",

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
        "MQ #162": "quality",
        "MQ #163": "quality",
        "MQ #164": "quality",
        "MQ #165": "quality",
        "MQ #166": "quality",
        "MQ #167": "quality",
        "MQ #168": "quality",
        "Quality #18": "quality",
        "Quality #19": "quality",
        "Quality #2": "quality",
        "Quality #21": "quality",
        "Quality #23": "quality",
        "Quality #26": "quality",
        "Quality #27": "quality",
        "Quality #28": "quality",
        "Quality #3": "quality",
        "Quality #32": "quality",
        "Quality #33": "quality",
        "Quality #34": "quality",
        "Quality #35": "quality",
        "Quality #36": "quality",
        "Quality #40": "quality",
        "Quality #41": "quality",
        "Quality #47": "quality",
        "Quality #49": "quality",
        "Quality #53": "quality",
        "Quality #54": "quality",
        "Quality #55": "quality",
        "Quality #57": "quality",
        "Quality #58": "quality",
        "Quality #60": "quality",
        "Quality #62": "quality",
        "Quality #63": "quality",
        "Quality #64": "quality",
        "Quality #66": "quality",
        "Quality #67": "quality",
        "Quality #69": "quality",
        "Quality #7": "quality",
        "Quality #72": "quality",
        "Quality #73": "quality",
        "Quality #74": "quality",
        "Quality #76": "quality",
        "Quality #77": "quality",
        "Quality #78": "quality",
        "Quality #8": "quality",
        "Quality #80": "quality",
        "Quality #81": "quality",
        "Quality #82": "quality",
        "Quality #86": "quality",
        "Quality #87": "quality",
        "Quality": "quality",
        "Quality": "quality",
        "Quality": "quality",
        "Quality": "quality",
        "Quality": "quality",
        "Quality": "quality",

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
        "MV #162": "visits",
        "MV #163": "visits",
        "MV #164": "visits",
        "MV #165": "visits",
        "MV #166": "visits",
        "MV #167": "visits",
        "MV #168": "visits",
        "Visits #18": "visits",
        "Visits #19": "visits",
        "Visits #2": "visits",
        "Visits #21": "visits",
        "Visits #23": "visits",
        "Visits #26": "visits",
        "Visits #27": "visits",
        "Visits #28": "visits",
        "Visits #3": "visits",
        "Visits #32": "visits",
        "Visits #33": "visits",
        "Visits #34": "visits",
        "Visits #35": "visits",
        "Visits #36": "visits",
        "Visits #40": "visits",
        "Visits #41": "visits",
        "Visits #47": "visits",
        "Visits #49": "visits",
        "Visits #53": "visits",
        "Visits #54": "visits",
        "Visits #55": "visits",
        "Visits #57": "visits",
        "Visits #58": "visits",
        "Visits #60": "visits",
        "Visits #62": "visits",
        "Visits #63": "visits",
        "Visits #64": "visits",
        "Visits #66": "visits",
        "Visits #67": "visits",
        "Visits #69": "visits",
        "Visits #7": "visits",
        "Visits #72": "visits",
        "Visits #73": "visits",
        "Visits #74": "visits",
        "Visits #76": "visits",
        "Visits #77": "visits",
        "Visits #78": "visits",
        "Visits #8": "visits",
        "Visits #80": "visits",
        "Visits #81": "visits",
        "Visits #82": "visits",
        "Visits #86": "visits",
        "Visits #87": "visits",
        "Visit": "visits",
        "Visit": "visits",
        "Visit": "visits",
        "Visit": "visits",
        "Visit": "visits",
        "Visit": "visits",

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
        "LAC #162": "lactation",
        "LAC #163": "lactation",
        "LAC #164": "lactation",
        "LAC #165": "lactation",
        "LAC #166": "lactation",
        "LAC #167": "lactation",
        "LAC #168": "lactation",
        "Lactation #18": "lactation",
        "Lactation #19": "lactation",
        "Lactation #2": "lactation",
        "Lactation #21": "lactation",
        "Lactation #23": "lactation",
        "Lactation #26": "lactation",
        "Lactation #27": "lactation",
        "Lactation #28": "lactation",
        "Lactation #3": "lactation",
        "Lactation #32": "lactation",
        "Lactation #33": "lactation",
        "Lactation #34": "lactation",
        "Lactation #35": "lactation",
        "Lactation #36": "lactation",
        "Lactation #40": "lactation",
        "Lactation #41": "lactation",
        "Lactation #47": "lactation",
        "Lactation #49": "lactation",
        "Lactation #53": "lactation",
        "Lactation #54": "lactation",
        "Lactation #55": "lactation",
        "Lactation #57": "lactation",
        "Lactation #58": "lactation",
        "Lactation #60": "lactation",
        "Lactation #62": "lactation",
        "Lactation #63": "lactation",
        "Lactation #64": "lactation",
        "Lactation #66": "lactation",
        "Lactation #67": "lactation",
        "Lactation #69": "lactation",
        "Lactation #7": "lactation",
        "Lactation #72": "lactation",
        "Lactation #73": "lactation",
        "Lactation #74": "lactation",
        "Lactation #76": "lactation",
        "Lactation #77": "lactation",
        "Lactation #78": "lactation",
        "Lactation #8": "lactation",
        "Lactation #80": "lactation",
        "Lactation #81": "lactation",
        "Lactation #82": "lactation",
        "Lactation #86": "lactation",
        "Lactation #87": "lactation",
        "Lactation": "lactation",
        "Lactation": "lactation",
        "Lactation": "lactation",
        "Lactation": "lactation",
        "Lactation": "lactation",
        "Lactation": "lactation",

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
        "EVENTS #162": "events",
        "EVENTS #163": "events",
        "EVENTS #164": "events",
        "EVENTS #165": "events",
        "EVENTS #166": "events",
        "EVENTS #167": "events",
        "EVENTS #168": "events",
        "Events #18": "events",
        "Events #19": "events",
        "Events #2": "events",
        "Events #21": "events",
        "Events #23": "events",
        "Events #26": "events",
        "Events #27": "events",
        "Events #28": "events",
        "Events #3": "events",
        "Events #32": "events",
        "Events #33": "events",
        "Events #34": "events",
        "Events #35": "events",
        "Events #36": "events",
        "Events #40": "events",
        "Events #41": "events",
        "Events #47": "events",
        "Events #49": "events",
        "Events #53": "events",
        "Events #54": "events",
        "Events #55": "events",
        "Events #57": "events",
        "Events #58": "events",
        "Events #60": "events",
        "Events #62": "events",
        "Events #63": "events",
        "Events #64": "events",
        "Events #66": "events",
        "Events #67": "events",
        "Events #69": "events",
        "Events #7": "events",
        "Events #72": "events",
        "Events #73": "events",
        "Events #74": "events",
        "Events #76": "events",
        "Events #77": "events",
        "Events #78": "events",
        "Events #8": "events",
        "Events #80": "events",
        "Events #81": "events",
        "Events #82": "events",
        "Events #86": "events",
        "Events #87": "events",
        "Event": "events",
        "Events": "events",
        "Events": "events",
        "Events": "events",
        "Events": "events",
        "Events": "events",

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
        "FD #162": "feed",
        "FD #163": "feed",
        "FD #164": "feed",
        "FD #165": "feed",
        "FD #166": "feed",
        "FD #167": "feed",
        "FD #168": "feed",
        "Feed #18": "feed",
        "Feed #19": "feed",
        "Feed #2": "feed",
        "Feed #21": "feed",
        "Feed #23": "feed",
        "Feed #26": "feed",
        "Feed #27": "feed",
        "Feed #28": "feed",
        "Feed #3": "feed",
        "Feed #32": "feed",
        "Feed #33": "feed",
        "Feed #34": "feed",
        "Feed #35": "feed",
        "Feed #36": "feed",
        "Feed #40": "feed",
        "Feed #41": "feed",
        "Feed #47": "feed",
        "Feed #49": "feed",
        "Feed #53": "feed",
        "Feed #54": "feed",
        "Feed #55": "feed",
        "Feed #57": "feed",
        "Feed #58": "feed",
        "Feed #60": "feed",
        "Feed #62": "feed",
        "Feed #63": "feed",
        "Feed #64": "feed",
        "Feed #66": "feed",
        "Feed #67": "feed",
        "Feed #69": "feed",
        "Feed #7": "feed",
        "Feed #72": "feed",
        "Feed #73": "feed",
        "Feed #74": "feed",
        "Feed #76": "feed",
        "Feed #77": "feed",
        "Feed #78": "feed",
        "Feed #8": "feed",
        "Feed #80": "feed",
        "Feed #81": "feed",
        "Feed #82": "feed",
        "Feed #86": "feed",
        "Feed #87": "feed",
        "Feed": "feed",
        "Feed": "feed",
        "Feed": "feed",
        "Feed": "feed",
        "Feed": "feed",
        "Feed": "feed",
    }
    # Normalize dictionary keys
    translation_map = {
        key.strip().lower(): value
        for key, value in translation_map.items()
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

# Function to analyze robot milking data
def analyze_robot_data(data_dict, label):
    total_files = len(data_dict)
    total_tabs = sum(len(sheets) for sheets in data_dict.values())
    print(f"{label}")
    print("Number of files:", total_files)
    print("Number of tabs:", total_tabs)
    for file_name, sheets in data_dict.items():
        # Separate files with lines
        print("=" * 60)
        print("File:", file_name)
        print("=" * 60)
        for sheet_name, df in sheets.items():
            # Separate tabs with lines
            print("-" * 40)
            print("Tab:", sheet_name)
            print("-" * 40)
            print(df.head(3))
            print(df.tail(3))
            print("Unique values:", df.nunique())
            duplicates = df[df.duplicated()]
            print("Duplicates:", duplicates)
            print("Number of duplicate rows:", df.duplicated().sum())
            print("Number of NA per column:", df.isna().sum())
            print("Total NA:", df.isna().sum().sum())

# Analyze the data before cleaning it
analyze_robot_data(robot_milking_data, "PRE-CLEAN")

# Clean daily_milk
def clean_daily_milk(df):
    clean_df = df.copy()
    # Manually cleaned data

    return clean_df

# Clean quality
def clean_quality(df):
    clean_df = df.copy()
    # Manually cleaned data

    return clean_df

# Clean visits
def clean_visits(df):
    clean_df = df.copy()
    # Manually cleaned data

    return clean_df

# Clean lactation
def clean_lactation(df):
    clean_df = df.copy()
    # Manually cleaned data

    return clean_df

# Clean events (events are mostly just text, and they likely won't be very useful for our models.)
def clean_events(df):
    clean_df = df.copy()
    # Manually cleaned data

    return clean_df

# Clean feed
def clean_feed(df):
    clean_df = df.copy()
    # Manually cleaned data

    return clean_df

# Analyze the data after cleaning it
analyze_robot_data(robot_milking_data, "POST-CLEAN")