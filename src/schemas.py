from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

class ContactInfo(BaseModel):
    email: str
    phone: str
    linkedin: str
    location: str

class Experience(BaseModel):
    job_title: str
    company: str
    location: str
    start_date: str
    end_date: str
    highlights: List[str]

class Education(BaseModel):
    degree: str
    school: str
    start_date: str
    end_date: str
    awards: List[str] = Field(default_factory=list)

class BaseResumeSchema(BaseModel):
    name: str
    contact_info: ContactInfo
    professional_summary: str
    skills: Dict[str, List[str]]
    professional_experience: List[Experience]
    educational_experience: List[Education]
    other_points: List[str] = Field(default_factory=list)

class JobTrackerEntry(BaseModel):
    job_id: str
    title: str
    company: str
    source_type: str
    source: str
    category: str
    user_score: str
    notes: str
    status: str

class JobDetailsSchema(BaseModel):
    job_title: str
    company: str
    location: str
    job_id: str
    category: str
    salary_range: Optional[str] = None
    requirements: List[str]
    nice_to_haves: List[str] = Field(default_factory=list)
    responsibilities: List[str]
    raw_text: str

class ClarificationQuestion(BaseModel):
    id: str
    type: Literal["multiple_choice", "text"]
    question: str
    options: List[str]

class ResumeChange(BaseModel):
    action: str
    section: str
    old_value: str
    new_value: str
    reason: str

class ResumeDiffSchema(BaseModel):
    changes: List[ResumeChange]
