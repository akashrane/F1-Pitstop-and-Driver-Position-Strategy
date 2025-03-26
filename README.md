🏎️ F1 Position Change Predictor 🏎️ 

Predict driver **position changes** during an F1 race using weather, tire, and race telemetry data. This project leverages advanced machine learning models like **XGBoost** and **Random Forest** to analyze driver behavior and pit strategy patterns.

---

## Author
- Akash Rane
- Master’s in Computer Science
- Pace University
- Linkden

---

---

##  Project Overview

Modern F1 races generate massive amounts of telemetry and weather data. This project aims to:
-  Analyze factors like tire usage, weather, and pit times
-  Predict driver **position changes**
-  Use **machine learning** models for predictive insight
-  Validate predictions using custom datasets
-  Build an **interactive dashboard** (in-progress)

---
## Key libraries:

- xgboost
- pandas, numpy
- matplotlib, seaborn
- scikit-learn

---

##  Features Used

Final features selected for prediction:
- `Laps`
- `Fast Lap Attempts`
- `Driver Aggression Score`
- `Tire Usage Aggression`
- `AvgPitStopTime`
- `Lap Time Variation`
- `Pit_Time`
- `Total Pit Stops`
- `Driver` (encoded)

---

##  Models & Performance

| Model               | MAE     | RMSE    | R² Score |
|--------------------|---------|---------|----------|
| Linear Regression   | 0.0273  | 0.0532  | 0.954    |
| Random Forest       | 0.0548  | 0.0813  | 0.892    |
| Gradient Boosting   | 0.1301  | 0.1600  | 0.584    |
| **XGBoost (best)**  | 0.0330  | 0.0588  | **0.944** |

 Hyperparameter tuning improved the model significantly.

---

## Validation Results

We used a synthetic dataset to validate the model’s output. The predicted values were consistent and correlated with expected patterns based on:
- **Aggressive driving behavior**
- **Pit strategy**
- **Lap dynamics**

 See the full [Validation Report](reports/validation_report.ipynb)

---

## Upcoming Dashboard

I am developing a **Streamlit-based interactive dashboard** to:
- Upload new race data
- Predict position changes on the fly
- Visualize driver behavior and impact

Stay tuned — it will go in `/dashboard/`.

---

## Acknowledgements
- Formula 1 telemetry data
- Kaggle weather datasets
- Seaborn, scikit-learn & XGBoost

---

