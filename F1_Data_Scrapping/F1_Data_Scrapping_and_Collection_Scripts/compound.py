import fastf1
import pandas as pd
import time

fastf1.Cache.enable_cache('f1_cache')

df_aggression = pd.read_csv("f1_aggression_with_abbreviations_column.csv")

tire_data = []
missing_sessions = []


df_grouped = df_aggression.groupby(["Season", "Round"])

for (season, round_number), group in df_grouped:
    if season < 2011 or season > 2020:
        print(f"Skipping {season} - No FastF1 data available.")
        missing_sessions.append(f"{season} Round {round_number}")
        continue

    print(f"Fetching tire stint data for {season} - Round {round_number}...")

    try:
        available_sessions = fastf1.get_event_schedule(season)
        if round_number not in available_sessions.index:
            print(f"No schedule data for {season} - Round {round_number}, skipping...")
            missing_sessions.append(f"{season} Round {round_number}")
            continue

        session = fastf1.get_session(season, round_number, "R")
        session.load(telemetry=False, weather=False, messages=False)

        if session.laps.empty:
            print(f"No lap data for {season} - Round {round_number}, skipping...")
            missing_sessions.append(f"{season} Round {round_number}")
            continue

        # Extract stint data
        stints = session.laps[["Driver", "Stint", "Compound", "LapNumber"]]
        stints = stints.groupby(["Driver", "Stint", "Compound"]).count().reset_index()
        stints = stints.rename(columns={"LapNumber": "Stint Length"})

        for _, stint in stints.iterrows():
            tire_data.append({
                "Season": season,
                "Round": round_number,
                "Driver Abbreviation": stint["Driver"],
                "Stint": stint["Stint"],
                "Tire Compound": stint["Compound"],
                "Stint Length": stint["Stint Length"]
            })

    except Exception as e:
        print(f"Error fetching tire stint data for {season} Round {round_number}: {e}")
        missing_sessions.append(f"{season} Round {round_number}")
        continue

    time.sleep(2)

df_tires = pd.DataFrame(tire_data)
df_tires.to_csv("f1_tire_stints_2011_2019.csv", index=False)

df_missing = pd.DataFrame(missing_sessions, columns=["Missing Session"])
df_missing.to_csv("missing_sessions_log_2.csv", index=False)

print(" Tire stint data saved successfully!")
