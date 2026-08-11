# Legacy data quarantine

The existing files in `F1_Position_Predictor/Formula1_Data` and `F1_Data_Scrapping/Data_Retived` are frozen legacy artifacts. They are retained to reproduce the original academic project and existing Kaggle versions.

They must not be consumed by the new training or publication pipeline unless a file has been migrated into a canonical table and passed validation.

Known risks include:

- unavailable historical pit-stop coverage represented as zero;
- Open-Meteo soil temperature labeled as F1 track temperature;
- full-day weather interpolated across laps without session timestamps;
- random or synthetic features in the original feature generator;
- character-encoding corruption;
- mixed race-driver and stint grains;
- synthetic validation and possible post-race target leakage.

The migration process never edits these artifacts in place. It writes immutable raw snapshots and new canonical outputs under `data/`.
