import os
import json
from typing import Any, Dict

from src.schemas import BaseResumeSchema, JobTrackerEntry
from src.state import ParentGraphState

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
    resumes_dir = "data/json_resumes"
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

    # 3. Return the updates for the state
    return {
        "base_resumes": base_resumes,
        "pending_jobs": pending_jobs,
        "config": state.get("config", {}),
        "prompts": state.get("prompts", {})
    }
