from __future__ import annotations

from functools import lru_cache
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import (
    ALLOWED_TITLE_PATTERNS,
    ARCHIVED_SHEETS_TAB,
    BLOCKED_TITLE_PATTERNS,
    FIT_DESCRIPTION_NEGATIVE_KEYWORDS,
    FIT_DESCRIPTION_POSITIVE_KEYWORDS,
    FIT_PREFERRED_LOCATION_KEYWORDS,
    FIT_SCORE_MINIMUM,
    FIT_STRONG_TITLE_PATTERNS,
    JOBSPY_BIG_COMPANY_EMPLOYEE_MARKERS,
    JOBSPY_BLOCKED_COMPANY_KEYWORDS,
    JOBSPY_BLOCKED_RECRUITER_KEYWORDS,
    JOBSPY_COUNTRY_INDEED,
    JOBSPY_HOURS_OLD,
    JOBSPY_SITES,
    MAX_JOBS_PER_DAY,
    OLLAMA_APPROVED_MAX_PER_RUN,
    OLLAMA_MIN_FIT_SCORE,
    OLLAMA_SHORTLIST_SIZE,
    PROFILE_NOTES_FILE,
    SEARCH_TERMS,
    TARGET_LOCATIONS,
)
from .google_sheets import append_contacted_job_from_values_if_new, get_jobs_for_today
from .job_identity import build_job_identity_signatures
from .ollama_fit import ollama_is_configured, split_jobs_with_ollama

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from jobspy import scrape_jobs
except ImportError:
    scrape_jobs = None


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


@lru_cache(maxsize=1)
def load_profile_preferences(profile_notes_path: str = str(PROFILE_NOTES_FILE)) -> dict[str, list[str]]:
    preferences: dict[str, list[str]] = {}
    current_section = ""
    path = Path(profile_notes_path)

    if not path.exists():
        return preferences

    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.endswith(":"):
            current_section = line[:-1].strip().lower()
            preferences.setdefault(current_section, [])
            continue
        if line.startswith("- ") and current_section:
            preferences.setdefault(current_section, []).append(normalize_text(line[2:]).lower())

    return preferences


def is_allowed_title(title: str) -> bool:
    normalized = normalize_text(title).lower()
    if not normalized:
        return False
    if any(pattern in normalized for pattern in BLOCKED_TITLE_PATTERNS):
        return False
    return any(pattern in normalized for pattern in ALLOWED_TITLE_PATTERNS)


def format_location(row: dict[str, Any]) -> str:
    location = normalize_text(row.get("location"))
    if location:
        return location

    city = normalize_text(row.get("city"))
    state = normalize_text(row.get("state"))
    country = normalize_text(row.get("country"))
    parts = [part for part in [city, state, country] if part]
    return ", ".join(parts)


def parse_posted_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None

    if pd is not None:
        try:
            parsed = pd.to_datetime(value, utc=False, errors="coerce")
            if pd.isna(parsed):
                return None
            if hasattr(parsed, "to_pydatetime"):
                return parsed.to_pydatetime()
        except Exception:
            return None

    if isinstance(value, datetime):
        return value

    return None


def format_posted_at(value: Any) -> str:
    posted = parse_posted_datetime(value)
    if posted is None:
        return normalize_text(value)
    return posted.strftime("%Y-%m-%d %H:%M")


def was_posted_within_hours(value: Any, hours_old: int) -> bool:
    posted = parse_posted_datetime(value)
    if posted is None:
        return True

    if posted.tzinfo is not None:
        now = datetime.now(posted.tzinfo)
    else:
        now = datetime.now()

    return posted >= now - timedelta(hours=hours_old)


def dataframe_to_records(dataframe) -> list[dict[str, Any]]:
    if hasattr(dataframe, "to_dict"):
        return list(dataframe.to_dict(orient="records"))
    return []


def normalize_jobspy_job(row: dict[str, Any]) -> dict[str, str] | None:
    title = normalize_text(row.get("title"))
    company = normalize_text(row.get("company"))
    link = normalize_text(row.get("job_url"))
    location = format_location(row)
    source = normalize_text(row.get("site")).lower()

    if not title or not company or not link:
        return None

    return {
        "title": title,
        "company": company,
        "location": location or "Unknown location",
        "link": link,
        "company_link": normalize_text(row.get("company_url")),
        "source": source or "jobspy",
        "posted_at": format_posted_at(row.get("date_posted")),
        "company_num_employees": normalize_text(row.get("company_num_employees")),
        "description": normalize_text(row.get("description")),
    }


def is_excluded_company(row: dict[str, Any]) -> bool:
    company_name = normalize_text(row.get("company")).lower()
    employee_label = normalize_text(row.get("company_num_employees")).lower()

    if any(keyword in company_name for keyword in JOBSPY_BLOCKED_COMPANY_KEYWORDS):
        return True

    if any(keyword in company_name for keyword in JOBSPY_BLOCKED_RECRUITER_KEYWORDS):
        return True

    if any(marker.lower() in employee_label for marker in JOBSPY_BIG_COMPANY_EMPLOYEE_MARKERS):
        return True

    return False


def score_job_fit(job: dict[str, str]) -> int:
    score = 0
    title = normalize_text(job.get("title")).lower()
    location = normalize_text(job.get("location")).lower()
    description = normalize_text(job.get("description")).lower()
    company = normalize_text(job.get("company")).lower()
    company_size = normalize_text(job.get("company_num_employees")).lower()
    full_text = " ".join([title, company, location, description]).strip()
    profile_preferences = load_profile_preferences()
    target_roles = profile_preferences.get("target roles", [])
    preferred_locations = profile_preferences.get("preferred locations", [])
    strong_fit_keywords = profile_preferences.get("strong fit keywords", [])
    avoid_keywords = profile_preferences.get("avoid", [])
    preferred_company_types = profile_preferences.get("preferred company type", [])
    preferred_industries = profile_preferences.get("preferred industries", [])

    if any(pattern in title for pattern in FIT_STRONG_TITLE_PATTERNS):
        score += 3

    if any(role in title for role in target_roles):
        score += 4

    if "associate" in title or "intern" in title or "analyst" in title:
        score += 2

    if any(keyword in location for keyword in preferred_locations or FIT_PREFERRED_LOCATION_KEYWORDS):
        score += 2

    if any(keyword in full_text for keyword in strong_fit_keywords):
        score += 3
    elif any(keyword in description for keyword in FIT_DESCRIPTION_POSITIVE_KEYWORDS):
        score += 2

    if company_size:
        if any(marker.lower() in company_size for marker in JOBSPY_BIG_COMPANY_EMPLOYEE_MARKERS):
            score -= 3
        else:
            score += 1
            if any(keyword in full_text for keyword in preferred_company_types):
                score += 1

    if "remote" in location or "remote" in description:
        score += 1

    if any(keyword in full_text for keyword in preferred_industries):
        score += 2

    if any(keyword in full_text for keyword in avoid_keywords):
        score -= 4

    if any(keyword in description for keyword in FIT_DESCRIPTION_NEGATIVE_KEYWORDS):
        score -= 3

    return score


def search_jobspy_jobs(
    site_names: list[str] | None = None,
    search_terms: list[str] | None = None,
    locations: list[str] | None = None,
    results_per_query: int = 10,
    hours_old: int = JOBSPY_HOURS_OLD,
    country_indeed: str = JOBSPY_COUNTRY_INDEED,
    exclude_big_companies: bool = False,
    minimum_fit_score: int = FIT_SCORE_MINIMUM,
) -> list[dict[str, str]]:
    if scrape_jobs is None:
        raise RuntimeError("JobSpy is not installed. Run: pip install -U python-jobspy")

    sites = site_names or JOBSPY_SITES
    query_terms = search_terms or SEARCH_TERMS
    target_locations = locations or TARGET_LOCATIONS

    collected_jobs: list[dict[str, str]] = []
    seen_keys: set[tuple[str, ...]] = set()

    for search_term in query_terms:
        for location in target_locations:
            log(f"Searching JobSpy for '{search_term}' in {location} on {', '.join(sites)}")
            dataframe = scrape_jobs(
                site_name=sites,
                search_term=search_term,
                google_search_term=f"{search_term} jobs near {location} since yesterday",
                location=location,
                results_wanted=results_per_query,
                hours_old=hours_old,
                country_indeed=country_indeed,
                description_format="markdown",
                linkedin_fetch_description="linkedin" in sites,
                verbose=0,
            )

            for raw_job in dataframe_to_records(dataframe):
                if not is_allowed_title(raw_job.get("title")):
                    continue
                if not was_posted_within_hours(raw_job.get("date_posted"), hours_old):
                    continue
                if exclude_big_companies and is_excluded_company(raw_job):
                    continue

                normalized = normalize_jobspy_job(raw_job)
                if normalized is None:
                    continue

                fit_score = score_job_fit(normalized)
                if fit_score < minimum_fit_score:
                    continue
                normalized["fit_score"] = str(fit_score)

                job_signatures = build_job_identity_signatures(
                    company_name=normalized["company"],
                    role_name=normalized["title"],
                    location=normalized["location"],
                    job_application_link=normalized["link"],
                )
                if any(signature in seen_keys for signature in job_signatures):
                    continue

                seen_keys.update(job_signatures)
                collected_jobs.append(normalized)
                log(
                    f"Extracted JobSpy job: {normalized['title']} at {normalized['company']} "
                    f"in {normalized['location']} via {normalized['source']} (fit {fit_score})"
                )

    collected_jobs.sort(
        key=lambda job: (
            -int(job.get("fit_score", "0") or 0),
            job.get("posted_at") == "",
            job.get("posted_at", ""),
            job["company"].lower(),
        ),
    )
    return collected_jobs


def print_jobspy_jobs(job_list: list[dict[str, str]]) -> None:
    if not job_list:
        log("No JobSpy jobs found.")
        return

    print("\nJobSpy job results:")
    for index, job in enumerate(job_list, start=1):
        ai_fit = job.get("ollama_fit_score")
        ai_fit_label = f" | ai {ai_fit}" if ai_fit else ""
        print(
            f"{index}. {job['title']} | {job['company']} | {job['location']} | "
            f"{job.get('source', 'jobspy')} | fit {job.get('fit_score', '')}{ai_fit_label} | "
            f"{job.get('posted_at', '')} | {job['link']}"
        )


def save_jobspy_jobs_to_google_sheets(
    job_list: list[dict[str, str]],
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str = "Jobs",
    max_jobs_per_day: int | None = None,
) -> None:
    if not job_list:
        log("No JobSpy jobs to save to Google Sheets.")
        return

    remaining_daily_slots = None
    if max_jobs_per_day is not None:
        remaining_daily_slots = get_remaining_daily_slots(
            credentials_path=credentials_path,
            spreadsheet_ref=spreadsheet_ref,
            worksheet_name=worksheet_name,
            max_jobs_per_day=max_jobs_per_day,
        )
        if remaining_daily_slots <= 0:
            log(f"Daily cap already reached for {worksheet_name}. No new rows will be added.")
            return

    for job in job_list:
        if remaining_daily_slots is not None and remaining_daily_slots <= 0:
            log(f"Stopped saving jobs because the daily cap for {worksheet_name} has been reached.")
            break

        try:
            was_added = append_contacted_job_from_values_if_new(
                credentials_path=credentials_path,
                spreadsheet_ref=spreadsheet_ref,
                worksheet_name=worksheet_name,
                company_name=job["company"],
                role_name=job["title"],
                location=job["location"],
                job_application_link=job["link"],
            )
            if was_added:
                log(f"Saved JobSpy job to Google Sheets: {job['title']} at {job['company']}")
                if remaining_daily_slots is not None:
                    remaining_daily_slots -= 1
            else:
                log(f"Skipped duplicate JobSpy job in Google Sheets: {job['title']} at {job['company']}")
        except Exception as exc:
            log(f"Failed to save JobSpy job for {job['company']}: {exc}")


def save_partitioned_jobspy_jobs_to_google_sheets(
    approved_jobs: list[dict[str, str]],
    archived_jobs: list[dict[str, str]],
    credentials_path: str,
    spreadsheet_ref: str,
    approved_worksheet_name: str,
    archived_worksheet_name: str,
    max_jobs_per_day: int | None = None,
) -> None:
    if approved_jobs:
        save_jobspy_jobs_to_google_sheets(
            job_list=approved_jobs,
            credentials_path=credentials_path,
            spreadsheet_ref=spreadsheet_ref,
            worksheet_name=approved_worksheet_name,
            max_jobs_per_day=max_jobs_per_day,
        )

    if archived_jobs:
        save_jobspy_jobs_to_google_sheets(
            job_list=archived_jobs,
            credentials_path=credentials_path,
            spreadsheet_ref=spreadsheet_ref,
            worksheet_name=archived_worksheet_name,
        )


def get_remaining_daily_slots(
    credentials_path: str,
    spreadsheet_ref: str,
    worksheet_name: str,
    max_jobs_per_day: int,
) -> int:
    if max_jobs_per_day <= 0:
        return 0

    _, todays_jobs = get_jobs_for_today(
        credentials_path=credentials_path,
        spreadsheet_ref=spreadsheet_ref,
        worksheet_name=worksheet_name,
    )
    return max(0, max_jobs_per_day - len(todays_jobs))


def run_jobspy_job_search(
    max_results: int = 8,
    max_jobs_per_day: int = MAX_JOBS_PER_DAY,
    save_to_sheets: bool = False,
    sheets_credentials_path: str = "",
    sheets_spreadsheet_ref: str = "",
    sheets_tab_name: str = "Email Jobs",
    archived_sheets_tab_name: str = ARCHIVED_SHEETS_TAB,
    site_names: list[str] | None = None,
    hours_old: int = JOBSPY_HOURS_OLD,
    country_indeed: str = JOBSPY_COUNTRY_INDEED,
    exclude_big_companies: bool = False,
) -> list[dict[str, str]]:
    remaining_daily_slots = max_jobs_per_day
    if save_to_sheets:
        remaining_daily_slots = get_remaining_daily_slots(
            credentials_path=sheets_credentials_path,
            spreadsheet_ref=sheets_spreadsheet_ref,
            worksheet_name=sheets_tab_name,
            max_jobs_per_day=max_jobs_per_day,
        )
        if remaining_daily_slots <= 0:
            if max_jobs_per_day <= 0:
                log(f"Daily cap for {sheets_tab_name} is set to 0. Skipping scrape and sheet updates.")
            else:
                log(
                    f"Daily cap reached for {sheets_tab_name}. "
                    f"Skipping scrape because today already has {max_jobs_per_day} jobs."
                )
            return []

    jobs = search_jobspy_jobs(
        site_names=site_names,
        results_per_query=max(max_results, 20),
        hours_old=hours_old,
        country_indeed=country_indeed,
        exclude_big_companies=exclude_big_companies,
    )
    approved_jobs = jobs[:max_results]
    archived_jobs: list[dict[str, str]] = []

    if ollama_is_configured():
        approved_jobs, archived_jobs = split_jobs_with_ollama(
            job_list=jobs,
            shortlist_size=max(max_results, OLLAMA_SHORTLIST_SIZE),
            minimum_fit_score=OLLAMA_MIN_FIT_SCORE,
        )
        approved_jobs = approved_jobs[: min(max_results, OLLAMA_APPROVED_MAX_PER_RUN, remaining_daily_slots)]
    else:
        approved_jobs = approved_jobs[: min(max_results, OLLAMA_APPROVED_MAX_PER_RUN, remaining_daily_slots)]

    print_jobspy_jobs(approved_jobs)
    if archived_jobs:
        log(f"Archived {len(archived_jobs)} jobs rejected by Ollama.")

    if save_to_sheets:
        save_partitioned_jobspy_jobs_to_google_sheets(
            approved_jobs=approved_jobs,
            archived_jobs=archived_jobs,
            credentials_path=sheets_credentials_path,
            spreadsheet_ref=sheets_spreadsheet_ref,
            approved_worksheet_name=sheets_tab_name,
            archived_worksheet_name=archived_sheets_tab_name,
            max_jobs_per_day=max_jobs_per_day,
        )

    return approved_jobs
