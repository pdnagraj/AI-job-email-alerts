# AI Job Email Alerts

Public repo name: `AI-job-email-alerts`

If you do not understand something, you can ask Claude, Codex, or whatever other vibe-coding tool you use to help you set this up in less than 10 minutes.

I hate looking for jobs, so I automated it.

This is a simple and free way to create your own system that emails you about jobs or internships.

This project helps you find jobs, score them, save them to Google Sheets, and email yourself a simple digest.

## What It Does

It does 4 small things:

1. looks for jobs
2. keeps the good ones
3. saves them to a Google Sheet
4. emails you the list

## Before You Start

You need:

- Python 3.12
- a Google Sheet
- a Google service account JSON file
- an email account that can send SMTP mail
- an Ollama API key if you want AI scoring

## Super Simple Setup

### 1. Download the project

```bash
git clone https://github.com/YOUR-USERNAME/AI-job-email-alerts.git
cd AI-job-email-alerts
```

### 2. Make a Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the packages

```bash
pip install -r requirements.txt
```

### 4. Add your Google key

Make a folder called `keys`.

Put your Google service account file here:

```text
keys/google-credentials.json
```

### 5. Fill in your profile notes

Open `docs/profile_notes.md`.

Replace the example text with your own:

- target roles
- cities
- keywords you like
- keywords you do not want

### 6. Make a Google Sheet

Create a Google Sheet and copy its URL.

The bot will use these columns:

- Company Name
- Date applied
- Role Name
- Location
- Job Application Link
- LinkedIn Link 1
- LinkedIn Link 2
- LinkedIn Link 3

### 7. Add your secrets

Copy the example file:

```bash
cp .env.example .env
```

Then put your real values inside `.env`:

```bash
RECRUITING_BOT_EMAIL_TO="you@example.com"
RECRUITING_BOT_EMAIL_FROM="you@example.com"
RECRUITING_BOT_SMTP_HOST="smtp.gmail.com"
RECRUITING_BOT_SMTP_PORT="587"
RECRUITING_BOT_SMTP_USERNAME="you@example.com"
RECRUITING_BOT_SMTP_PASSWORD="your-app-password"
RECRUITING_BOT_SMTP_USE_TLS="true"
OLLAMA_API_KEY="your-key"
```

## Run It

Search for jobs and save them:

```bash
python3 bot.py --max-jobs 12 --hours-old 24 --sheets-url "YOUR_GOOGLE_SHEET_URL"
```

Send a digest email:

```bash
python3 bot.py --send-sheet-digest --sheets-url "YOUR_GOOGLE_SHEET_URL"
```

Send a test email:

```bash
python3 bot.py --send-test-email --email-to you@example.com
```

## Make It Yours

If you want different jobs, edit `app/config.py`.

You can change:

- job titles
- cities
- filters
- scoring rules

## Put It On GitHub

1. Create a new repo called `AI-job-email-alerts`.
2. Push this code there.
3. Add your GitHub Actions secrets.
4. Keep it private or make it public if you want to share it.

More setup help is in `docs/cloud_setup.md`.

## Open Source

This repo is now set up to be shared publicly:

- personal resume removed
- personal profile replaced with a template
- private sheet link removed
- simple MIT license added
