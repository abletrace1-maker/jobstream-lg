import os
import json
import tempfile
import pytest
from unittest import mock

from src.nodes.parent_nodes import job_ingestion, load_config_and_resume
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
    resume_path = resumes_dir / "data_science.json"
    resume_path.write_text(json.dumps(dummy_resume_data))
    
    # Patch the paths in the module
    with mock.patch("src.nodes.parent_nodes.os.path.exists", side_effect=lambda path: str(path).endswith("job_tracker.json") or "json_resumes" in str(path)):
        with mock.patch("src.nodes.parent_nodes.open", mock.mock_open(read_data=job_tracker_path.read_text())) as m:
            # We need a more complex mock for open since it opens multiple files
            def mock_open_wrapper(file, mode="r", encoding=None):
                if "job_tracker.json" in file:
                    return mock.mock_open(read_data=json.dumps(job_data))()
                elif "json_resumes" in file:
                    return mock.mock_open(read_data=json.dumps(dummy_resume_data))()
                return mock.mock_open()()
            
            with mock.patch("src.nodes.parent_nodes.open", side_effect=mock_open_wrapper):
                with mock.patch("src.nodes.parent_nodes.os.listdir", return_value=["data_science.json"]):
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
        with mock.patch("src.nodes.parent_nodes.open", mock.mock_open()) as m_open:
            with mock.patch("src.nodes.parent_nodes.os.makedirs") as m_makedirs:
                state = {}
                updates = load_config_and_resume(state)
                
                assert "pending_jobs" in updates
                assert len(updates["pending_jobs"]) == 1
                assert updates["pending_jobs"][0].job_id == "dummy-123"
                assert "base_resumes" in updates
                assert len(updates["base_resumes"]) == 0


def test_job_ingestion_extracts_targeted_text_from_url():
    job = JobTrackerEntry(
        job_id="job-1",
        title="Data Analyst",
        company="Acme",
        source_type="url",
        source="https://example.com/job",
        category="data",
        user_score="high",
        notes="",
        status="PENDING",
    )
    raw_html = """
    <h1 class="topcard__title">Data Analyst</h1>
    <div class="show-more-less-html__markup">Analyze metrics.</div>
    """

    with mock.patch("src.nodes.parent_nodes.scraper.uc.Chrome") as mock_chrome:
        mock_driver = mock.Mock()
        mock_chrome.return_value = mock_driver
        with mock.patch("src.nodes.parent_nodes.scraper.fetch_url_stealth", return_value=raw_html) as mock_fetch:
            updates = job_ingestion({"pending_jobs": [job], "scraped_jobs": []})

    assert len(updates["scraped_jobs"]) == 1
    scraped_job = updates["scraped_jobs"][0]
    assert scraped_job.job_id == "job-1"
    assert scraped_job.job_title == "Data Analyst"
    assert "Core Description:\nAnalyze metrics." in scraped_job.raw_text
    assert updates["failed_jobs"] == []
    mock_fetch.assert_called_once_with(mock_driver, "https://example.com/job")
    mock_driver.quit.assert_called_once()


def test_job_ingestion_extracts_targeted_text_from_file(tmp_path):
    source_file = tmp_path / "posting.html"
    source_file.write_text(
        "<h1 class='topcard__title'>Engineer</h1><div class='show-more-less-html__markup'>Build services.</div>"
    )
    job = JobTrackerEntry(
        job_id="job-2",
        title="Engineer",
        company="Acme",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )

    updates = job_ingestion({"pending_jobs": [job], "scraped_jobs": []})

    assert len(updates["scraped_jobs"]) == 1
    assert "Core Description:\nBuild services." in updates["scraped_jobs"][0].raw_text
    assert updates["failed_jobs"] == []


def test_job_ingestion_records_failed_jobs():
    job = JobTrackerEntry(
        job_id="job-3",
        title="Engineer",
        company="Acme",
        source_type="unknown",
        source="",
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )

    updates = job_ingestion({"pending_jobs": [job], "scraped_jobs": []})

    assert updates["scraped_jobs"] == []
    assert updates["failed_jobs"] == [job]
