import os
import json
import re
import yaml
from datetime import date
from typing import Any, Callable, Dict, Mapping

from src.schemas import BaseResumeSchema, JobDetailsSchema, JobTrackerEntry
from src.state import JobStatus, ParentGraphState
from src.utils.html_parser import extract_job_details
from src.utils import scraper
from src.resume_converter import convert_starter_resumes_to_json, BatchResumeConversionError

def load_config_and_resume(state: ParentGraphState) -> Dict[str, Any]:
    """
    Loads configuration, base resumes, and the job tracker queue.
    """
    
    # 1. Load job_tracker.json
    job_tracker_path = "data/job_tracker.json"
    pending_jobs = []
    if os.path.exists(job_tracker_path):
        with open(job_tracker_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                pending_jobs = [JobTrackerEntry(**job) for job in data]
            except Exception as e:
                print(f"Error parsing job_tracker.json: {e}")
    else:
        # Create dummy if missing
        dummy_job = JobTrackerEntry(
            job_id="dummy-123",
            title="Software Engineer",
            company="Tech Corp",
            source_type="url",
            source="https://example.com/job",
            category="software_engineering",
            user_score="high",
            notes="Dummy job",
            status="PENDING"
        )
        pending_jobs.append(dummy_job)
        os.makedirs(os.path.dirname(job_tracker_path), exist_ok=True)
        with open(job_tracker_path, "w", encoding="utf-8") as f:
            json.dump([dummy_job.model_dump()], f, indent=2)

    # 2. Read JSON base resumes from data/json_resumes/
    starter_dir = "data/starter_resumes"
    resumes_dir = "data/json_resumes"
    
    # Try converting any new starter resumes first
    try:
        convert_starter_resumes_to_json(starter_dir=starter_dir, output_dir=resumes_dir)
    except BatchResumeConversionError as e:
        print(f"Batch conversion error during startup: {e}")
    except Exception as e:
        print(f"Error converting starter resumes during startup: {e}")

    base_resumes = {}
    if os.path.exists(resumes_dir):
        for filename in os.listdir(resumes_dir):
            if filename.endswith(".json"):
                stem = filename[:-5]
                category = stem.removeprefix("base_resume_")
                filepath = os.path.join(resumes_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        base_resumes[category] = BaseResumeSchema(**data)
                except Exception as e:
                    print(f"Error parsing resume {filename}: {e}")
    else:
        os.makedirs(resumes_dir, exist_ok=True)

    # 3. Load config.yaml
    config_data = {}
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Error parsing config.yaml: {e}")

    # 4. Return the updates for the state
    return {
        "base_resumes": base_resumes,
        "pending_jobs": pending_jobs,
        "config": config_data,
        "prompts": state.get("prompts", {})
    }


def job_ingestion(state: ParentGraphState) -> Dict[str, Any]:
    existing_scraped_jobs = state.get("scraped_jobs", [])
    if existing_scraped_jobs:
        return {"scraped_jobs": existing_scraped_jobs}

    scraped_jobs = []
    failed_jobs = []
    parser = state.get("config", {}).get("job_details_parser")

    for batch_index, job in enumerate(state.get("pending_jobs", []), start=1):
        try:
            focused_text = _normalize_job_source(job)
            scraped_jobs.append(
                _parse_job_details(
                    focused_text,
                    job,
                    parser=parser,
                    batch_index=batch_index,
                )
            )
        except Exception:
            failed_jobs.append(_failed_job_entry(job))

    return {"scraped_jobs": scraped_jobs, "failed_jobs": failed_jobs}


def _failed_job_entry(job: JobTrackerEntry) -> JobTrackerEntry:
    if job.source_type == "url":
        return job.model_copy(update={"status": JobStatus.MANUAL_INPUT_REQUIRED.value})

    return job


JobDetailsParser = Callable[[str, JobTrackerEntry], Mapping[str, Any] | JobDetailsSchema]


def _parse_job_details(
    normalized_text: str,
    job: JobTrackerEntry,
    parser: JobDetailsParser | None = None,
    batch_index: int = 1,
) -> JobDetailsSchema:
    parsed_fields = (parser or _default_job_details_parser)(normalized_text, job)
    if isinstance(parsed_fields, JobDetailsSchema):
        parsed_fields = parsed_fields.model_dump()

    defaults = _job_details_defaults(normalized_text, job)
    merged = {**defaults, **dict(parsed_fields)}
    merged["job_title"] = merged.get("job_title") or defaults["job_title"]
    merged["company"] = _resolve_company(merged.get("company"), job.company)
    merged["job_id"] = _resolve_job_id(job.job_id, merged["company"], batch_index)
    merged["category"] = defaults["category"]
    merged["raw_text"] = normalized_text

    if merged.get("salary_range") == "":
        merged["salary_range"] = None
    if merged.get("nice_to_haves") is None:
        merged["nice_to_haves"] = []

    return JobDetailsSchema(**merged)


def _job_details_defaults(normalized_text: str, job: JobTrackerEntry) -> Dict[str, Any]:
    return {
        "job_title": job.title,
        "company": job.company,
        "location": "",
        "job_id": job.job_id,
        "category": job.category,
        "salary_range": None,
        "requirements": [],
        "nice_to_haves": [],
        "responsibilities": [],
        "raw_text": normalized_text,
    }


def _resolve_company(parsed_company: str | None, tracker_company: str | None) -> str:
    return _clean_string(parsed_company) or _clean_string(tracker_company) or "unknown-company"


def _resolve_job_id(existing_job_id: str | None, company: str, batch_index: int) -> str:
    if _is_valid_job_id(existing_job_id):
        return existing_job_id.strip()

    return _generate_canonical_job_id(company, batch_index)


def _is_valid_job_id(job_id: str | None) -> bool:
    if not job_id or not job_id.strip():
        return False

    normalized = job_id.strip().lower()
    return normalized not in {"placeholder", "tbd", "todo", "none", "null", "n/a", "na", "unknown"}


def _generate_canonical_job_id(company: str, batch_index: int) -> str:
    company_name = _sanitize_company_for_job_id(company)
    return f"{date.today():%m-%d}_{batch_index}_{company_name}"


def _sanitize_company_for_job_id(company: str) -> str:
    cleaned = _clean_string(company) or "unknown-company"
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"[\s_]+", "-", cleaned.strip())
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned or "unknown-company"


def _clean_string(value: str | None) -> str:
    return value.strip() if value else ""


def _default_job_details_parser(
    normalized_text: str,
    job: JobTrackerEntry,
) -> Mapping[str, Any]:
    sections = _split_normalized_sections(normalized_text)
    core_lines = _section_lines(sections.get("Core Description", normalized_text))

    return {
        "job_title": _first_line(sections.get("Job Title")) or job.title,
        "company": _first_line(sections.get("Company Info")) or job.company,
        "location": "",
        "salary_range": _first_line(sections.get("Compensation")),
        "requirements": _extract_list_by_keywords(core_lines, ("requirement", "qualification")),
        "nice_to_haves": _extract_list_by_keywords(core_lines, ("nice to have", "preferred")),
        "responsibilities": _extract_list_by_keywords(core_lines, ("responsibilit", "what you'll do", "duties")),
    }


def _split_normalized_sections(normalized_text: str) -> Dict[str, str]:
    section_labels = {
        "Job Title",
        "Company Info",
        "Core Description",
        "Job Criteria",
        "Compensation",
    }
    sections: Dict[str, list[str]] = {}
    current_label = None

    for line in normalized_text.splitlines():
        stripped = line.strip()
        possible_label = stripped[:-1] if stripped.endswith(":") else ""
        if possible_label in section_labels:
            current_label = possible_label
            sections.setdefault(current_label, [])
        elif current_label and stripped:
            sections[current_label].append(stripped)

    return {label: "\n".join(lines) for label, lines in sections.items()}


def _first_line(value: str | None) -> str:
    if not value:
        return ""
    return next((line for line in value.splitlines() if line.strip()), "").strip()


def _section_lines(value: str) -> list[str]:
    return [line.strip(" -•\t") for line in value.splitlines() if line.strip(" -•\t")]


def _extract_list_by_keywords(lines: list[str], keywords: tuple[str, ...]) -> list[str]:
    matches = []
    capture = False
    for line in lines:
        lowered = line.lower().rstrip(":")
        if any(keyword in lowered for keyword in keywords):
            capture = True
            continue
        if capture and lowered in {
            "requirements",
            "qualifications",
            "responsibilities",
            "preferred",
            "nice to have",
            "nice-to-have",
        }:
            continue
        if capture and line:
            matches.append(line)
    return matches


def _normalize_job_source(job: JobTrackerEntry) -> str:
    raw_content = _load_job_source(job)
    return extract_job_details(raw_content)


def _load_job_source(job: JobTrackerEntry) -> str:
    if job.source_type == "url":
        return _load_url_source(job.source)

    if job.source_type == "file":
        return _load_file_source(job.source)

    raise ValueError(f"Unsupported job source_type: {job.source_type}")


def _load_url_source(url: str) -> str:
    driver = scraper.create_driver()
    try:
        return scraper.fetch_url_stealth(driver, url)
    finally:
        if hasattr(driver, "quit"):
            driver.quit()


def _load_file_source(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
