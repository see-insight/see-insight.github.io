"""
Exploratory Data Analysis for the early detection of HPAI in cows
using robotic milking project
Data is collected by the DRIVE Lab from videos into Excel spreadsheets
Contributions by Brendan Daly
"""

# Load in necessary libraries
from pathlib import Path
import pandas as pd

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

# All Robotic Milking Data Files (Very Messy!)
data_directory = Path(__file__).parent / "data"
Robot_milking_data = []
for file_path in data_directory.glob("Robot Farm #*.xlsx"):
    file_name = file_path.name
    print("Reading:", file_name)
    df = read_data("data", file_name, "Robot_milking_data")
    Robot_milking_data.append(df)
print("Number of files:", len(Robot_milking_data))

# Combine the dataframes (messy, but necessary for the code)
Robot_milking_data = pd.concat(Robot_milking_data, ignore_index=True)

print("Number of rows:", len(Robot_milking_data))
# More initial data analysis

# Clean the data

# Data analysis with clean data

# Correlation Matrix

# Plots

# Conclusion