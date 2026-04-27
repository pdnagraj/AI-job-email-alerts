from __future__ import annotations

from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
LOCAL_TIMEZONE = "America/New_York"
PROFILE_NOTES_FILE = PROJECT_ROOT / "docs" / "profile_notes.md"
DEFAULT_SHEETS_CREDENTIALS = PROJECT_ROOT / "keys" / "google-credentials.json"
OLLAMA_BASE_URL = "https://ollama.com"
OLLAMA_MODEL = "gemma3:4b-cloud"
OLLAMA_SHORTLIST_SIZE = 12
OLLAMA_MIN_FIT_SCORE = 9
OLLAMA_APPROVED_MAX_PER_RUN = 2
DEFAULT_SHEETS_URL = ""
DEFAULT_SHEETS_TAB = "Jobs"
ARCHIVED_SHEETS_TAB = "Archived Jobs"
JOBSPY_SITES = [
    "linkedin",
    "google",
    "indeed",
]
JOBSPY_HOURS_OLD = 24
JOBSPY_COUNTRY_INDEED = "USA"
JOBSPY_BIG_COMPANY_EMPLOYEE_MARKERS = [
    "1001 to 5,000",
    "5001 to 10,000",
    "10,000+",
]
JOBSPY_BLOCKED_COMPANY_KEYWORDS = []
JOBSPY_BLOCKED_RECRUITER_KEYWORDS = [
    "teksystems",
    "optomi",
    "motion recruitment",
    "recruit",
    "staffing",
    "consulting",
    "consultancy",
]
FIT_SCORE_MINIMUM = 4
FIT_DESCRIPTION_POSITIVE_KEYWORDS = [
    "mba",
    "new grad",
    "early career",
    "0-2 years",
    "0-3 years",
    "1-3 years",
    "consumer",
    "b2c",
    "growth",
    "experimentation",
    "analytics",
    "platform",
    "roadmap",
    "product strategy",
]
FIT_DESCRIPTION_NEGATIVE_KEYWORDS = [
    "7+ years",
    "8+ years",
    "10+ years",
    "staff",
    "principal",
    "director",
    "vp",
    "vice president",
    "quota",
    "sales",
]
FIT_PREFERRED_LOCATION_KEYWORDS = []
SEARCH_TERMS = [
    "Associate Product Manager",
    "Product Manager",
    "Product Strategy",
    "Product Manager Intern",
    "MBA Product Manager",
]
TARGET_LOCATIONS = [
    "Boston, Massachusetts, United States",
    "New York, New York, United States",
    "San Francisco, California, United States",
]
MAX_JOBS_PER_DAY = 8
ALLOWED_TITLE_PATTERNS = [
    "associate product manager",
    "product manager",
    "product strategy",
    "product management",
    "growth product manager",
    "product operations",
    "product analyst",
]
BLOCKED_TITLE_PATTERNS = [
    "senior",
    "sr.",
    "staff",
    "principal",
    "director",
    "head of",
    "vice president",
    "vp ",
    "lead ",
    "group product manager",
    "chief ",
    "technical product manager",
    "security product manager",
    "internal systems",
    "founding product manager",
    "clinical product manager",
    "manager, product management",
]
FIT_STRONG_TITLE_PATTERNS = [
    "associate product manager",
    "product manager intern",
    "product strategy",
    "product manager",
]
