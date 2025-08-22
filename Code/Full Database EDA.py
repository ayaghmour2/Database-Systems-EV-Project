# -*- coding: utf-8 -*-
"""
Created on Thu Aug 21 19:10:22 2025

@author: aey1519
"""

## Packages
import os
import psycopg2
import pdfplumber
import pandas as pd
import glob
import re
import matplotlib.pyplot as plt
import requests
import seaborn as sns
import time
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError


## Set directory
os.chdir('C:/Users/aey1519/Documents/GitHub/Database-Systems-EV-Project/Data')

## Load the station data
df = pd.read_csv("Electric and Alternative Fuel Charging Stations.csv")
il_df = df[df['State'] == 'IL']

## Columns to Drop as they are completely empty or nearly empty 
cols_to_drop = [
    'Plus4', 'BD Blends', 'NG Fill Type Code', 'NG PSI',
    'Expected Date', 'Cards Accepted', 'EV Other Info',
    'Federal Agency ID', 'Federal Agency Name',
    'Hydrogen Status Link', 'NG Vehicle Class', 'LPG Primary',
    'E85 Blender Pump', 'Intersection Directions (French)',
    'Access Days Time (French)', 'BD Blends (French)',
    'Groups With Access Code (French)', 'Hydrogen Is Retail',
    'Federal Agency Code', 'CNG Dispenser Num', 'CNG On-Site Renewable Source',
    'CNG Total Compression Capacity', 'CNG Storage Capacity',
    'LNG On-Site Renewable Source', 'E85 Other Ethanol Blends',
    'EV Pricing (French)', 'LPG Nozzle Types', 'Hydrogen Pressures',
    'Hydrogen Standards', 'CNG Fill Type Code', 'CNG PSI',
    'CNG Vehicle Class', 'LNG Vehicle Class', 'EV On-Site Renewable Source'
]

## Drop columns from your Illinois EV dataset
il_df = il_df.drop(columns=cols_to_drop, errors = 'ignore')
il_df.head()

## Fill NA with 0 for charger counts
for col in ['EV Level1 EVSE Num', 'EV Level2 EVSE Num', 'EV DC Fast Count']:
    il_df[col] = il_df[col].fillna(0)

## Create total chargers column
il_df['Total Chargers'] = (
    il_df['EV Level1 EVSE Num'] +
    il_df['EV Level2 EVSE Num'] +
    il_df['EV DC Fast Count']
)

## Check new shape and preview
print(il_df.shape)
il_df[['Station Name', 'City', 'ZIP', 'Total Chargers']].head()
il_df['Total Chargers'].value_counts().sort_index()

## Only electric chargers
ev_df = il_df[il_df['Fuel Type Code'] == 'ELEC']
ev_df['Total Chargers'].value_counts().sort_index()

## Load the demographic data
# ==============================
# CONFIG
# ==============================
API_KEY = "0b0513fe67b0e2da1250859200feb24c65be5558"
STATE_FIPS = "17"  # Illinois
YEARS = ["2021", "2022", "2023"]

## Variables (counts only) - Added Total Population
VARIABLES_COUNTS = [
    ## Total Population
    "DP05_0001E",
    ## Income
    "DP03_0062E","DP03_0052E","DP03_0053E","DP03_0054E","DP03_0055E",
    "DP03_0056E","DP03_0057E","DP03_0058E","DP03_0059E","DP03_0060E",
    "DP03_0061E",
    ## Age
    "DP02_0014E","DP02_0015E","DP02_0016E","DP02_0017E","DP02_0018E",
    "DP02_0019E","DP02_0020E","DP02_0021E","DP02_0022E","DP02_0023E",
    "DP02_0024E","DP02_0025E","DP02_0026E",
    ## Education
    "DP02_0062E","DP02_0063E","DP02_0064E","DP02_0065E","DP02_0066E",
    "DP02_0067E","DP02_0068E",
    ## Race/Ethnicity
    "DP05_0037E","DP05_0038E","DP05_0039E","DP05_0044E","DP05_0052E",
    "DP05_0057E","DP05_0058E","DP05_0071E","DP05_0072E"
]

## Human-readable mapping for major variables
COL_RENAME = {
    "NAME": "Geography",
    "DP05_0001E": "Total_Population",
    "DP03_0062E": "Median_HH_Income",
    "DP03_0052E": "HH_Income_<10k",
    "DP03_0053E": "HH_Income_10k_14k",
    "DP03_0054E": "HH_Income_15k_24k",
    "DP03_0055E": "HH_Income_25k_34k",
    "DP03_0056E": "HH_Income_35k_49k",
    "DP03_0057E": "HH_Income_50k_74k",
    "DP03_0058E": "HH_Income_75k_99k",
    "DP03_0059E": "HH_Income_100k_149k",
    "DP03_0060E": "HH_Income_150k_199k",
    "DP03_0061E": "HH_Income_200k_plus",
    "DP02_0014E": "Age_Under_5",
    "DP02_0015E": "Age_5_9",
    "DP02_0016E": "Age_10_14",
    "DP02_0017E": "Age_15_19",
    "DP02_0018E": "Age_20_24",
    "DP02_0019E": "Age_25_34",
    "DP02_0020E": "Age_35_44",
    "DP02_0021E": "Age_45_54",
    "DP02_0022E": "Age_55_59",
    "DP02_0023E": "Age_60_64",
    "DP02_0024E": "Age_65_74",
    "DP02_0025E": "Age_75_84",
    "DP02_0026E": "Age_85_plus",
    "DP02_0062E": "Edu_Less_9th",
    "DP02_0063E": "Edu_9_12_NoDiploma",
    "DP02_0064E": "Edu_HS_Grad",
    "DP02_0065E": "Edu_SomeCollege",
    "DP02_0066E": "Edu_Associate",
    "DP02_0067E": "Edu_Bachelors",
    "DP02_0068E": "Edu_Graduate",
    "DP05_0037E": "Race_White",
    "DP05_0038E": "Race_Black",
    "DP05_0039E": "Race_AmericanIndian",
    "DP05_0044E": "Race_Asian",
    "DP05_0052E": "Race_NativeHawaiian",
    "DP05_0057E": "Race_Other",
    "DP05_0058E": "Race_TwoOrMore",
    "DP05_0071E": "Ethn_Hispanic",
    "DP05_0072E": "Ethn_NonHispanic"
}

# ==============================
# MULTI-YEAR DATA PULL
# ==============================
county_all = []
zip_all = []

for yr in YEARS:
    print(f"Pulling data for {yr}...")

    base_url = f"https://api.census.gov/data/{yr}/acs/acs5/profile"

    # ---- COUNTY DATA ----
    params_county = {
        "get": ",".join(["NAME"] + VARIABLES_COUNTS),
        "for": "county:*",
        "in": f"state:{STATE_FIPS}",
        "key": API_KEY
    }
    resp = requests.get(base_url, params=params_county)
    resp.raise_for_status()
    data = resp.json()
    df_county = pd.DataFrame(columns=data[0], data=data[1:])
    df_county.rename(columns=lambda x: COL_RENAME.get(x, x), inplace=True)
    df_county["Year"] = yr
    county_all.append(df_county)

    # ---- zip DATA ----
    params_zip = {
        "get": ",".join(["NAME"] + VARIABLES_COUNTS),
        "for": "zip code tabulation area:*",
        "key": API_KEY
    }
    resp = requests.get(base_url, params=params_zip)
    resp.raise_for_status()
    data = resp.json()
    df_zip = pd.DataFrame(columns=data[0], data=data[1:])
    df_zip.rename(columns=lambda x: COL_RENAME.get(x, x), inplace=True)
    df_zip["Year"] = yr

    # Illinois ZIP filter (prefix method: 60xxx, 61xxx, 62xxx)
    df_zip = df_zip[df_zip['zip code tabulation area'].str.startswith(('60', '61', '62'))]

    zip_all.append(df_zip)
    
## Combine all years
county_df = pd.concat(county_all, ignore_index=True)
zip_df = pd.concat(zip_all, ignore_index=True)

print("✅ Pull complete:")
print("  County DF shape:", county_df.shape)
print("  Zip DF shape:", zip_df.shape)

# ==============================
# SAVE FINAL COMBINED CSVs
# ==============================
county_df.to_csv("il_census_county_counts_2021_2023.csv", index=False)
zip_df.to_csv("il_census_zcta_counts_2021_2023.csv", index=False)

print("✅ Multi-year combined files saved successfully.")

## Load the saved data
county_demo_df = pd.read_csv("il_census_county_counts_2021_2023.csv", dtype=str)
zip_demo_df = pd.read_csv("il_census_zcta_counts_2021_2023.csv", dtype=str)
county_demo_df.head()
county_demo_df.shape

zip_demo_df.head()
zip_demo_df.shape

## Load the EV coutns data
## Grab all files with 'electric' in the file name
pdf_files = sorted(glob.glob("electric*.pdf"))
print(f"{len(pdf_files)} PDFs found")

## Extract County and Zip Code
county_rows, zip_rows = [], []

start = time.time()

for i, pdf_file in enumerate(pdf_files, start=1):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            t = page.extract_text() or ""
            text += t + "\n"

    ## Extract date from header
    date_match = re.search(r"AS OF (\d{2}/\d{2}/\d{4})", text)
    date = pd.to_datetime(date_match.group(1)) if date_match else None

    ## County table extraction
    county_section = re.search(
        r"COUNTY TOTALS AS OF.*?\n(.*?)(?:ELECTRIC VEHICLES IN ILLINOIS ZIPCODE TOTALS|ELECTRIC VEHICLES IN ILLINOIS\\nZIPCODE TOTALS|ZIPCODE TOTALS AS OF)",
        text, re.DOTALL
    )
    if county_section:
        for line in county_section.group(1).split("\n"):
            match = re.match(r"([A-Z .'-]+?)\s*\.*\s+([0-9]+)", line.strip())
            if match:
                county, count = match.groups()
                county_rows.append({
                    "Date": date,
                    "County": county.strip(),
                    "Count": int(count),
                    "Source File": pdf_file
                })

    ## Zip code table extraction
    zip_section = re.search(r"ZIPCODE TOTALS AS OF.*?\n(.*)", text, re.DOTALL)
    if zip_section:
        for line in zip_section.group(1).split("\n"):
            match = re.match(r"([A-Z .'-]+)\s+(\d{5})\s+([0-9]+)", line.strip())
            if match:
                city, zipcode, count = match.groups()
                zip_rows.append({
                    "Date": date,
                    "City": city.strip(),
                    "ZIP Code": zipcode,
                    "Count": int(count),
                    "Source File": pdf_file
                })

    ## Progress print
    print(f"Finished {i}/{len(pdf_files)}: {pdf_file}")
    sys.stdout.flush()

elapsed = time.time() - start
print(f"\nAll done in {elapsed:.2f} seconds")

## Convert to DataFrames for downstream work (optional but handy)
county_df = pd.DataFrame(county_rows)
zip_df    = pd.DataFrame(zip_rows)

print("county_df:", county_df.shape, "zip_df:", zip_df.shape)

## Create pandas dataframes for analysis
county_registration_df = pd.DataFrame(county_rows)
zipcode_registration_df = pd.DataFrame(zip_rows)

## Data type for each dataframe
print(county_registration_df.info())
print(zipcode_registration_df.info())
zipcode_registration_df.columns

## Connect to your local postgres db
engine = create_engine("postgresql+psycopg2://postgres:JopFlop17@localhost:5432/ev_project", future=True)

## Database name to check/create
db_name = "ev_project"

## SQL to check if the database exists
check_db_sql = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
create_db_sql = f"CREATE DATABASE {db_name}"

with engine.connect() as conn:
    result = conn.execute(check_db_sql, {"dbname": db_name}).scalar()
    if result:
        print(f"Database '{db_name}' already exists.")
    else:
        try:
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text(create_db_sql))
            print(f"Database '{db_name}' created successfully.")
        except ProgrammingError as e:
            print(f"Failed to create database: {e}")

## Adjust zipcode
def fix_zip(series):
    return (series.astype(str)
                  .str.extract(r"(\d{5})")[0]   # grab 5 digits if present
                  .str.zfill(5))
## Charging data
if "ZIP" in il_df.columns:
    il_df = il_df.rename(columns={"ZIP": "zipcode"})
    il_df["zipcode"] = fix_zip(il_df["zipcode"])

## Zip demographics
if "Zip" in zip_df.columns:
    zip_df = zip_df.rename(columns={"Zip": "zipcode"})
    zip_df["zipcode"] = fix_zip(zip_df["zipcode"])

## Zipcode registration
if "ZIP Code" in zipcode_registration_df.columns:
    zipcode_registration_df = zipcode_registration_df.rename(columns={"ZIP Code": "zipcode"})
    zipcode_registration_df["zipcode"] = fix_zip(zipcode_registration_df["zipcode"])

## Charging stations
il_df.to_sql("il_df", engine, index=False, if_exists="replace")

## County registration
county_registration_df.to_sql("county_registration_df", engine, index=False, if_exists="replace")

## Zipcode registration
zipcode_registration_df.to_sql("zipcode_registration_df", engine, index=False, if_exists="replace")

## Zip demographics
zip_demo_df.to_sql("zip_demo_df", engine, index=False, if_exists="replace")

## County demographics
county_demo_df.to_sql("county_demo_df", engine, index=False, if_exists="replace")
