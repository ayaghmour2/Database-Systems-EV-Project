## Packages
import pdfplumber 
import pandas as pd
import re
import glob
import os
import requests
import sqlite3
import time

########## Creating a SQL Database for Benchmarking ##########
#####  Counts by County and City Database #####

## Change working directory
os.chdir(r"C:\Documents\GitHub\Database-Systems-EV-Project\Data")

## Grab all files with 'electric' in the file name
pdf_files = glob.glob("electric*.pdf")

## Extract County and Zip Code
county_rows = []
zip_rows = []

for pdf_file in pdf_files:
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        
        ## Extract date from header
        date_match = re.search(r"AS OF (\d{2}/\d{2}/\d{4})", text)
        date = pd.to_datetime(date_match.group(1)) if date_match else None
        
        ## County table extraction
        county_section = re.search(r"COUNTY TOTALS AS OF.*?\n(.*?)(?:ELECTRIC VEHICLES IN ILLINOIS ZIPCODE TOTALS|ELECTRIC VEHICLES IN ILLINOIS\\nZIPCODE TOTALS|ZIPCODE TOTALS AS OF)",
    text, re.DOTALL)
        if county_section:
            county_lines = county_section.group(1).split("\n")
            for line in county_lines:
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
            zip_lines = zip_section.group(1).split("\n")
            for line in zip_lines:
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

#####  Charging Stations #####
## Load the CSV
df = pd.read_csv("Electric and Alternative Fuel Charging Stations.csv")

## Filter to only electric stations
ev_df = df[df['Fuel Type Code'] == 'ELEC']

## Further filter to only Illinois stations
ev_il_df = ev_df[ev_df['State'] == 'IL']

## Columns to drop as they are completely empty or nearly empty 
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
ev_il_df = ev_il_df.drop(columns=cols_to_drop, errors = 'ignore')

## Fill NA values with 0 for charger counts
for col in ['EV Level1 EVSE Num', 'EV Level2 EVSE Num', 'EV DC Fast Count']:
    ev_il_df[col] = ev_il_df[col].fillna(0)

## Create total chargers column
ev_il_df['Total Chargers'] = (
    ev_il_df['EV Level1 EVSE Num'] +
    ev_il_df['EV Level2 EVSE Num'] +
    ev_il_df['EV DC Fast Count']
)

## Fill missing charger counts with 0
ev_il_df['EV DC Fast Count'] = ev_il_df['EV DC Fast Count'].fillna(0)
ev_il_df['EV Level2 EVSE Num'] = ev_il_df['EV Level2 EVSE Num'].fillna(0)

## Convert Open Date to datetime
ev_il_df['Open Date'] = pd.to_datetime(ev_il_df['Open Date'], errors='coerce')

## Extract year from Open Date
ev_il_df['Open Year'] = ev_il_df['Open Date'].dt.year

#####  Demographic Data #####
## Set your Census API key (register here: https://api.census.gov/data/key_signup.html)
API_KEY = "0b0513fe67b0e2da1250859200feb24c65be5558"
BASE_URL = "https://api.census.gov/data/2022/acs/acs5"

## Configuration
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

## Multi-Year Data Pull
county_all = []
zcta_all = []

for yr in YEARS:
    print(f"Pulling data for {yr}...")

    base_url = f"https://api.census.gov/data/{yr}/acs/acs5/profile"

    ## ---- COUNTY DATA ----
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

    ## ---- ZCTA DATA ----
    params_zcta = {
        "get": ",".join(["NAME"] + VARIABLES_COUNTS),
        "for": "zip code tabulation area:*",
        "key": API_KEY
    }
    resp = requests.get(base_url, params=params_zcta)
    resp.raise_for_status()
    data = resp.json()
    df_zcta = pd.DataFrame(columns=data[0], data=data[1:])
    df_zcta.rename(columns=lambda x: COL_RENAME.get(x, x), inplace=True)
    df_zcta["Year"] = yr

    ## Illinois ZIP filter (prefix method: 60xxx, 61xxx, 62xxx)
    df_zcta = df_zcta[df_zcta['zip code tabulation area'].str.startswith(('60', '61', '62'))]

    zcta_all.append(df_zcta)

## Combine all years
county_df = pd.concat(county_all, ignore_index=True)
zcta_df = pd.concat(zcta_all, ignore_index=True)

#####  Create the Database #####
## Establish the connection
conn = sqlite3.connect("EV-SQL.db")

## Convert dataframes to SQL
## County-level EV counts
pd.DataFrame(county_rows).to_sql("ev_county_totals", conn, if_exists="replace", index=False)

## Zip-level EV counts
pd.DataFrame(zip_rows).to_sql("ev_zip_totals", conn, if_exists="replace", index=False)

## Charging stations in Illinois
ev_il_df.to_sql("charging_stations_il", conn, if_exists="replace", index=False)

## Census county demographics
county_df.to_sql("demographics_county", conn, if_exists="replace", index=False)

## Census ZIP code demographics
zcta_df.to_sql("demographics_zip", conn, if_exists="replace", index=False)

## Create indexes
## Index for county-level EV data
conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_county_totals_county ON ev_county_totals(county);")

## Index for ZIP-level EV data
conn.execute("CREATE INDEX IF NOT EXISTS idx_ev_zip_totals_zip ON ev_zip_totals('ZIP Code');")

## Index for charging stations
conn.execute("CREATE INDEX IF NOT EXISTS idx_charging_stations_zip ON charging_stations_il(ZIP);")

## Index for county demographics
conn.execute("CREATE INDEX IF NOT EXISTS idx_demographics_county ON demographics_county(county);")

## Index for ZIP demographics
conn.execute("CREATE INDEX IF NOT EXISTS idx_demographics_zip ON demographics_zip('zip code tabulation area');")
    
##### Query Test Speeds #####
## Set up function
def run_query(conn, query, label):
    start = time.time()
    result = conn.execute(query).fetchall()
    end = time.time()
    duration = end - start
    print(f"{label}: {len(result)} rows returned in {duration:.4f} seconds")
    return result

## Simple select
_ = run_query(conn, "SELECT * FROM demographics_zip LIMIT 100;", "Simple SELECT")
## Simple SELECT: 100 rows returned in 0.0020 seconds

## Population above 100,000
_ = run_query(conn, """
    SELECT * FROM demographics_zip
    WHERE CAST(Total_Population AS INTEGER) > 100000;
""", "Filter: Zip Pop > 100K")
## Filter: Zip Pop > 100K: 3 rows returned in 0.0412 seconds

## Above median income
_ = run_query(conn, """
    SELECT * FROM demographics_county
    WHERE CAST(Median_HH_Income AS INTEGER) > 60000;
""", "Filter: County Income > 60K")
## Filter: County Income > 60K: 188 rows returned in 0.0064 seconds

## Join test
_ = run_query(conn, """
    SELECT cs."Station Name", dz."zip code tabulation area", dz.Total_Population
    FROM charging_stations_il cs
    JOIN demographics_zip dz ON cs.ZIP = dz."zip code tabulation area"
    WHERE CAST(dz.Total_Population AS INTEGER) > 50000;
""", "Join: Stations + Zip Pop > 50K")
## Join: Stations + Zip Pop > 50K: 473 rows returned in 0.0069 seconds

## Rank zip codes
_ = run_query(conn, """
    SELECT ZIP, COUNT(*) AS station_count
    FROM charging_stations_il
    GROUP BY ZIP
    ORDER BY station_count DESC
    LIMIT 10;
""", "Top 10 Zip Codes by Station Count")
## Top 10 Zip Codes by Station Count: 10 rows returned in 0.0254 seconds
