import requests
import pandas as pd

def parse_duration(duration):
    try:
        if ':' in duration:
            minutes, seconds = duration.split(':')
            return int(minutes) * 60 + float(seconds)
        else:
            return float(duration)
    except Exception as e:
        print(f"Error parsing duration: {duration}. Error: {e}")
        return None

def fetch_race_results_with_pitstops(season):

    base_url = f"https://ergast.com/api/f1/{season}"
    
    season_url = f"{base_url}.json"
    season_response = requests.get(season_url)
    if season_response.status_code != 200:
        print(f"Failed to fetch season info for {season}")
        return []

    season_data = season_response.json()
    total_rounds = int(season_data['MRData']['total']) 
    feature_data = []


    for round_number in range(1, total_rounds + 1):
        print(f"Fetching Round {round_number} for Season {season}...")

        race_results_url = f"{base_url}/{round_number}/results.json?limit=1000"
        response = requests.get(race_results_url)

        if response.status_code != 200:
            print(f"⚠️ No race results found for Season {season}, Round {round_number}.")
            continue 

        race_data = response.json()
        if not race_data['MRData']['RaceTable']['Races']:
            continue

        race = race_data['MRData']['RaceTable']['Races'][0]
        circuit = race['Circuit']['circuitName']


        pit_stop_url = f"{base_url}/{round_number}/pitstops.json?limit=1000"
        pit_stop_response = requests.get(pit_stop_url)
        pit_stop_data = []
        
        if pit_stop_response.status_code == 200:
            pit_stops = pit_stop_response.json()
            if pit_stops['MRData']['RaceTable']['Races']:
                pit_stop_data = pit_stops['MRData']['RaceTable']['Races'][0].get('PitStops', [])

        for result in race['Results']:
            driver = result['Driver']
            driver_name = f"{driver['givenName']} {driver['familyName']}"
            constructor = result['Constructor']['name']
            laps = int(result['laps'])
            position = result['position']


            driver_pit_stops = [
                {
                    "Lap": int(pit_stop['lap']),
                    "StopTime": parse_duration(pit_stop['duration'])
                }
                for pit_stop in pit_stop_data if pit_stop['driverId'] == driver['driverId']
            ]
            total_pit_stops = len(driver_pit_stops)
            avg_pit_stop_time = (
                sum(p['StopTime'] for p in driver_pit_stops if p['StopTime'] is not None) / total_pit_stops
                if total_pit_stops > 0 else None
            )

            feature_set = {
                'Season': season,
                'Round': round_number,
                'Circuit': circuit,
                'Driver': driver_name,
                'Constructor': constructor,
                'Laps': laps,
                'Position': position,
                'TotalPitStops': total_pit_stops,
                'AvgPitStopTime': avg_pit_stop_time,
                'PitStops': driver_pit_stops
            }

            feature_data.append(feature_set)

    return feature_data


seasons = list(range(1950, 2015))
all_feature_data = []

for season in seasons:
    print(f"Fetching data for season {season}...")
    season_data = fetch_race_results_with_pitstops(season)
    all_feature_data.extend(season_data)


df = pd.DataFrame(all_feature_data)
output_file = "f1_pitstop_data_1950_2015_1.csv"
df.to_csv(output_file, index=False)
print(f"Feature set with pit stop data saved successfully to {output_file}!")
