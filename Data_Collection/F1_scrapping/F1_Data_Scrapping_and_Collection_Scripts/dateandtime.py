import requests
import pandas as pd

def fetch_race_schedule(season):

    url = f"https://ergast.com/api/f1/{season}.json"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch race data for season {season}.")
        return []

    data = response.json()
    race_schedule = []

    for race in data['MRData']['RaceTable']['Races']:
        race_name = race['raceName']
        round_number = race['round']
        date = race['date'] 
        time = race['time'] if 'time' in race else "Unknown"  #
        circuit = race['Circuit']['circuitName']
        location = race['Circuit']['Location']['locality']
        country = race['Circuit']['Location']['country']

        race_schedule.append({
            "Season": season,
            "Round": round_number,
            "Race Name": race_name,
            "Date": date,
            "Time (UTC)": time,
            "Circuit": circuit,
            "Location": location,
            "Country": country
        })

    return race_schedule

seasons = list(range(1950, 2025))  
all_feature_data = []

for season in seasons:
    print(f"Fetching data for season {season}...")
    season_data = fetch_race_schedule(season)
    all_feature_data.extend(season_data)

# Convert to DataFrame and save as CSV
df = pd.DataFrame(all_feature_data)
output_file = "f1_pitstop_Date_time_1950_2024.csv"
df.to_csv(output_file, index=False)
print(f"Feature set with pit stop data saved successfully to {output_file}!")