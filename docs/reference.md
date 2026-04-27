# AI Job Email Alerts Reference

## What This Project Does

This project:

- finds recent jobs with JobSpy
- gives each job a score
- optionally asks Ollama to do a second pass
- saves good jobs to Google Sheets
- can email you a simple digest
- can run on GitHub Actions

## Main Files

- `bot.py`
  main command line entry
- `app/config.py`
  default search settings and scoring rules
- `app/jobspy_jobs.py`
  job search and filtering logic
- `app/ollama_fit.py`
  Ollama scoring logic
- `app/google_sheets.py`
  Google Sheets read and write helpers
- `app/email_jobs.py`
  email sending helpers
- `docs/profile_notes.md`
  your personal scoring notes

## Default Flow

1. Search for jobs.
2. Remove obvious bad matches.
3. Score the remaining jobs.
4. Save approved jobs to a Google Sheet.
5. Email a digest if you want.

## Important Commands

Collect jobs:

```bash
python3 bot.py --max-jobs 12 --max-jobs-per-day 8 --hours-old 24 --sheets-url "YOUR_GOOGLE_SHEET_URL" --sheets-tab "Email Jobs"
```

Send today's digest:

```bash
python3 bot.py --send-sheet-digest --sheets-url "YOUR_GOOGLE_SHEET_URL" --sheets-tab "Email Jobs"
```

Send yesterday's digest:

```bash
python3 bot.py --send-sheet-digest --digest-yesterday --sheets-url "YOUR_GOOGLE_SHEET_URL" --sheets-tab "Email Jobs"
```

Send a test email:

```bash
python3 bot.py --send-test-email --email-to you@example.com
```
