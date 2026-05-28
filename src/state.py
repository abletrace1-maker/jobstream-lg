from enum import Enum
from typing import TypedDict, Dict, List

from src.schemas import (
    BaseResumeSchema,
    JobTrackerEntry,
    JobDetailsSchema,
    ClarificationQuestion,
    ResumeDiffSchema,
)

class JobStatus(str, Enum):
    EVALUATING = "EVALUATING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    STRATEGY_DRAFTED = "STRATEGY_DRAFTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUAL_INPUT_REQUIRED = "MANUAL_INPUT_REQUIRED"

class ParentGraphState(TypedDict):
    base_resumes: Dict[str, BaseResumeSchema]
    config: dict
    prompts: dict
    pending_jobs: List[JobTrackerEntry]
    scraped_jobs: List[JobDetailsSchema]
    failed_jobs: List[JobTrackerEntry]

class ChildGraphState(TypedDict):
    base_resume: BaseResumeSchema
    job_details: JobDetailsSchema
    status: JobStatus
    clarification_questions: List[ClarificationQuestion]
    user_clarification_answers: Dict[str, str]
    strategy_markdown: str
    resume_diffs: ResumeDiffSchema
    user_feedback: str
    tailored_resume: BaseResumeSchema
    cover_letter_markdown: str
    resume_pdf_path: str
    cover_letter_pdf_path: str
