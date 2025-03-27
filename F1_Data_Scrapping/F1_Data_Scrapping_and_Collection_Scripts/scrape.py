from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time

# Configure WebDriver
chrome_options = Options()
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

def scrape_f1_results(year):
    url = f"https://www.formula1.com/en/results.html/{year}/races.html"
    driver.get(url)

    # Wait for the page to load
    time.sleep(10)  # Allow additional time for JavaScript to render
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)

    # Debug: Check page source
    print("Debugging HTML Content...")
    print(driver.page_source[:2000])  # Print a snippet of the HTML

    # Locate race rows
    try:
        race_elements = driver.find_elements(By.CSS_SELECTOR, "tr.resultsarchive-row")
        print(f"Found {len(race_elements)} race elements for {year}.")
    except Exception as e:
        print(f"Error locating race elements: {e}")
        return []

    race_data = []
    for race in race_elements:
        try:
            race_name = race.find_element(By.CSS_SELECTOR, "td a").text
        except:
            race_name = "N/A"

        try:
            date = race.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text
        except:
            date = "N/A"

        try:
            winner = race.find_element(By.CSS_SELECTOR, "td:nth-child(3)").text
        except:
            winner = "N/A"

        try:
            car = race.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text
        except:
            car = "N/A"

        try:
            laps = race.find_element(By.CSS_SELECTOR, "td:nth-child(5)").text
        except:
            laps = "N/A"

        try:
            time_or_points = race.find_element(By.CSS_SELECTOR, "td:nth-child(6)").text
        except:
            time_or_points = "N/A"

        race_data.append([race_name, date, winner, car, laps, time_or_points])
        print(race_name, date, winner, car, laps, time_or_points)  # Debugging

    return race_data

# Scrape data for multiple years
years = list(range(2015, 2024))
all_race_data = []

for year in years:
    print(f"Scraping F1 results for {year}...")
    year_data = scrape_f1_results(year)
    all_race_data.extend(year_data)

driver.quit()

# Save data to CSV
df = pd.DataFrame(all_race_data, columns=["Race", "Date", "Winner", "Car", "Laps", "Time/Points"])
if not df.empty:
    df.to_csv("f1_race_results.csv", index=False)
    print("Data saved successfully to f1_race_results.csv!")
else:
    print("No data scraped! CSV file was not created.")
