# Generated data layout

Generated data is intentionally excluded from Git. The pipeline uses:

- `data/raw/<source>/<season>/<round>/`: immutable source responses
- `data/interim/`: normalized source-specific tables
- `data/processed/`: validated canonical datasets

Published releases include checksums, source metadata, schema versions, and a validation report. Legacy files remain in their original folders and are never overwritten.

Bulk builds also create `data/processed/manifest_<start>_<end>.json` and a `consolidated_<start>_<end>/` folder. Races without detailed source coverage are recorded as `unavailable`; they are never silently omitted or filled with invented values.

OpenF1 detailed session coverage begins in 2023. The 2018–2022 detailed backfill therefore uses a separate FastF1 adapter rather than pretending the OpenF1 pipeline covers those seasons.
