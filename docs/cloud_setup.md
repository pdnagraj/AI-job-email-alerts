# Cloud Setup

This project already includes GitHub Actions so it can run without your laptop being open.

Included workflows:

- `.github/workflows/hourly-jobspy.yml`
  collects fresh jobs every 2 hours
- `.github/workflows/nightly-digest.yml`
  sends one digest email each morning

## Secrets To Add In GitHub

Open your repo, then go to `Settings -> Secrets and variables -> Actions`.

Add these secrets:

- `GOOGLE_CREDENTIALS_JSON`
- `GOOGLE_SHEETS_URL`
- `RECRUITING_BOT_EMAIL_TO`
- `RECRUITING_BOT_EMAIL_FROM`
- `RECRUITING_BOT_SMTP_HOST`
- `RECRUITING_BOT_SMTP_PORT`
- `RECRUITING_BOT_SMTP_USERNAME`
- `RECRUITING_BOT_SMTP_PASSWORD`

Optional:

- `RECRUITING_BOT_SMTP_USE_TLS`
  use `true` for most email providers
- `OLLAMA_API_KEY`
  only needed if you want AI scoring

## Gmail Example

If you use Gmail:

- host: `smtp.gmail.com`
- port: `587`
- username: your Gmail address
- password: a Google app password

## Local Test Commands

Collect jobs:

```bash
python3 bot.py --max-jobs 12 --max-jobs-per-day 8 --hours-old 24 --sheets-url "YOUR_GOOGLE_SHEET_URL" --sheets-tab "Email Jobs"
```

Send a digest for today:

```bash
python3 bot.py --send-sheet-digest --sheets-url "YOUR_GOOGLE_SHEET_URL" --sheets-tab "Email Jobs"
```

Send a digest for yesterday:

```bash
python3 bot.py --send-sheet-digest --digest-yesterday --sheets-url "YOUR_GOOGLE_SHEET_URL" --sheets-tab "Email Jobs"
```

Send a plain test email:

```bash
python3 bot.py --send-test-email --email-to you@example.com
```
