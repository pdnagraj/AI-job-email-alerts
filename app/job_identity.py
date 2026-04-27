from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_QUERY_PARAMS = {
    "fbclid",
    "gh_src",
    "gclid",
    "mc_cid",
    "mc_eid",
    "trk",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
UNKNOWN_LOCATION_MARKERS = {
    "",
    "n/a",
    "na",
    "none",
    "not specified",
    "unknown",
    "unknown location",
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()


def normalize_key(value: Any) -> str:
    return normalize_text(value).casefold()


def normalize_location_key(value: Any) -> str:
    normalized = normalize_key(value)
    if normalized in UNKNOWN_LOCATION_MARKERS:
        return ""
    return normalized


def canonicalize_job_url(value: Any) -> str:
    raw_url = normalize_text(value)
    if not raw_url:
        return ""

    try:
        parsed = urlsplit(raw_url)
    except Exception:
        return raw_url.casefold().rstrip("/")

    if not parsed.scheme or not parsed.netloc:
        return raw_url.casefold().rstrip("/")

    netloc = parsed.netloc.casefold()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    path = parsed.path.rstrip("/") or parsed.path or "/"
    filtered_query_items = [
        (key.casefold(), normalize_text(item_value))
        for key, item_value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_QUERY_PARAMS
    ]
    filtered_query_items.sort()
    query = urlencode(filtered_query_items, doseq=True)

    return urlunsplit((parsed.scheme.casefold(), netloc, path, query, ""))


def build_job_identity_signatures(
    company_name: Any,
    role_name: Any,
    location: Any = "",
    job_application_link: Any = "",
) -> set[tuple[str, ...]]:
    company_key = normalize_key(company_name)
    role_key = normalize_key(role_name)
    location_key = normalize_location_key(location)
    url_key = canonicalize_job_url(job_application_link)
    signatures: set[tuple[str, ...]] = set()

    if url_key:
        signatures.add(("url", url_key))

    if company_key and role_key and location_key:
        signatures.add(("company-role-location", company_key, role_key, location_key))
    elif company_key and role_key and not url_key:
        signatures.add(("company-role", company_key, role_key))

    return signatures


def job_rows_match(
    company_name: Any,
    role_name: Any,
    location: Any,
    job_application_link: Any,
    other_company_name: Any,
    other_role_name: Any,
    other_location: Any,
    other_job_application_link: Any,
) -> bool:
    company_key = normalize_key(company_name)
    role_key = normalize_key(role_name)

    if not company_key or not role_key:
        return False

    if company_key != normalize_key(other_company_name):
        return False
    if role_key != normalize_key(other_role_name):
        return False

    url_key = canonicalize_job_url(job_application_link)
    other_url_key = canonicalize_job_url(other_job_application_link)
    if url_key and other_url_key and url_key == other_url_key:
        return True

    location_key = normalize_location_key(location)
    other_location_key = normalize_location_key(other_location)
    if location_key and other_location_key:
        return location_key == other_location_key

    if (location_key or other_location_key) and url_key and other_url_key:
        return False

    if not url_key or not other_url_key:
        return True

    return False
