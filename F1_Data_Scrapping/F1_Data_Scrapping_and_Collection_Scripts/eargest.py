import requests
import pandas as pd

def fetch_race_results(year):
    url = f"https://ergast.com/api/f1/{year}/results.json"
    response = requests.get(url)
    data = response.json()

    race_data = []
    for race in data['MRData']['RaceTable']['Races']:
        race_name = race['raceName']
        date = race['date']
        for result in race['Results']:
            driver = result['Driver']
            driver_name = f"{driver['givenName']} {driver['familyName']}"
            constructor = result['Constructor']['name']
            position = result['position']
            race_data.append([race_name, date, driver_name, constructor, position])

    return race_data

# Fetch data for multiple years
years = list(range(1950, 2024))
all_race_data = []

for year in years:
    print(f"Fetching F1 results for {year}...")
    year_data = fetch_race_results(year)
    all_race_data.extend(year_data)

# Save data to CSV
df = pd.DataFrame(all_race_data, columns=["Race", "Date", "Driver", "Constructor", "Position"])
df.to_csv("f1_api_results.csv", index=False)
print("Data saved successfully to f1_api_results.csv!")
