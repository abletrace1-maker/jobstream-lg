import json
import pytest
from unittest import mock

from src.nodes.parent_nodes import load_config_and_resume
from src.schemas import BaseResumeSchema, JobTrackerEntry

@pytest.fixture
def dummy_resume_data():
    return {
        "name": "John Doe",
        "contact_info": {
            "email": "john@example.com",
            "phone": "123-456-7890",
            "linkedin": "linkedin.com/in/johndoe",
            "location": "New York, NY"
        },
        "professional_summary": "Experienced software engineer.",
        "skills": {
            "languages": ["Python", "JavaScript"]
        },
        "professional_experience": [
            {
                "job_title": "Software Engineer",
                "company": "Tech Corp",
                "location": "New York, NY",
                "start_date": "2020-01-01",
                "end_date": "Present",
                "highlights": ["Built cool things."]
            }
        ],
        "educational_experience": [
            {
                "degree": "B.S. Computer Science",
                "school": "University",
                "start_date": "2016-09-01",
                "end_date": "2020-05-01",
                "awards": ["Dean's List"]
            }
        ],
        "other_points": ["Avid hiker."]
    }

def test_load_config_and_resume_with_existing_data(dummy_resume_data, tmp_path):
    # Setup mock file system inside the test
    job_tracker_path = tmp_path / "data" / "job_tracker.json"
    resumes_dir = tmp_path / "data" / "json_resumes"
    resumes_dir.mkdir(parents=True, exist_ok=True)
    
    # Write mock job_tracker.json
    job_data = [{
        "job_id": "test-job-1",
        "title": "Data Scientist",
        "company": "Data Inc",
        "source_type": "url",
        "source": "https://example.com/data",
        "category": "data_science",
        "user_score": "high",
        "notes": "Test note",
        "status": "PENDING"
    }]
    job_tracker_path.write_text(json.dumps(job_data))
    
    # Write mock resume
    resume_path = resumes_dir / "base_resume_data_science.json"
    resume_path.write_text(json.dumps(dummy_resume_data))
    
    # Patch the paths in the module
    with mock.patch("src.nodes.parent_nodes.os.path.exists", side_effect=lambda path: str(path).endswith("job_tracker.json") or "json_resumes" in str(path)):
        with mock.patch("src.nodes.parent_nodes.open", mock.mock_open(read_data=job_tracker_path.read_text())):
            # We need a more complex mock for open since it opens multiple files
            def mock_open_wrapper(file, mode="r", encoding=None):
                if "job_tracker.json" in file:
                    return mock.mock_open(read_data=json.dumps(job_data))()
                elif "json_resumes" in file:
                    return mock.mock_open(read_data=json.dumps(dummy_resume_data))()
                return mock.mock_open()()
            
            with mock.patch("src.nodes.parent_nodes.open", side_effect=mock_open_wrapper):
                with mock.patch("src.nodes.parent_nodes.os.listdir", return_value=["base_resume_data_science.json"]):
                    state = {}
                    updates = load_config_and_resume(state)
                    
                    assert "base_resumes" in updates
                    assert "data_science" in updates["base_resumes"]
                    assert isinstance(updates["base_resumes"]["data_science"], BaseResumeSchema)
                    assert updates["base_resumes"]["data_science"].name == "John Doe"
                    
                    assert "pending_jobs" in updates
                    assert len(updates["pending_jobs"]) == 1
                    assert isinstance(updates["pending_jobs"][0], JobTrackerEntry)
                    assert updates["pending_jobs"][0].job_id == "test-job-1"

def test_load_config_and_resume_creates_dummy(tmp_path):
    with mock.patch("src.nodes.parent_nodes.os.path.exists", return_value=False):
        with mock.patch("src.nodes.parent_nodes.open", mock.mock_open()):
            with mock.patch("src.nodes.parent_nodes.os.makedirs"):
                state = {}
                updates = load_config_and_resume(state)
                
                assert "pending_jobs" in updates
                assert len(updates["pending_jobs"]) == 1
                assert updates["pending_jobs"][0].job_id == "dummy-123"
                assert "base_resumes" in updates
                assert len(updates["base_resumes"]) == 0
