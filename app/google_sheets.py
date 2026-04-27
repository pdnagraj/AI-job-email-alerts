from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .config import LOCAL_TIMEZONE
from .job_identity import job_rows_match

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("Missing dependencies: gspread and google-auth")
    print("Install them with: pip install gspread google-auth")
    sys.exit(1)


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
# Match the sheet structure you showed so new rows line up with your tracker.
DEFAULT_HEADERS = [
    "Company Name",
    "Date applied",
    "Role Name",
    "Location",
    "Job Application Link",
    "LinkedIn Link 1",
    "LinkedIn Link 2",
    "LinkedIn Link 3",
]


@dataclass
class ContactedJobRow:
    # Small data container so the append logic stays predictable and easy to reuse.
    company_name: str
    role_name: str
    location: str = ""
    linkedin_link_1: str = ""
    linkedin_link_2: str = ""
    linkedin_link_3: str = ""
    job_application_link: str = ""
    date_applied: str = ""

    def to_row(self) -> list[str]:
        formatted_date = self.date_applied or get_current_date_label()
        return [
            self.company_name,
            formatted_date,
            self.role_name,
            self.location,
            self.job_application_link,
            self.linkedin_link_1,
            self.linkedin_link_2,
            self.linkedin_link_3,
        ]


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def extract_spreadsheet_id(sheet_ref: str) -> str:
    if not sheet_ref:
        return ""

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_ref)
    if match:
        return match.group(1)

    return sheet_ref.strip()


def get_current_date_label(timezone_name: str = LOCAL_TIMEZONE) -> str:
    try:
        return datetime.now(ZoneInfo(timezone_name)).strftime("%m/%d/%Y")
    except Exception:
        return date.today().strftime("%m/%d/%Y")


# Build an authenticated Sheets client from a service account JSON key.
def build_client(credentials_path: str):
    if not credentials_path:
        raise ValueError("Missing credentials path. Set GOOGLE_SHEETS_CREDENTIALS or pass --credentials.")

    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


# Open the exact worksheet that will store your contacted-job rows.
def open_worksheet(credentials_path: str, spreadsheet_ref: str, worksheet_name: str):
    if not spreadsheet_ref:
        raise ValueError("Missing spreadsheet reference. Set GOOGLE_SHEET_NAME or pass --sheet.")
    if not worksheet_name:
        raise ValueError("Missing worksheet name. Set GOOGLE_SHEET_TAB or pass --tab.")

    client = build_client(credentials_path)
    spreadsheet = client.open_by_key(extract_spreadsheet_id(spreadsheet_ref))
    return spreadsheet.worksheet(worksheet_name)


# Only write headers automatically when the sheet is empty to avoid overwriting your layout.
def ensure_headers(worksheet, headers: list[str] | None = None) -> None:
    expected_headers = headers or DEFAULT_HEADERS
    existing_headers = worksheet.row_values(1)

    if existing_headers[: len(expected_headers)] == expected_headers:
        return

    if any(cell.strip() for cell in existing_headers):
        return

    worksheet.update("A1:H1", [expected_headers])


# Append one structured job-contact row to the sheet.
def append_contacted_job(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    row: ContactedJobRow,
) -> None:
    worksheet = open_worksheet(credentials_path, spreadsheet_ref, worksheet_name)
    ensure_headers(worksheet)
    worksheet.append_row(row.to_row(), value_input_option="USER_ENTERED")


def has_matching_job_row(
    worksheet,
    company_name: str,
    role_name: str,
    location: str = "",
    job_application_link: str = "",
) -> bool:
    records = worksheet.get_all_values()

    for row in records[1:]:
        row_company = row[0].strip() if len(row) > 0 else ""
        row_role = row[2].strip() if len(row) > 2 else ""
        row_location = row[3].strip() if len(row) > 3 else ""
        row_link = row[4].strip() if len(row) > 4 else ""

        if job_rows_match(
            company_name=company_name,
            role_name=role_name,
            location=location,
            job_application_link=job_application_link,
            other_company_name=row_company,
            other_role_name=row_role,
            other_location=row_location,
            other_job_application_link=row_link,
        ):
            return True

    return False


def append_contacted_job_if_new(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    row: ContactedJobRow,
) -> bool:
    worksheet = open_worksheet(credentials_path, spreadsheet_ref, worksheet_name)
    ensure_headers(worksheet)

    if has_matching_job_row(
        worksheet,
        company_name=row.company_name,
        role_name=row.role_name,
        location=row.location,
        job_application_link=row.job_application_link,
    ):
        return False

    worksheet.append_row(row.to_row(), value_input_option="USER_ENTERED")
    return True


def get_all_job_rows(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
) -> list[dict[str, str]]:
    worksheet = open_worksheet(credentials_path, spreadsheet_ref, worksheet_name)
    ensure_headers(worksheet)
    normalized_records: list[dict[str, str]] = []
    records = worksheet.get_all_values()

    for row in records[1:]:
        normalized_records.append(
            {
                "company": row[0].strip() if len(row) > 0 else "",
                "date_applied": row[1].strip() if len(row) > 1 else "",
                "title": row[2].strip() if len(row) > 2 else "",
                "location": row[3].strip() if len(row) > 3 else "",
                "link": row[4].strip() if len(row) > 4 else "",
            }
        )

    return normalized_records


def get_jobs_for_applied_date(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    applied_date: str,
) -> list[dict[str, str]]:
    matching_rows: list[dict[str, str]] = []

    for row in get_all_job_rows(credentials_path, spreadsheet_ref, worksheet_name):
        if row["date_applied"] != applied_date:
            continue
        if not row["company"] or not row["title"] or not row["link"]:
            continue
        matching_rows.append(row)

    return matching_rows


def get_jobs_for_today(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    timezone_name: str = LOCAL_TIMEZONE,
) -> tuple[str, list[dict[str, str]]]:
    today_label = get_current_date_label(timezone_name)
    return today_label, get_jobs_for_applied_date(
        credentials_path=credentials_path,
        spreadsheet_ref=spreadsheet_ref,
        worksheet_name=worksheet_name,
        applied_date=today_label,
    )


def get_jobs_for_day_offset(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    days_offset: int,
    timezone_name: str = LOCAL_TIMEZONE,
) -> tuple[str, list[dict[str, str]]]:
    try:
        target_date = datetime.now(ZoneInfo(timezone_name)).date()
    except Exception:
        target_date = date.today()

    target_label = (target_date + timedelta(days=days_offset)).strftime("%m/%d/%Y")
    return target_label, get_jobs_for_applied_date(
        credentials_path=credentials_path,
        spreadsheet_ref=spreadsheet_ref,
        worksheet_name=worksheet_name,
        applied_date=target_label,
    )


def find_matching_row(worksheet, company_name: str, role_name: str = "") -> int | None:
    records = worksheet.get_all_values()

    for row_index, row in enumerate(records[1:], start=2):
        row_company = row[0].strip() if len(row) > 0 else ""
        row_role = row[2].strip() if len(row) > 2 else ""

        if row_company != company_name:
            continue

        if role_name and row_role != role_name:
            continue

        return row_index

    return None


def update_linkedin_link_for_job(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    company_name: str,
    role_name: str,
    linkedin_url: str,
) -> bool:
    worksheet = open_worksheet(credentials_path, spreadsheet_ref, worksheet_name)
    row_index = find_matching_row(worksheet, company_name, role_name)

    if row_index is None:
        return False

    for column_index in (6, 7, 8):
        current_value = worksheet.cell(row_index, column_index).value or ""
        if not current_value.strip():
            worksheet.update_cell(row_index, column_index, linkedin_url)
            return True

    return False


# Convenience wrapper so callers can pass plain strings without constructing the dataclass.
def append_contacted_job_from_values(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    company_name: str,
    role_name: str,
    location: str = "",
    linkedin_link_1: str = "",
    linkedin_link_2: str = "",
    linkedin_link_3: str = "",
    job_application_link: str = "",
    date_applied: str = "",
) -> None:
    row = ContactedJobRow(
        company_name=company_name,
        date_applied=date_applied,
        role_name=role_name,
        location=location,
        linkedin_link_1=linkedin_link_1,
        linkedin_link_2=linkedin_link_2,
        linkedin_link_3=linkedin_link_3,
        job_application_link=job_application_link,
    )
    append_contacted_job(credentials_path, spreadsheet_ref, worksheet_name, row)


def append_contacted_job_from_values_if_new(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    company_name: str,
    role_name: str,
    location: str = "",
    linkedin_link_1: str = "",
    linkedin_link_2: str = "",
    linkedin_link_3: str = "",
    job_application_link: str = "",
    date_applied: str = "",
) -> bool:
    row = ContactedJobRow(
        company_name=company_name,
        date_applied=date_applied,
        role_name=role_name,
        location=location,
        linkedin_link_1=linkedin_link_1,
        linkedin_link_2=linkedin_link_2,
        linkedin_link_3=linkedin_link_3,
        job_application_link=job_application_link,
    )
    return append_contacted_job_if_new(credentials_path, spreadsheet_ref, worksheet_name, row)


# Support both CLI flags and environment variables for simple local use.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Append contacted jobs to a Google Sheet")
    parser.add_argument("--credentials", default=get_env("GOOGLE_SHEETS_CREDENTIALS"))
    parser.add_argument("--sheet", default=get_env("GOOGLE_SHEET_NAME"))
    parser.add_argument("--tab", default=get_env("GOOGLE_SHEET_TAB", "Jobs"))
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--location", default="")
    parser.add_argument("--linkedin-1", default="")
    parser.add_argument("--linkedin-2", default="")
    parser.add_argument("--linkedin-3", default="")
    parser.add_argument("--job-link", required=True)
    parser.add_argument("--date", default="")
    return parser.parse_args()


def main() -> None:
    # CLI entrypoint for testing the sheet connection independently of the LinkedIn bot.
    args = parse_args()

    try:
        append_contacted_job_from_values(
            credentials_path=args.credentials,
            spreadsheet_ref=args.sheet,
            worksheet_name=args.tab,
            company_name=args.company,
            role_name=args.role,
            location=args.location,
            linkedin_link_1=args.linkedin_1,
            linkedin_link_2=args.linkedin_2,
            linkedin_link_3=args.linkedin_3,
            job_application_link=args.job_link,
            date_applied=args.date,
        )
        print("Appended row to Google Sheets successfully.")
    except Exception as exc:
        print(f"Failed to append row: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
