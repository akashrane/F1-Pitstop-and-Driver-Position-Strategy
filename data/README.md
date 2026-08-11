# Generated data layout

Generated data is intentionally excluded from Git. The pipeline uses:

- `data/raw/<source>/<season>/<round>/`: immutable source responses
- `data/interim/`: normalized source-specific tables
- `data/processed/`: validated canonical datasets

Published releases include checksums, source metadata, schema versions, and a validation report. Legacy files remain in their original folders and are never overwritten.
