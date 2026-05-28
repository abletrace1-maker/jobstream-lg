import pytest
from pydantic import ValidationError
from src.schemas import JobTrackerEntry, BaseResumeSchema, JobDetailsSchema

def test_job_tracker_entry_valid():
    data = {
        "job_id": "05-20_1_MHB-Group-Canada",
        "title": "Development Manager",
        "company": "MHB Group Canada",
        "source_type": "url",
        "source": "https://www.linkedin.com/jobs/view/...",
        "category": "project_management",
        "user_score": "8/10",
        "notes": "Development management job...",
        "status": "PENDING"
    }
    obj = JobTrackerEntry(**data)
    assert obj.job_id == "05-20_1_MHB-Group-Canada"

def test_job_tracker_entry_invalid():
    with pytest.raises(ValidationError):
        JobTrackerEntry(title="Missing Fields")

def test_base_resume_schema_valid():
    data = {
        "name": "John Doe",
        "contact_info": {
            "email": "john.doe@example.com",
            "phone": "555-0100",
            "linkedin": "linkedin.com/in/johndoe",
            "location": "New York, NY"
        },
        "professional_summary": "Experienced software engineer...",
        "skills": {
            "languages": ["Python", "JavaScript", "Go"],
        },
        "professional_experience": [
            {
                "job_title": "Senior Backend Engineer",
                "company": "Tech Corp",
                "location": "Remote",
                "start_date": "2020-05",
                "end_date": "Present",
                "highlights": [
                    "Designed and implemented microservices architecture reducing latency by 40%."
                ]
            }
        ],
        "educational_experience": [
            {
                "degree": "B.S. Computer Science",
                "school": "State University",
                "start_date": "2015-09",
                "end_date": "2019-05",
                "awards": ["Dean's List 2018"]
            }
        ],
        "other_points": [
            "AWS Certified Solutions Architect"
        ]
    }
    obj = BaseResumeSchema(**data)
    assert obj.name == "John Doe"

def test_base_resume_schema_invalid():
    with pytest.raises(ValidationError):
        BaseResumeSchema(name="Missing Fields")

def test_job_details_schema_valid():
    data = {
        "job_title": "Lead Python Developer",
        "company": "DataTech Solutions",
        "location": "New York, NY (Hybrid)",
        "job_id": "05-20_3_DataTech-Solutions",
        "category": "engineering", 
        "salary_range": "$140k - $180k",
        "requirements": [
            "5+ years of Python experience"
        ],
        "nice_to_haves": [
            "Frontend experience with React"
        ],
        "responsibilities": [
            "Build and maintain agentic workflows"
        ],
        "raw_text": "..." 
    }
    obj = JobDetailsSchema(**data)
    assert obj.job_title == "Lead Python Developer"

def test_job_details_schema_invalid():
    with pytest.raises(ValidationError):
        JobDetailsSchema(job_title="Missing Fields")
