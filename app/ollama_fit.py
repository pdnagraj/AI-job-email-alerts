from __future__ import annotations

import json
import os
from pathlib import Path
from openai import OpenAI

from .config import (
    OLLAMA_MIN_FIT_SCORE,
    PROFILE_NOTES_FILE,
)

def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

def ollama_is_configured() -> bool:
    # Function name retained so we don't break imports in jobspy_jobs.py
    return bool(get_env("OPENAI_API_KEY"))

def load_profile_notes(profile_notes_path: str = str(PROFILE_NOTES_FILE)) -> str:
    path = Path(profile_notes_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()

def build_job_prompt(job: dict[str, str], profile_notes: str) -> str:
    description = (job.get("description") or "")[:4000]
    return (
        "You are scoring whether a job is a strong fit for a candidate.\n"
        "Use the profile notes as the source of truth.\n"
        "Return only valid JSON with keys fit_score, should_save, reason.\n"
        "fit_score must be an integer from 0 to 10.\n"
        "should_save must be a boolean (true or false).\n"
        "reason must be one short sentence explaining the score.\n\n"
        f"Profile notes:\n{profile_notes}\n\n"
        f"Job title: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Posted at: {job.get('posted_at', '')}\n"
        f"Description:\n{description}\n"
    )

def score_job_with_ollama(job: dict[str, str], profile_notes: str) -> dict[str, str] | None:
    api_key = get_env("OPENAI_API_KEY")
    if not api_key:
        return None

    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise recruiting assistant. Only return valid JSON."
                },
                {
                    "role": "user",
                    "content": build_job_prompt(job=job, profile_notes=profile_notes)
                }
            ],
            temperature=0.0
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        fit_score = parsed.get("fit_score", 0)
        should_save = parsed.get("should_save", False)
        reason = str(parsed.get("reason", "")).strip()

        try:
            fit_score_int = max(0, min(10, int(fit_score)))
        except (TypeError, ValueError):
            fit_score_int = 0
            
        return {
            "ollama_fit_score": str(fit_score_int),
            "ollama_should_save": "true" if should_save else "false",
            "ollama_reason": reason,
        }

    except Exception as e:
        # This f-string properly injects the error message 'e'
        print(f"\nCRITICAL OPENAI API ERROR: {e}\n")
        return None

def rerank_jobs_with_ollama(
    job_list: list[dict[str, str]],
    shortlist_size: int,
    minimum_fit_score: int = OLLAMA_MIN_FIT_SCORE,
) -> list[dict[str, str]]:
    if not job_list or not ollama_is_configured():
        return job_list

    profile_notes = load_profile_notes()
    if not profile_notes:
        return job_list

    shortlist = job_list[:shortlist_size]
    remainder = job_list[shortlist_size:]
    reranked: list[dict[str, str]] = []

    for job in shortlist:
        ollama_result = score_job_with_ollama(job=job, profile_notes=profile_notes)
        if ollama_result is None:
            reranked.append(job)
            continue

        enriched_job = dict(job)
        enriched_job.update(ollama_result)
        ai_score = int(enriched_job.get("ollama_fit_score", "0") or 0)
        if enriched_job.get("ollama_should_save") == "true" and ai_score >= minimum_fit_score:
            reranked.append(enriched_job)

    reranked.sort(
        key=lambda job: (
            -int(job.get("ollama_fit_score", "0") or 0),
            -int(job.get("fit_score", "0") or 0),
            job.get("posted_at") == "",
            job.get("posted_at", ""),
            job.get("company", "").lower(),
        ),
    )
    return reranked + remainder

def split_jobs_with_ollama(
    job_list: list[dict[str, str]],
    shortlist_size: int,
    minimum_fit_score: int = OLLAMA_MIN_FIT_SCORE,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not job_list:
        return [], []

    shortlist = job_list[:shortlist_size]
    if not ollama_is_configured():
        return shortlist, []

    profile_notes = load_profile_notes()
    if not profile_notes:
        return shortlist, []

    approved: list[dict[str, str]] = []
    archived: list[dict[str, str]] = []

    for job in shortlist:
        ollama_result = score_job_with_ollama(job=job, profile_notes=profile_notes)
        if ollama_result is None:
            approved.append(job)
            continue

        enriched_job = dict(job)
        enriched_job.update(ollama_result)
        ai_score = int(enriched_job.get("ollama_fit_score", "0") or 0)

        if enriched_job.get("ollama_should_save") == "true" and ai_score >= minimum_fit_score:
            approved.append(enriched_job)
        else:
            archived.append(enriched_job)

    approved.sort(
        key=lambda job: (
            -int(job.get("ollama_fit_score", "0") or 0),
            -int(job.get("fit_score", "0") or 0),
            job.get("posted_at") == "",
            job.get("posted_at", ""),
            job.get("company", "").lower(),
        ),
    )
    archived.sort(
        key=lambda job: (
            -int(job.get("fit_score", "0") or 0),
            job.get("posted_at") == "",
            job.get("posted_at", ""),
            job.get("company", "").lower(),
        ),
    )
    return approved, archived