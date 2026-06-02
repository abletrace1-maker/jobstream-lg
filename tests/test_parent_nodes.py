import json
from datetime import date
from unittest import mock

import pytest

from src.nodes.parent_nodes import job_ingestion, load_config_and_resume
from src.schemas import BaseResumeSchema, JobTrackerEntry
from src.resume_converter import BatchResumeConversionError

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
                    with mock.patch("src.nodes.parent_nodes.convert_starter_resumes_to_json") as mock_convert:
                        state = {}
                        updates = load_config_and_resume(state)
                        
                        mock_convert.assert_called_once_with(
                            starter_dir="data/starter_resumes", 
                            output_dir="data/json_resumes"
                        )
                        
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
                with mock.patch("src.nodes.parent_nodes.convert_starter_resumes_to_json") as mock_convert:
                    state = {}
                    updates = load_config_and_resume(state)
                    
                    mock_convert.assert_called_once_with(
                        starter_dir="data/starter_resumes", 
                        output_dir="data/json_resumes"
                    )
                    
                    assert "pending_jobs" in updates
                    assert len(updates["pending_jobs"]) == 1
                    assert updates["pending_jobs"][0].job_id == "dummy-123"
                    assert "base_resumes" in updates
                    assert len(updates["base_resumes"]) == 0

def test_load_config_and_resume_handles_conversion_error(tmp_path):
    with mock.patch("src.nodes.parent_nodes.os.path.exists", return_value=False):
        with mock.patch("src.nodes.parent_nodes.open", mock.mock_open()):
            with mock.patch("src.nodes.parent_nodes.os.makedirs"):
                with mock.patch("src.nodes.parent_nodes.convert_starter_resumes_to_json", side_effect=BatchResumeConversionError({}, {})) as mock_convert:
                    state = {}
                    updates = load_config_and_resume(state)
                    
                    mock_convert.assert_called_once()
                    assert "pending_jobs" in updates
                    assert updates["pending_jobs"][0].job_id == "dummy-123"

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

    with mock.patch("src.nodes.parent_nodes.scraper.create_driver") as mock_create_driver:
        mock_driver = mock.Mock()
        mock_create_driver.return_value = mock_driver
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


def test_job_ingestion_extracts_raw_text_from_file(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Plain text job posting\nBuild reliable services.", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="job-raw-file",
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
    assert updates["scraped_jobs"][0].raw_text == "Plain text job posting\nBuild reliable services."
    assert updates["failed_jobs"] == []


def test_job_ingestion_preserves_existing_scraped_jobs():
    scraped_job = mock.Mock()
    pending_job = JobTrackerEntry(
        job_id="job-4",
        title="Engineer",
        company="Acme",
        source_type="url",
        source="https://example.com/job",
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )

    with mock.patch("src.nodes.parent_nodes._normalize_job_source") as mock_normalize:
        updates = job_ingestion(
            {"pending_jobs": [pending_job], "scraped_jobs": [scraped_job], "failed_jobs": []}
        )

    assert updates == {"scraped_jobs": [scraped_job]}
    mock_normalize.assert_not_called()


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


def test_job_ingestion_records_scraper_exception_as_manual_input_required():
    job = JobTrackerEntry(
        job_id="job-scraper-fails",
        title="Engineer",
        company="Acme",
        source_type="url",
        source="https://example.com/blocked-job",
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )

    with mock.patch("src.nodes.parent_nodes.scraper.create_driver") as mock_create_driver:
        mock_driver = mock.Mock()
        mock_create_driver.return_value = mock_driver
        with mock.patch(
            "src.nodes.parent_nodes.scraper.fetch_url_stealth",
            side_effect=RuntimeError("blocked"),
        ):
            updates = job_ingestion({"pending_jobs": [job], "scraped_jobs": []})

    assert updates["scraped_jobs"] == []
    assert len(updates["failed_jobs"]) == 1
    assert updates["failed_jobs"][0].job_id == "job-scraper-fails"
    assert updates["failed_jobs"][0].status == "MANUAL_INPUT_REQUIRED"
    assert job.status == "PENDING"
    mock_create_driver.assert_called_once()
    mock_driver.quit.assert_called_once()


def test_job_ingestion_records_missing_file_and_continues(tmp_path):
    missing_job = JobTrackerEntry(
        job_id="job-missing-file",
        title="Missing File Role",
        company="Acme",
        source_type="file",
        source=str(tmp_path / "missing.txt"),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    success_file = tmp_path / "success.txt"
    success_file.write_text("Successful posting", encoding="utf-8")
    success_job = JobTrackerEntry(
        job_id="job-success",
        title="Success Role",
        company="Acme",
        source_type="file",
        source=str(success_file),
        category="engineering",
        user_score="high",
        notes="",
        status="PENDING",
    )

    updates = job_ingestion({"pending_jobs": [missing_job, success_job], "scraped_jobs": []})

    assert [job.job_id for job in updates["scraped_jobs"]] == ["job-success"]
    assert updates["failed_jobs"] == [missing_job]


def test_job_ingestion_keeps_mixed_success_and_failure_batches_isolated(tmp_path):
    success_file = tmp_path / "success.txt"
    success_file.write_text("Successful posting", encoding="utf-8")
    success_job = JobTrackerEntry(
        job_id="job-success",
        title="Success Role",
        company="Acme",
        source_type="file",
        source=str(success_file),
        category="engineering",
        user_score="high",
        notes="",
        status="PENDING",
    )
    unsupported_job = JobTrackerEntry(
        job_id="job-unsupported",
        title="Unsupported Role",
        company="Acme",
        source_type="manual",
        source="",
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(return_value={"requirements": [], "responsibilities": []})

    updates = job_ingestion(
        {
            "pending_jobs": [success_job, unsupported_job],
            "scraped_jobs": [],
            "config": {"job_details_parser": parser},
        }
    )

    assert [job.job_id for job in updates["scraped_jobs"]] == ["job-success"]
    assert updates["failed_jobs"] == [unsupported_job]
    parser.assert_called_once_with("Successful posting", success_job)


def test_job_ingestion_uses_injected_structured_parser(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Parsed job text", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="tracker-job-id",
        title="Fallback Title",
        company="Fallback Co",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="high",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(
        return_value={
            "job_title": "Parsed Engineer",
            "company": "Parsed Co",
            "location": "Remote",
            "job_id": "parser-job-id",
            "category": "parser-category",
            "salary_range": "$100k - $120k",
            "requirements": ["Python"],
            "nice_to_haves": ["LangGraph"],
            "responsibilities": ["Build workflows"],
        }
    )

    updates = job_ingestion(
        {
            "pending_jobs": [job],
            "scraped_jobs": [],
            "config": {"job_details_parser": parser},
        }
    )

    assert updates["failed_jobs"] == []
    scraped_job = updates["scraped_jobs"][0]
    assert scraped_job.job_title == "Parsed Engineer"
    assert scraped_job.company == "Parsed Co"
    assert scraped_job.location == "Remote"
    assert scraped_job.job_id == "tracker-job-id"
    assert scraped_job.category == "engineering"
    assert scraped_job.salary_range == "$100k - $120k"
    assert scraped_job.requirements == ["Python"]
    assert scraped_job.nice_to_haves == ["LangGraph"]
    assert scraped_job.responsibilities == ["Build workflows"]
    assert scraped_job.raw_text == "Parsed job text"
    parser.assert_called_once_with("Parsed job text", job)


def test_job_ingestion_defaults_missing_optional_parser_fields(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Posting without salary or nice-to-haves", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="job-no-optionals",
        title="Backend Engineer",
        company="Acme",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(
        return_value={"requirements": ["Python"], "responsibilities": ["Build APIs"]}
    )

    updates = job_ingestion(
        {
            "pending_jobs": [job],
            "scraped_jobs": [],
            "config": {"job_details_parser": parser},
        }
    )

    scraped_job = updates["scraped_jobs"][0]
    assert scraped_job.job_title == "Backend Engineer"
    assert scraped_job.company == "Acme"
    assert scraped_job.salary_range is None
    assert scraped_job.nice_to_haves == []
    assert updates["failed_jobs"] == []


def test_job_ingestion_records_malformed_parser_output(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Malformed parser output", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="job-malformed",
        title="Backend Engineer",
        company="Acme",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(return_value={"requirements": "Python", "responsibilities": []})

    updates = job_ingestion(
        {
            "pending_jobs": [job],
            "scraped_jobs": [],
            "config": {"job_details_parser": parser},
        }
    )

    assert updates["scraped_jobs"] == []
    assert updates["failed_jobs"] == [job]


def test_job_ingestion_file_parser_does_not_use_network(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("No network parser text", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="job-file-parser",
        title="Backend Engineer",
        company="Acme",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(return_value={"requirements": [], "responsibilities": []})

    with mock.patch("src.nodes.parent_nodes.scraper.fetch_url_stealth") as mock_fetch:
        updates = job_ingestion(
            {
                "pending_jobs": [job],
                "scraped_jobs": [],
                "config": {"job_details_parser": parser},
            }
        )

    assert len(updates["scraped_jobs"]) == 1
    assert updates["failed_jobs"] == []
    mock_fetch.assert_not_called()
    parser.assert_called_once_with("No network parser text", job)


def test_job_ingestion_preserves_existing_valid_job_id(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Existing ID posting", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="existing-job-123",
        title="Backend Engineer",
        company="Tracker Co",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(
        return_value={"company": "Parsed Co", "requirements": [], "responsibilities": []}
    )

    updates = job_ingestion(
        {
            "pending_jobs": [job],
            "scraped_jobs": [],
            "config": {"job_details_parser": parser},
        }
    )

    assert updates["scraped_jobs"][0].job_id == "existing-job-123"
    assert updates["scraped_jobs"][0].company == "Parsed Co"


def test_job_ingestion_replaces_placeholder_job_id_with_canonical_id(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Placeholder ID posting", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="placeholder",
        title="Backend Engineer",
        company="Tracker Co",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(
        return_value={"company": "Parsed Company", "requirements": [], "responsibilities": []}
    )

    with mock.patch("src.nodes.parent_nodes.date") as mock_date:
        mock_date.today.return_value = date(2025, 3, 9)
        updates = job_ingestion(
            {
                "pending_jobs": [job],
                "scraped_jobs": [],
                "config": {"job_details_parser": parser},
            }
        )

    assert updates["scraped_jobs"][0].job_id == "03-09_1_Parsed-Company"


def test_job_ingestion_generates_job_ids_with_stable_batch_index(tmp_path):
    first_source = tmp_path / "first.txt"
    second_source = tmp_path / "second.txt"
    first_source.write_text("First posting", encoding="utf-8")
    second_source.write_text("Second posting", encoding="utf-8")
    first_job = JobTrackerEntry(
        job_id="",
        title="Backend Engineer",
        company="One Co",
        source_type="file",
        source=str(first_source),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    second_job = JobTrackerEntry(
        job_id="",
        title="Data Engineer",
        company="Two Co",
        source_type="file",
        source=str(second_source),
        category="data",
        user_score="high",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(return_value={"requirements": [], "responsibilities": []})

    with mock.patch("src.nodes.parent_nodes.date") as mock_date:
        mock_date.today.return_value = date(2025, 3, 9)
        updates = job_ingestion(
            {
                "pending_jobs": [first_job, second_job],
                "scraped_jobs": [],
                "config": {"job_details_parser": parser},
            }
        )

    assert [job.job_id for job in updates["scraped_jobs"]] == [
        "03-09_1_One-Co",
        "03-09_2_Two-Co",
    ]


def test_job_ingestion_sanitizes_company_names_for_generated_job_ids(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Sanitized ID posting", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="n/a",
        title="Backend Engineer",
        company="Acme, Inc. / R&D",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(return_value={"requirements": [], "responsibilities": []})

    with mock.patch("src.nodes.parent_nodes.date") as mock_date:
        mock_date.today.return_value = date(2025, 3, 9)
        updates = job_ingestion(
            {
                "pending_jobs": [job],
                "scraped_jobs": [],
                "config": {"job_details_parser": parser},
            }
        )

    assert updates["scraped_jobs"][0].job_id == "03-09_1_Acme-Inc-RD"


def test_job_ingestion_uses_unknown_company_when_no_company_is_available(tmp_path):
    source_file = tmp_path / "posting.txt"
    source_file.write_text("Unknown company posting", encoding="utf-8")
    job = JobTrackerEntry(
        job_id="",
        title="Backend Engineer",
        company="",
        source_type="file",
        source=str(source_file),
        category="engineering",
        user_score="medium",
        notes="",
        status="PENDING",
    )
    parser = mock.Mock(return_value={"company": "", "requirements": [], "responsibilities": []})

    with mock.patch("src.nodes.parent_nodes.date") as mock_date:
        mock_date.today.return_value = date(2025, 3, 9)
        updates = job_ingestion(
            {
                "pending_jobs": [job],
                "scraped_jobs": [],
                "config": {"job_details_parser": parser},
            }
        )

    assert updates["scraped_jobs"][0].company == "unknown-company"
    assert updates["scraped_jobs"][0].job_id == "03-09_1_unknown-company"
