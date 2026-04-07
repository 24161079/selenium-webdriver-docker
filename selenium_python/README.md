# Selenium Python Rewrite

This folder is a Python + Selenium rewrite of the original TypeScript + Playwright source.

## Structure

- config.py
- constants.py
- app_types.py
- index.py
- steps/
- utils/

## Run with Docker Compose

```bash
docker compose up --build
```

Then open noVNC:

- http://localhost:7900

## Notes

- Business logic should be implemented in step modules, mainly:
  - steps/process_data.py
  - steps/upload_files.py
  - steps/download_input_files.py
- The orchestration flow is in index.py and mirrors the old source flow.
