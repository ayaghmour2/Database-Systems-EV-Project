## Import Packages
import pdfplumber 
import pandas as pd
import re
import glob
import os
import matplotlib.pyplot as plt

##### Data Extraction #####
## Change working directory
os.chdir(r"C:\Users\aey1519\Documents\GitHub\Grad-School\Database Systems\Final Project\PDFs")

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
                    
## Set target location for CSVs
os.chdir(r"C:\Users\aey1519\Documents\GitHub\Grad-School\Database Systems\Final Project\Exports")

## Save to CSV
pd.DataFrame(county_rows).to_csv("county_level_ev_counts.csv", index=False)
pd.DataFrame(zip_rows).to_csv("zip_level_ev_counts.csv", index=False)

##### Exploratory Data Analysis #####
## Create pandas dataframes for analysis
county_df = pd.DataFrame(county_rows)
zipcode_df = pd.DataFrame(zip_rows)

## Data type for each dataframe
print(county_df.info())
print(zipcode_df.info())

## Count how many counties, zip codes, and cities there are
unique_counties = county_df['County'].nunique()
unique_zipcodes = zipcode_df['ZIP Code'].nunique()
unique_cities = zipcode_df['City'].nunique()
print(unique_counties, unique_zipcodes, unique_cities)

## Calculate average counts per county by year
## Extract year
county_df['Year'] = pd.to_datetime(county_df['Date']).dt.year

## Group by both Year and ZIP Code, then calculate the average
avg_per_year_zip = county_df.groupby(['Year', 'County'])['Count'].mean().reset_index()

## Find the top 5 and bottom 5 zip codes per year
result = []
for year in avg_per_year_zip['Year'].unique():
    year_df = avg_per_year_zip[avg_per_year_zip['Year'] == year]
    top5 = year_df.nlargest(5, 'Count')
    bottom5 = year_df.nsmallest(5, 'Count')
    result.append(pd.concat([top5.assign(Rank='Top 5'), bottom5.assign(Rank='Bottom 5')]))

county_top5_bottom5 = pd.concat(result)
print(county_top5_bottom5)

## Calculate average counts per zip code by year
## Extract year
zipcode_df['Year'] = zipcode_df['Date'].dt.year

## Group by both Year and ZIP Code, then calculate the average
avg_per_year_zip = zipcode_df.groupby(['Year', 'ZIP Code'])['Count'].mean().reset_index()

## Find the top 5 and bottom 5 zip codes per year
result = []
for year in avg_per_year_zip['Year'].unique():
    year_df = avg_per_year_zip[avg_per_year_zip['Year'] == year]
    top5 = year_df.nlargest(5, 'Count')
    bottom5 = year_df.nsmallest(5, 'Count')
    result.append(pd.concat([top5.assign(Rank='Top 5'), bottom5.assign(Rank='Bottom 5')]))

zipcode_top5_bottom5 = pd.concat(result)
print(zipcode_top5_bottom5)

## Find top 5 and bottom 5 total for county
## Group by County and calculate the average count across all years
avg_county = county_df.groupby('County')['Count'].mean().reset_index()

## Find top 5 and bottom 5 counties
top5_county = avg_county.nlargest(5, 'Count').assign(Rank='Top 5')
bottom5_county = avg_county.nsmallest(5, 'Count').assign(Rank='Bottom 5')

## Combine results
county_top_bottom = pd.concat([top5_county, bottom5_county])
print(county_top_bottom)

## Find any counties with no EVs for the entire period
zero_avg_county = avg_county[avg_county['Count'] == 0]
print(zero_avg_county)

## Find top 5 and bottom 5 total for zipcode
## Group by zipcode and calculate the average count across all years
avg_zipcode = zipcode_df.groupby('ZIP Code')['Count'].mean().reset_index()

## Find top 5 and bottom 5 counties
top5_zipcode = avg_zipcode.nlargest(5, 'Count').assign(Rank='Top 5')
bottom5_zipcode = avg_zipcode.nsmallest(5, 'Count').assign(Rank='Bottom 5')

## Combine results
zipcode_top_bottom = pd.concat([top5_zipcode, bottom5_zipcode])
print(zipcode_top_bottom)

## Find any zipcodes with no EVs for the entire period
zero_avg_zipcodes = avg_zipcode[avg_zipcode['Count'] == 0]
print(zero_avg_zipcodes)


## Find top 5 and bottom 5 total for city
## Group by County and calculate the average count across all years
avg_city = zipcode_df.groupby('City')['Count'].mean().reset_index()

## Find top 5 and bottom 5 counties
top5_city = avg_city.nlargest(5, 'Count').assign(Rank='Top 5')
bottom5_city = avg_city.nsmallest(5, 'Count').assign(Rank='Bottom 5')

## Combine results
city_top_bottom = pd.concat([top5_city, bottom5_city])
print(city_top_bottom)

## Find any zipcodes with no EVs for the entire period
zero_avg_city = avg_city[avg_city['Count'] == 0]
print(zero_avg_city)

## Explore overall data trends
## Group by Date and sum counts across all ZIP codes
overall_trend = zipcode_df.groupby('Date')['Count'].sum().reset_index()

## Plot the trend
plt.figure(figsize=(12, 6))
plt.plot(overall_trend['Date'], overall_trend['Count'], marker='o', linestyle='-', color='teal')
plt.title('Overall EV Count Trend by Date')
plt.xlabel('Date')
plt.ylabel('Total Count')
plt.grid(True)
plt.tight_layout()
plt.xticks(rotation=45)
plt.show()

## Display yearly counts
print(overall_trend)

## Find the top 10 increases
## Set start and end date
first_date = zipcode_df['Date'].min()
last_date = zipcode_df['Date'].max()

## Group by city and date then sum
city_date_counts = zipcode_df.groupby(['City', 'Date'])['Count'].sum().reset_index()

## Get counts for the first and last date
first_counts = city_date_counts[city_date_counts['Date'] == first_date].set_index('City')['Count']
last_counts = city_date_counts[city_date_counts['Date'] == last_date].set_index('City')['Count']

## Calculate growth
city_growth = pd.DataFrame({
    'September 2021': first_counts,
    'July 2025': last_counts
}).dropna()

city_growth['Increase'] = city_growth['July 2025'] - city_growth['September 2021']

## Find the top 10
top_10_cities = city_growth.sort_values(by='Increase', ascending=False).head(10).reset_index()

## Display the result
print(top_10_cities)

## Find the bottom 10
bottom_10_cities = city_growth.sort_values(by='Increase', ascending=True).head(10).reset_index()

## Display the result
print(bottom_10_cities)

## List all cities with decreases
## Filter for decreases
decreased_cities = city_growth[city_growth['Increase'] < 0].sort_values(by='Increase')

## Display the result
print(decreased_cities)

## Find the cities with the top increases in percentage (when units > 25)
## Filter cities with at least 25 registered cars in September 2021
percent_city_growth = city_growth[city_growth['September 2021'] >= 25].copy()

## Calculate percent increase
percent_city_growth['Percent Increase'] = ((percent_city_growth['July 2025'] - percent_city_growth['September 2021']) / city_growth['September 2021']) * 100

## Filter for cities with positive percent increase and take the top 10
top_10_percent_increase = percent_city_growth[percent_city_growth['Percent Increase'] > 0].sort_values(by='Percent Increase', ascending=False).head(10).reset_index()

## Display the result
print(top_10_percent_increase)

## Plot trends by county
county_monthly_counts = county_df.groupby(['Date', 'County'])['Count'].sum().reset_index()

## Pivot table for plotting
pivot_df = county_monthly_counts.pivot(index='Date', columns='County', values='Count')

## Plot the trend
plt.figure(figsize=(15, 8))
pivot_df.plot(ax=plt.gca(), legend=False, alpha=0.7)
plt.title('Monthly Electric Vehicle Counts by County')
plt.xlabel('Month')
plt.ylabel('EV Count')
plt.legend(loc='upper left', bbox_to_anchor=(1, 1), ncol=2, fontsize='small')
plt.tight_layout()
plt.show()

## Plot trends by zipcode
zipcode_monthly_counts = zipcode_df.groupby(['Date', 'ZIP Code'])['Count'].sum().reset_index()

## Pivot table for plotting
pivot_df = zipcode_monthly_counts.pivot(index='Date', columns='ZIP Code', values='Count')

## Plot the trend
plt.figure(figsize=(15, 8))
pivot_df.plot(ax=plt.gca(), legend=False, alpha=0.7)
plt.title('Monthly Electric Vehicle Counts by Zipcode')
plt.xlabel('Month')
plt.ylabel('EV Count')
plt.legend(loc='upper left', bbox_to_anchor=(1, 1), ncol=2, fontsize='small')
plt.tight_layout()
plt.show()

## Plot trends by city
city_monthly_counts = zipcode_df.groupby(['Date', 'City'])['Count'].sum().reset_index()

## Pivot table for plotting
pivot_df = city_monthly_counts.pivot(index='Date', columns='City', values='Count')

## Plot the trend
plt.figure(figsize=(15, 8))
pivot_df.plot(ax=plt.gca(), legend=False, alpha=0.7)
plt.title('Monthly Electric Vehicle Counts by City')
plt.xlabel('Month')
plt.ylabel('EV Count')
plt.legend(loc='upper left', bbox_to_anchor=(1, 1), ncol=2, fontsize='small')
plt.tight_layout()
plt.show()

## Histogram for counts by county
## Group by County and Date and  calculate average
county_grouped = county_df.groupby(['County', 'Date'])['Count'].mean().reset_index()

# Plot histogram for each county
## Group by County and calculate the average
county_avg = county_df.groupby('County')['Count'].mean().reset_index()

## Filter out counties with average count below 100
county_avg = county_avg[county_avg['Count'] >= 100]

## Sort by average count in descending order
county_avg = county_avg.sort_values(by='Count', ascending=False)

## Plot histogram of average counts by county
plt.figure(figsize=(10, 6))
plt.bar(county_avg['County'], county_avg['Count'], color='blue', edgecolor='black')

plt.title('Average Monthly Vehicle Counts by County')
plt.xlabel('County')
plt.ylabel('Registered EVs')
plt.xticks(rotation=45)
plt.grid(axis='y')
plt.tight_layout()
plt.show()

## Histogram for counts by zipcode
## Group by Zipcode and Date and calculate average
zipcode_grouped = zipcode_df.groupby(['ZIP Code', 'Date'])['Count'].mean().reset_index()

# Plot histogram for each county
## Group by county and calculate the average
zipcode_avg = zipcode_df.groupby('ZIP Code')['Count'].mean().reset_index()

## Filter out counties with average count below 400
zipcode_avg = zipcode_avg[zipcode_avg['Count'] >= 400]

## Sort by average count in descending order
zipcode_avg = zipcode_avg.sort_values(by='Count', ascending=False)

## Plot histogram of average counts by zipcode
plt.figure(figsize=(10, 6))
plt.bar(zipcode_avg['ZIP Code'], zipcode_avg['Count'], color='blue', edgecolor='black')

plt.title('Average Monthly Vehicle Counts by Zipcode')
plt.xlabel('Zipcode')
plt.ylabel('Registered EVs')
plt.xticks(rotation=45)
plt.grid(axis='y')
plt.tight_layout()
plt.show()

## Histogram for counts by city
## Group by City and Date and calculate average
city_grouped = zipcode_df.groupby(['City', 'Date'])['Count'].mean().reset_index()

## Group by city and calculate the average
city_avg = zipcode_df.groupby('City')['Count'].mean().reset_index()

## Filter out counties with average count below 500
city_avg = city_avg[city_avg['Count'] >= 500]

## Sort by average count in descending order
city_avg = city_avg.sort_values(by='Count', ascending=False)

## Plot histogram of average counts by city
plt.figure(figsize=(10, 6))
plt.bar(city_avg['City'], city_avg['Count'], color='blue', edgecolor='black')

plt.title('Average Monthly Vehicle Counts by City')
plt.xlabel('City')
plt.ylabel('Registered EVs')
plt.xticks(rotation=55)
plt.grid(axis='y')
plt.tight_layout()
plt.show()

## Random Sample Analysis
## Randomly select 15 unique ZIP codes
sampled_zips = zipcode_df['ZIP Code'].dropna().unique()
sampled_zips = pd.Series(sampled_zips).sample(15, random_state=2)

## Filter the original DataFrame to include only those ZIP codes
df_random_sample = zipcode_df[zipcode_df['ZIP Code'].isin(sampled_zips)]

## Group by ZIP Code, Date, and City to calculate average Count
date_avg = df_random_sample.groupby(['ZIP Code', 'City', 'Date'])['Count'].mean().reset_index()

## Plot the trends
plt.figure(figsize=(12, 6))

## Plot a line for each ZIP Code with City in the label
for (zip_code, city), group in date_avg.groupby(['ZIP Code', 'City']):
    label = f"{zip_code} ({city})"
    plt.plot(group['Date'], group['Count'], marker='o', label=label)

plt.title('Average Count Trends for Sampled ZIP Codes')
plt.xlabel('Date')
plt.ylabel('Average Count')
plt.xticks(rotation=45)
plt.legend(title='ZIP Code (City)', bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.grid(True)
plt.show()

## Display sorted overall averages
overall_avg_table = df_random_sample.groupby(['ZIP Code', 'City'])['Count'].mean().reset_index()
overall_avg_table = overall_avg_table.sort_values(by='Count', ascending=False)
print(overall_avg_table)

