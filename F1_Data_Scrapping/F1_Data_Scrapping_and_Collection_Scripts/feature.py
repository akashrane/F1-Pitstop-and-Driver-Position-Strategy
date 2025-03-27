import requests
import pandas as pd
import random  

def fetch_race_data(season):
    """
    Fetch race results and additional features for a given season using the Ergast API.
    """
    url = f"https://ergast.com/api/f1/{season}/results.json"
    response = requests.get(url)
    
    # Check if API request was successful
    if response.status_code != 200:
        print(f"Failed to fetch data for season {season}. Status Code: {response.status_code}")
        return []
    
    data = response.json()
    feature_data = []

    # Process each race
    for race in data['MRData']['RaceTable']['Races']:
        circuit = race['Circuit']['circuitName']
        round_number = race['round']
        laps = int(race['Results'][0]['laps'])  

        avg_lap_time = random.uniform(80, 110)  
        avg_pit_loss = random.uniform(20, 25)  
        track_temp = random.uniform(25, 40)  
        air_temp = random.uniform(15, 30)  # Simulated air temperature in Celsius
        humidity = random.uniform(40, 80)  # Simulated humidity percentage
        wind_speed = random.uniform(0, 15)  # Simulated wind speed in km/h
        rain_probability = random.uniform(0, 100)  # Simulated rain probability percentage
        driver_aggressiveness = random.uniform(1, 10)  # Simulated driver aggressiveness score
        current_tire_condition = random.choice(['Good', 'Fair', 'Poor'])  
        competitor_pit_stop = random.choice([0, 1])  
        safety_car_event = random.choice([0, 1])  

        # Process each driver in the race
        for result in race['Results']:
            driver = result['Driver']
            driver_name = f"{driver['givenName']} {driver['familyName']}"
            constructor = result['Constructor']['name']

            feature_set = {
                'Season': season,
                'Round': round_number,
                'Circuit': circuit,
                'Driver': driver_name,
                'Constructor': constructor,
                'Laps': laps,
                'AvgLapTime': avg_lap_time,
                'PitLaneTimeLoss': avg_pit_loss,
                'TireCompounds': ['Soft', 'Medium', 'Hard'],
                'TrackTemp': track_temp,
                'AirTemp': air_temp,
                'Humidity': humidity,
                'WindSpeed': wind_speed,
                'RainProbability': rain_probability,
                'DriverAggressiveness': driver_aggressiveness,
                'CurrentTireCondition': current_tire_condition,
                'CompetitorPitStop': competitor_pit_stop,
                'SafetyCarEvent': safety_car_event,
                'StrategyOutcome': None 
            }

            feature_data.append(feature_set)

    return feature_data


seasons = list(range(1950,2024))  
all_feature_data = []

for season in seasons:
    print(f"Fetching data for season {season}...")
    season_data = fetch_race_data(season)
    all_feature_data.extend(season_data)


df = pd.DataFrame(all_feature_data)
output_file = "f1_feature_set.csv"
df.to_csv(output_file, index=False)
print(f"Feature set saved successfully to {output_file}!")

print(df.head())
