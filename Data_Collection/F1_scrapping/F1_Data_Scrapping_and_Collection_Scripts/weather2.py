import requests
import time
import pandas as pd
import os
from datetime import datetime

def get_lat_lon(city):
    """
    Fetch latitude and longitude for a given city using OpenStreetMap API.
    """
    geocode_url = f"https://nominatim.openstreetmap.org/search?city={city}&format=json"
    headers = {"User-Agent": "F1-Weather-Data-Collector"}
    
    try:
        response = requests.get(geocode_url, headers=headers)
        response.raise_for_status()
        geo_data = response.json()
        
        if geo_data:
            return float(geo_data[0]['lat']), float(geo_data[0]['lon'])
        else:
            print(f"No coordinates found for {city}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"Geocoding API Error for {city}: {e}")
        return None, None

def get_avg_weather(city, date):
    """
    Fetch and compute the average weather data (air & track temperature, humidity, wind speed) for a given city and date.
    """
    lat, lon = get_lat_lon(city)
    if lat is None or lon is None:
        return None

    # Auto-detect and convert date format
    try:
        date = str(date).strip()
        if "-" in date and date.count("-") == 2:
            for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%m-%d-%Y"):
                try:
                    date_obj = datetime.strptime(date, fmt)
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue
            else:
                print(f"Unsupported date format: {date} for {city}, skipping...")
                return None
        else:
            print(f"Invalid date format: {date} for {city}, skipping...")
            return None
    except Exception as e:
        print(f"Error processing date {date} for {city}: {e}")
        return None

    # Fetch weather data from Open-Meteo API
    weather_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={formatted_date}&end_date={formatted_date}&hourly=temperature_2m,soil_temperature_0cm,relative_humidity_2m,wind_speed_10m"
    headers = {"User-Agent": "F1-Weather-Data-Collector"}
    
    try:
        weather_response = requests.get(weather_url, headers=headers)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        if "hourly" in weather_data:
            avg_air_temp = sum(weather_data["hourly"]["temperature_2m"]) / len(weather_data["hourly"]["temperature_2m"])
            avg_track_temp = sum(filter(None, weather_data["hourly"]["soil_temperature_0cm"])) / max(1, len(list(filter(None, weather_data["hourly"]["soil_temperature_0cm"]))))
            avg_humidity = sum(weather_data["hourly"]["relative_humidity_2m"]) / len(weather_data["hourly"]["relative_humidity_2m"])
            avg_wind_speed = sum(weather_data["hourly"]["wind_speed_10m"]) / len(weather_data["hourly"]["wind_speed_10m"])

            return {
                "Air Temperature (°C)": avg_air_temp,
                "Track Temperature (°C)": avg_track_temp,
                "Humidity (%)": avg_humidity,
                "Wind Speed (km/h)": avg_wind_speed
            }
        else:
            print(f"No weather data available for {city} on {formatted_date}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Weather API Error for {city}: {e}")
        return None

# Load dataset
file_path = "f1_pitstop_with_schedule.csv"
df_races = pd.read_csv(file_path)

# Filter data from 2011 onwards
df_races = df_races[df_races["Season"] >= 2011]

# Check if previous data exists to resume from last recorded race
weather_file = "f1_avg_race_weather.csv" 
if os.path.exists(weather_file):
    df_existing = pd.read_csv(weather_file)
    completed_races = set(zip(df_existing["Season"], df_existing["Round"], df_existing["Circuit"], df_existing["Date"]))
else:
    df_existing = pd.DataFrame()
    completed_races = set()

# Create Weather Data Per Race
race_weather_data = []

for _, race in df_races.iterrows():
    season, round_number, circuit, date, race_time, location = race["Season"], race["Round"], race["Circuit"], race["Date"], race["Time (UTC)"], race["Location"]

    if (season, round_number, circuit, date) in completed_races:
        print(f"Skipping {circuit} on {date}, already processed.")
        continue

    print(f"Fetching weather for {location} on {date} at {race_time}...")

    avg_weather = get_avg_weather(location, date)
    if avg_weather is None:
        continue

    race_weather_data.append({
        "Season": season,
        "Round": round_number,
        "Circuit": circuit,
        "Date": date,
        "Time (UTC)": race_time,
        "Air Temperature (°C)": avg_weather["Air Temperature (°C)"],
        "Track Temperature (°C)": avg_weather["Track Temperature (°C)"],
        "Humidity (%)": avg_weather["Humidity (%)"],
        "Wind Speed (km/h)": avg_weather["Wind Speed (km/h)"]
    })

    df_temp = pd.DataFrame(race_weather_data)
    df_temp.to_csv(weather_file, mode="a", header=not os.path.exists(weather_file), index=False)
    completed_races.add((season, round_number, circuit, date))
    time.sleep(1)

# Merge with Pit Stop Data
df_weather = pd.read_csv(weather_file)
df_final = df_races.merge(df_weather, on=["Season", "Round", "Circuit", "Date", "Time (UTC)"], how="left")
df_final.to_csv("f1_pitstops_with_avg_weather.csv", index=False)

print("Full dataset with average race weather merged saved successfully!")
