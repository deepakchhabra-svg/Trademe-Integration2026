# Diagnostics scripts (read-only)

These scripts are **operator/developer diagnostics** and should be treated as **read-only** helpers.

## Safety rules

- **No writes**: do not commit scripts that mutate DB settings, enqueue commands, publish listings, or top-up gates.
- **No secrets**: do not print or embed credentials/tokens.
- **Expect 404/403**: Trade Me endpoints vary by account/app permissions.

## Common usage

Run from the repo root:

```bash
python verify_connection.py
python check_db_stats.py
python find_candidate.py
```

