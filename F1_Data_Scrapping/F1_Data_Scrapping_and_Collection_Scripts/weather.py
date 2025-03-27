import requests
import time
import pandas as pd
import numpy as np
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
            print(f"⚠️ No coordinates found for {city}")
            return None, None
    except requests.exceptions.RequestException as e:
        print(f"❌ Geocoding API Error for {city}: {e}")
        return None, None

def get_weather_per_hour(city, date):
    """
    Fetch hourly weather data (air & track temperature, humidity, wind speed) for a given city and date.
    """
    lat, lon = get_lat_lon(city)
    if lat is None or lon is None:
        return None

    # Fetch weather data from Open-Meteo API
    weather_url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={date}&end_date={date}&hourly=temperature_2m,soil_temperature_0cm,relative_humidity_2m,wind_speed_10m"
    headers = {"User-Agent": "F1-Weather-Data-Collector"}
    
    try:
        weather_response = requests.get(weather_url, headers=headers)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

        if "hourly" in weather_data:
            # ✅ Convert all data to float & handle missing values
            return pd.DataFrame({
                "Hour": list(range(24)),
                "AirTemp": pd.to_numeric(weather_data["hourly"]["temperature_2m"], errors="coerce").fillna(20.0),
                "TrackTemp": pd.to_numeric(weather_data["hourly"]["soil_temperature_0cm"], errors="coerce").fillna(25.0),
                "Humidity": pd.to_numeric(weather_data["hourly"]["relative_humidity_2m"], errors="coerce").fillna(60.0),
                "WindSpeed": pd.to_numeric(weather_data["hourly"]["wind_speed_10m"], errors="coerce").fillna(10.0),
            })
        else:
            print(f"⚠️ No weather data available for {city} on {date}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Weather API Error for {city}: {e}")
        return None

# ✅ Load dataset with pit stops and laps
file_path = "f1_pitstop_with_schedule.csv"
df_races = pd.read_csv(file_path)

# ✅ Create Weather Data for Each Lap
race_weather_data = []

for _, race in df_races.iterrows():
    season, round_number, circuit, date, race_time, location, laps = race["Season"], race["Round"], race["Circuit"], race["Date"], race["Time (UTC)"], race["Location"], race["Laps"]

    print(f"🌍 Fetching weather for {location} on {date} at {race_time}...")

    hourly_weather = get_weather_per_hour(location, date)
    if hourly_weather is None:
        continue

    # ✅ Convert laps to numeric safely
    try:
        total_laps = int(laps)
    except ValueError:
        print(f"⚠️ Invalid lap count for {circuit} on {date}, skipping...")
        continue

    # ✅ Interpolate weather conditions per lap
    lap_numbers = np.linspace(0, 23, total_laps)  # Create lap-based index
    lap_weather = pd.DataFrame({
        "Lap": range(1, total_laps + 1),
        "AirTemp": np.interp(lap_numbers, hourly_weather["Hour"], hourly_weather["AirTemp"]),
        "TrackTemp": np.interp(lap_numbers, hourly_weather["Hour"], hourly_weather["TrackTemp"]),
        "Humidity": np.interp(lap_numbers, hourly_weather["Hour"], hourly_weather["Humidity"]),
        "WindSpeed": np.interp(lap_numbers, hourly_weather["Hour"], hourly_weather["WindSpeed"]),
    })

    for _, lap in lap_weather.iterrows():
        race_weather_data.append({
            "Season": season,
            "Round": round_number,
            "Circuit": circuit,
            "Date": date,
            "Time (UTC)": race_time,
            "Lap": int(lap["Lap"]),
            "Air Temperature (°C)": lap["AirTemp"],
            "Track Temperature (°C)": lap["TrackTemp"],
            "Humidity (%)": lap["Humidity"],
            "Wind Speed (km/h)": lap["WindSpeed"]
        })

    # Avoid API rate limits
    time.sleep(1)

# ✅ Convert to DataFrame
df_weather = pd.DataFrame(race_weather_data)

# ✅ Save Weather Data Per Lap
df_weather.to_csv("f1_weather_per_lap.csv", index=False)
print("✅ Lap-based weather data saved successfully!")

# ✅ Merge with Pit Stop Data (if needed)
df_final = df_races.merge(df_weather, on=["Season", "Round", "Circuit", "Date", "Time (UTC)"], how="left")
df_final.to_csv("f1_pitstops_with_lap_weather.csv", index=False)
print("✅ Full dataset with lap weather merged saved successfully!")
