from __future__ import annotations

import argparse
import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from app.config import (
    ARCHIVED_SHEETS_TAB,
    DEFAULT_SHEETS_CREDENTIALS,
    DEFAULT_SHEETS_TAB,
    DEFAULT_SHEETS_URL,
    JOBSPY_COUNTRY_INDEED,
    JOBSPY_HOURS_OLD,
    JOBSPY_SITES,
    MAX_JOBS_PER_DAY,
)
from app.email_jobs import send_digest_email, send_job_summary_email, send_test_email
from app.google_sheets import get_jobs_for_applied_date, get_jobs_for_day_offset, get_jobs_for_today
from app.jobspy_jobs import run_jobspy_job_search


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect jobs, score them, save them, and email a digest.")
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=MAX_JOBS_PER_DAY,
        help=f"Maximum number of jobs to collect. Default: {MAX_JOBS_PER_DAY}",
    )
    parser.add_argument(
        "--max-jobs-per-day",
        type=int,
        default=MAX_JOBS_PER_DAY,
        help=f"Stop saving approved jobs after this many have been added for the day. Default: {MAX_JOBS_PER_DAY}",
    )
    parser.add_argument(
        "--skip-sheets-save",
        action="store_true",
        help="Skip saving found jobs to Google Sheets",
    )
    parser.add_argument(
        "--sheets-credentials",
        default=str(DEFAULT_SHEETS_CREDENTIALS),
        help=f"Path to the Google service account JSON file. Default: {DEFAULT_SHEETS_CREDENTIALS}",
    )
    parser.add_argument(
        "--sheets-url",
        default=os.getenv("GOOGLE_SHEETS_URL", os.getenv("GOOGLE_SHEET_NAME", DEFAULT_SHEETS_URL)),
        help="Google Sheets URL or spreadsheet ID for saving found jobs",
    )
    parser.add_argument(
        "--sheets-tab",
        default=os.getenv("GOOGLE_SHEET_TAB", DEFAULT_SHEETS_TAB),
        help=f"Worksheet/tab name to append to. Default: {DEFAULT_SHEETS_TAB}",
    )
    parser.add_argument(
        "--archive-tab",
        default=os.getenv("GOOGLE_ARCHIVE_SHEET_TAB", ARCHIVED_SHEETS_TAB),
        help=f"Worksheet/tab name for Ollama-rejected jobs. Default: {ARCHIVED_SHEETS_TAB}",
    )
    parser.add_argument(
        "--jobspy-site",
        action="append",
        default=[],
        help="JobSpy source to search. Repeat for multiple values.",
    )
    parser.add_argument(
        "--hours-old",
        type=int,
        default=JOBSPY_HOURS_OLD,
        help=f"Only keep jobs within this many hours when the source supports it. Default: {JOBSPY_HOURS_OLD}",
    )
    parser.add_argument(
        "--country-indeed",
        default=JOBSPY_COUNTRY_INDEED,
        help=f"Country used by Indeed/Glassdoor in JobSpy. Default: {JOBSPY_COUNTRY_INDEED}",
    )
    parser.add_argument(
        "--exclude-big-companies",
        action="store_true",
        help="Exclude obvious large companies and recruiting middlemen from JobSpy results",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send an email summary after sourcing jobs",
    )
    parser.add_argument(
        "--email-to",
        default="",
        help="Override the recipient for the email summary",
    )
    parser.add_argument(
        "--send-sheet-digest",
        action="store_true",
        help="Send an email digest from jobs already saved in Google Sheets instead of scraping",
    )
    parser.add_argument(
        "--digest-max-jobs",
        type=int,
        default=10,
        help="Maximum number of jobs to include in the digest email. Default: 10",
    )
    parser.add_argument(
        "--digest-date",
        default="",
        help="Digest date in MM/DD/YYYY format. If omitted, use today's date in America/New_York.",
    )
    parser.add_argument(
        "--digest-yesterday",
        action="store_true",
        help="Send the digest for yesterday's sheet rows in America/New_York",
    )
    parser.add_argument(
        "--send-test-email",
        action="store_true",
        help="Send a plain test email using the configured SMTP settings",
    )
    return parser.parse_args()


def main() -> None:
    if load_dotenv is not None:
        load_dotenv()

    args = parse_args()

    if args.send_test_email:
        was_sent = send_test_email(
            recipient_override=args.email_to,
            subject="AI Job Email Alerts Test Email",
            body="This is a test email from AI Job Email Alerts.",
        )
        if was_sent:
            print("Sent test email.")
        else:
            print(
                "Test email skipped because SMTP settings are missing. "
                "Set RECRUITING_BOT_SMTP_HOST, RECRUITING_BOT_SMTP_PORT, "
                "RECRUITING_BOT_SMTP_USERNAME, RECRUITING_BOT_SMTP_PASSWORD, "
                "RECRUITING_BOT_EMAIL_FROM, and RECRUITING_BOT_EMAIL_TO or pass --email-to."
            )
        return

    if args.send_sheet_digest:
        if args.digest_date:
            digest_label = args.digest_date
            jobs = get_jobs_for_applied_date(
                credentials_path=args.sheets_credentials,
                spreadsheet_ref=args.sheets_url,
                worksheet_name=args.sheets_tab,
                applied_date=digest_label,
            )
        elif args.digest_yesterday:
            digest_label, jobs = get_jobs_for_day_offset(
                credentials_path=args.sheets_credentials,
                spreadsheet_ref=args.sheets_url,
                worksheet_name=args.sheets_tab,
                days_offset=-1,
            )
        else:
            digest_label, jobs = get_jobs_for_today(
                credentials_path=args.sheets_credentials,
                spreadsheet_ref=args.sheets_url,
                worksheet_name=args.sheets_tab,
            )

        jobs = list(reversed(jobs))[: args.digest_max_jobs]

        was_sent = send_digest_email(
            job_list=jobs,
            digest_label=digest_label,
            source_label="AI Job Email Alerts Digest",
            recipient_override=args.email_to,
        )
        if was_sent:
            print(f"Sent sheet digest email for {digest_label}.")
        else:
            print(
                "Digest email skipped because SMTP settings are missing. "
                "Set RECRUITING_BOT_SMTP_HOST, RECRUITING_BOT_SMTP_PORT, "
                "RECRUITING_BOT_SMTP_USERNAME, RECRUITING_BOT_SMTP_PASSWORD, "
                "and RECRUITING_BOT_EMAIL_TO."
            )
        return

    jobs = run_jobspy_job_search(
        max_results=args.max_jobs,
        max_jobs_per_day=args.max_jobs_per_day,
        save_to_sheets=not args.skip_sheets_save,
        sheets_credentials_path=args.sheets_credentials,
        sheets_spreadsheet_ref=args.sheets_url,
        sheets_tab_name=args.sheets_tab,
        archived_sheets_tab_name=args.archive_tab,
        site_names=args.jobspy_site or JOBSPY_SITES,
        hours_old=args.hours_old,
        country_indeed=args.country_indeed,
        exclude_big_companies=args.exclude_big_companies,
    )

    if args.send_email:
        was_sent = send_job_summary_email(
            job_list=jobs,
            source_label="JobSpy",
            recipient_override=args.email_to,
        )
        if was_sent:
            print("Sent JobSpy summary email.")
        else:
            print(
                "Email summary skipped because SMTP settings are missing. "
                "Set RECRUITING_BOT_SMTP_HOST, RECRUITING_BOT_SMTP_PORT, "
                "RECRUITING_BOT_SMTP_USERNAME, RECRUITING_BOT_SMTP_PASSWORD, "
                "and RECRUITING_BOT_EMAIL_TO."
            )


if __name__ == "__main__":
    main()
