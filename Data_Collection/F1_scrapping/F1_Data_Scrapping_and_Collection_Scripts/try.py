import fastf1
import requests
import pandas as pd
from datetime import datetime
import time

# Enable FastF1 cache
fastf1.Cache.enable_cache('f1_cache')

# Function to get race data from Ergast API
def get_race_info(season, round_number):
    url = f"https://ergast.com/api/f1/{season}/{round_number}.json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['MRData']['RaceTable']['Races']:
            race_info = data['MRData']['RaceTable']['Races'][0]
            circuit = race_info['Circuit']['circuitName']
            laps = race_info.get('Laps', 57)  # Default to 57 if laps not available
            return circuit, laps
    return None, None

# Function to get feature set for a single race
def get_race_feature_set(season, round_number):
    # Get basic race info from Ergast
    circuit, laps = get_race_info(season, round_number)
    if not circuit:
        return None  # Skip if data not available

    try:
        # Load race data from FastF1
        race = fastf1.get_session(season, circuit, 'R')
        race.load()

        # Calculate average lap time and pit lane time loss
        laps_data = race.laps
        avg_lap_time = laps_data['LapTime'].mean()
        pit_laps = laps_data[laps_data['PitOutTime'].notna() | laps_data['PitInTime'].notna()]
        regular_laps = laps_data[~(laps_data['PitOutTime'].notna() | laps_data['PitInTime'].notna())]
        avg_pit_loss = (pit_laps['LapTime'].mean() - regular_laps['LapTime'].mean()).total_seconds()

        # Retrieve weather data
        weather = race.weather_data
        track_temp = weather['TrackTemp'].mean()
        air_temp = weather['AirTemp'].mean()
        humidity = weather['Humidity'].mean()
        wind_speed = weather['WindSpeed'].mean()

        # Example placeholder values
        rain_probability = 0.1
        driver_aggressiveness = 'High'
        current_tire_condition = 'Moderate'
        competitor_pit_stop = 15
        safety_car_event = 1 if 'SafetyCar' in weather.columns else 0

        # feature dictionary
        feature_set = {
            'Season': season,
            'Round': round_number,
            'Circuit': circuit,
            'Laps': laps,
            'AvgLapTime': avg_lap_time.total_seconds() if avg_lap_time else None,
            'PitLaneTimeLoss': avg_pit_loss,
            'TireCompounds': ['Soft', 'Medium', 'Hard'],
            'TrackTemp': track_temp,
            'AirTemp': air_temp,
            'Humidity': humidity,
            'WindSpeed': wind_speed,
            'RainProbability': rain_probability,
            'DriverAggressiveness': driver_aggressiveness,
            'CurrentTireCondition': current_tire_condition,
            'CurrentLapTime': laps_data['LapTime'].iloc[-1].total_seconds() if not laps_data.empty else None,
            'CompetitorPitStop': competitor_pit_stop,
            'SafetyCarEvent': safety_car_event,
            'StrategyOutcome': None
        }

        return feature_set

    except Exception as e:
        print(f"Error loading race {season} {round_number}: {e}")
        return None

# Loop through all seasons and rounds, saving incrementally
current_year = datetime.now().year
for season in range(2005, current_year + 1):
    season_data = []
    for round_number in range(1, 23):
        feature_set = get_race_feature_set(season, round_number)
        if feature_set:
            season_data.append(feature_set)
        else:
            print(f"Skipping season {season}, round {round_number} due to missing data.")

        # Delay added to avoid hitting the rate limit
        time.sleep(2)

    # Save data incrementally for each season
    season_data_df = pd.DataFrame(season_data)
    output_path = f'./f1_data_{season}.csv'
    season_data_df.to_csv(output_path, index=False)
    print(f"Data for season {season} saved to {output_path}")

# Optional: Combine all season files into a single Excel file
all_race_data_df = pd.concat([pd.read_csv(f'./f1_data_{season}.csv') for season in range(2000, current_year + 1)], ignore_index=True)
final_output_path = './all_race_data.xlsx'
all_race_data_df.to_excel(final_output_path, index=False)
print(f"All data combined and saved to {final_output_path}")
