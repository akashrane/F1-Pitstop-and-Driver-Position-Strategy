# 🏎️ F1 Position Change Predictor 🏁  
Predicting driver **position changes** in Formula 1 using real-time telemetry, tire strategy, and weather data.

This project leverages machine learning models like **XGBoost** and **Random Forest** to understand the impact of pit stop strategy, driver behavior, and environmental conditions on race outcomes.

---

## 👨‍💻 Author  
**Akash Rane**  
Master’s in Computer Science | Pace University  
[LinkedIn](https://www.linkedin.com/in/akashrane/) | [Portfolio](https://akashrane.github.io/website/) 

---

## 📌 Project Overview  
Modern Formula 1 races generate huge amounts of data from sensors, weather feeds, and driver telemetry. This project dives into that data to:

- Predict **driver position changes** during a race  
- Analyze key factors like **tire compounds**, **aggressiveness**, **weather**, and **pit stops**  
- Train and validate predictive models using historical race data (1950–2024)  
- Visualize insights and build an upcoming **interactive dashboard**

---

## 🛠️ Tech Stack & Libraries  

- **Python**, **Pandas**, **NumPy**  
- **XGBoost**, **Random Forest**, **Linear Regression**  
- **Matplotlib**, **Seaborn**, **scikit-learn**  
- **APIs**: Ergast, Open-Meteo, FastF1  
- **Web Scraping**: Selenium

---

## 🧪 Feature Engineering  
Selected predictive features include:

- `Laps`, `Fast Lap Attempts`, `Lap Time Variation`  
- `AvgPitStopTime`, `Pit Time`, `Total Pit Stops`  
- `Driver Aggression Score`, `Tire Usage Aggression`  
- Encoded categorical values like `Driver`, `Tire Compound`

---

## 📈 Model Comparison

| Model                | MAE     | RMSE    | R² Score |
|---------------------|---------|---------|----------|
| Linear Regression    | 0.0273  | 0.0532  | 0.954    |
| Random Forest        | 0.0548  | 0.0813  | 0.892    |
| Gradient Boosting    | 0.1301  | 0.1600  | 0.584    |
| **XGBoost (Best)**   | 0.0330  | 0.0588  | **0.944** |

*XGBoost outperformed others post hyperparameter tuning.*

---

## ✅ Model Validation  

To verify model performance, a synthetic validation set was generated based on real-world behavior. Key validation highlights:

- Accurate reflection of **aggressive driving patterns**  
- Reliable correlation between **pit stop timing** and position shifts  
- Sensitivity to **lap-by-lap weather fluctuations**

📄 [Read the full Validation Report](/F1_Position_Predictor/Reports/Validation_Report_F1_Position_Change.md)

---

## 🧾 Data Pipeline  
This project combines multiple data sources and APIs into a single dataset:

- 🛠️ **Race Results & Pit Stops** – Ergast API (1950–2024)  
- 🌡️ **Hourly Weather** – Open-Meteo (city + date-based retrieval)  
- 🧪 **Tire Strategy & Aggression** – FastF1 telemetry and stint tracking  
- 🕐 **Schedule & Timing** – Ergast + Selenium scraping for edge cases

---

## 📊 Upcoming Feature: Interactive Dashboard  
🚧 **In Progress** – A **Streamlit** dashboard to:

- Upload new race data  
- Predict position changes on the fly  
- Visualize the influence of tire strategies and weather  

🗂️ Will be added to `/dashboard/` soon.

---

## 🙌 Acknowledgements  

- Formula 1 Open Telemetry & FastF1  
- Kaggle & Open-Meteo weather APIs  
- scikit-learn, XGBoost, Matplotlib, Seaborn  
- Ergast Developer API for historical F1 race data
