"""
Exploratory Data Analysis for the early detection of HPAI in cows
using robotic milking project
Data is collected by the DRIVE Lab from videos into Excel spreadsheets
Contributions by Brendan Daly
"""

# Load in necessary libraries
from pathlib import Path
import pandas as pd
from IPython.core.display_functions import display


# Read in the data
# Function to read in data with three inputs, folder with file, file name, and the df name
def read_data(parent_folder,file_name,df_name):
    data_directory = Path(__file__).parent / parent_folder
    file_path = data_directory / file_name
    df_name = pd.read_excel(file_path)
    return df_name

# HPAI viral test results using ELISA
HPAI_results = read_data("data","Robot_dairy_results.xlsx","HPAI_results")
print(HPAI_results.head())

# All Robotic Milking Data Files
data_directory = Path(__file__).parent / "data"

Robot_milking_data = {}

for file_path in data_directory.glob("Robot Farm #*.xlsx"):

    file_name = file_path.name
    print("Reading:", file_name)

    # Read all tabs from the Excel file
    sheets = pd.read_excel(file_path, sheet_name=None)

    # Store all tabs for this farm
    Robot_milking_data[file_name] = sheets

# More initial data analysis
# HPAI Results pre-clean analysis
# First 15 rows
print(HPAI_results.head(15))
# Last 15 riws
print(HPAI_results.tail(15))
print("\nNumber of rows:")
print(len(HPAI_results))
print("\nUnique values:")
print(HPAI_results.nunique())
print("\nDuplicates")
HPAI_results_duplicates = HPAI_results[HPAI_results.duplicated()]
print(HPAI_results_duplicates)
print("\nNumber of duplicate rows:", HPAI_results.duplicated().sum())

# Robotic milking data pre-clean analysis
for file_name, sheets in Robot_milking_data.items():

    # Separate files with lines
    print("\n" + "=" * 60)
    print("File:", file_name)
    print("=" * 60)

    for sheet_name, df in sheets.items():

        # Separate tabs with lines
        print("\n" + "-" * 40)
        print("Tab:", sheet_name)
        print("-" * 40)

        # First 15 rows
        print("\nFirst 15 rows:")
        print(df.head(15))

        # Last 15 rows
        print("\nLast 15 rows:")
        print(df.tail(15))

        # Unique values
        print("\nUnique values:")
        print(df.nunique())

        # Duplicates
        duplicates = df[df.duplicated()]
        print("\nDuplicates:")
        print(duplicates)

        print("\nNumber of duplicate rows:", df.duplicated().sum())

# Clean the data
# Clean HPAI Results
# (no duplicates)
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

# Check for missing values
print("Number of N/A:", HPAI_results.isna().sum())

# Check for duplicates again
print("Exact duplicate rows:", HPAI_results.duplicated().sum())

display(HPAI_results)
# Data analysis with clean data

# Correlation Matrix

# Plots

# Conclusion