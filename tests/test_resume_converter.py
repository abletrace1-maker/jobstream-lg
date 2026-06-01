import copy
import json
from pathlib import Path
from typing import Any

import pytest

from src.resume_converter import (
    BatchResumeConversionError,
    DuplicateStarterResumeError,
    ResumeValidationError,
    UnsupportedResumeFormatError,
    convert_resume_file_to_json,
    convert_resume_text,
    convert_resume_text_to_json,
    convert_starter_resumes_to_json,
    discover_starter_resumes,
    extract_resume_text,
)
from src.schemas import BaseResumeSchema


VALID_RESUME_DATA: dict[str, Any] = {
    "name": "Jane Candidate",
    "contact_info": {
        "email": "jane@example.com",
        "phone": "555-0100",
        "linkedin": "linkedin.com/in/janecandidate",
        "location": "Toronto, Ontario",
    },
    "professional_summary": "Delivery leader with implementation experience.",
    "skills": {
        "delivery": ["Project Management", "Client Onboarding"],
        "technical": ["API Integrations", "Jira"],
    },
    "professional_experience": [
        {
            "job_title": "Implementation Manager",
            "company": "Example Co",
            "location": "Toronto, Ontario",
            "start_date": "January 2020",
            "end_date": "Present",
            "highlights": [
                "Led API rollout across three client teams.",
                "Preserved this exact measurable bullet without summarization.",
            ],
        }
    ],
    "educational_experience": [
        {
            "degree": "Bachelor of Science",
            "school": "Example University",
            "start_date": "2015",
            "end_date": "2019",
            "awards": [],
        }
    ],
    "other_points": ["PMP certified"],
}


def test_convert_resume_text_accepts_injected_parser_output() -> None:
    def parser(raw_text: str, category: str) -> dict[str, object]:
        assert raw_text == "resume text"
        assert category == "engineering"
        return VALID_RESUME_DATA

    resume = convert_resume_text("resume text", "engineering", parser=parser)

    assert isinstance(resume, BaseResumeSchema)
    assert resume.name == "Jane Candidate"
    assert resume.professional_experience[0].highlights == VALID_RESUME_DATA[
        "professional_experience"
    ][0]["highlights"]


def test_convert_resume_text_to_json_writes_deterministic_base_resume_file(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "json_resumes"

    resume = convert_resume_text_to_json(
        "resume text",
        "engineering",
        output_dir,
        parser=lambda _raw_text, _category: VALID_RESUME_DATA,
    )

    output_path = output_dir / "base_resume_engineering.json"
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("{\n  \"name\":")
    loaded_resume = BaseResumeSchema.model_validate_json(
        output_path.read_text(encoding="utf-8")
    )
    assert loaded_resume == resume


def test_convert_resume_text_to_json_does_not_write_invalid_parser_output(
    tmp_path: Path,
) -> None:
    invalid_resume_data = copy.deepcopy(VALID_RESUME_DATA)
    del invalid_resume_data["contact_info"]

    with pytest.raises(ResumeValidationError, match="category='engineering'"):
        convert_resume_text_to_json(
            "resume text",
            "engineering",
            tmp_path,
            parser=lambda _raw_text, _category: invalid_resume_data,
        )

    assert not (tmp_path / "base_resume_engineering.json").exists()


def test_convert_resume_text_to_json_preserves_existing_json_on_failed_overwrite(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "base_resume_engineering.json"
    existing_json = json.dumps(VALID_RESUME_DATA, indent=2) + "\n"
    output_path.write_text(existing_json, encoding="utf-8")
    invalid_resume_data = copy.deepcopy(VALID_RESUME_DATA)
    del invalid_resume_data["professional_experience"]

    with pytest.raises(ResumeValidationError):
        convert_resume_text_to_json(
            "resume text",
            "engineering",
            tmp_path,
            parser=lambda _raw_text, _category: invalid_resume_data,
        )

    assert output_path.read_text(encoding="utf-8") == existing_json


def test_convert_resume_text_to_json_ignores_extra_top_level_parser_fields(
    tmp_path: Path,
) -> None:
    resume_data = copy.deepcopy(VALID_RESUME_DATA)
    resume_data["unsupported_top_level_field"] = "do not rely on this downstream"

    resume = convert_resume_text_to_json(
        "resume text",
        "engineering",
        tmp_path,
        parser=lambda _raw_text, _category: resume_data,
    )

    output_data = json.loads(
        (tmp_path / "base_resume_engineering.json").read_text(encoding="utf-8")
    )
    assert "unsupported_top_level_field" not in resume.model_dump()
    assert "unsupported_top_level_field" not in output_data


def test_default_plain_text_parser_preserves_starter_resume_highlights(
    tmp_path: Path,
) -> None:
    source_path = Path("data/starter_resumes/starter_engineering.txt")

    resume = convert_resume_file_to_json(source_path, "engineering", tmp_path)

    output_data = json.loads(
        (tmp_path / "base_resume_engineering.json").read_text(encoding="utf-8")
    )
    BaseResumeSchema.model_validate(output_data)
    all_highlights = [
        highlight
        for experience in resume.professional_experience
        for highlight in experience.highlights
    ]
    assert (
        "Directed multiple API integration initiatives connecting franchise POS systems, Shopify e-commerce storefronts, and third-party inventory and accounting applications with the central head office backend."
        in all_highlights
    )
    assert (
        "Chaired weekly stakeholder meetings and technical workshops with clients, engineering partners, and regulatory inspectors to align delivery goals, address project variations, and manage technical change controls."
        in all_highlights
    )
    assert len(resume.professional_experience) == 5
    assert len(all_highlights) == 22


def test_discover_starter_resumes_extracts_strict_categories(tmp_path: Path) -> None:
    starter_dir = tmp_path / "starter_resumes"
    starter_dir.mkdir()
    engineering_path = starter_dir / "starter_engineering.txt"
    project_management_path = starter_dir / "starter_project_management.docx"
    engineering_path.write_text("engineering resume", encoding="utf-8")
    project_management_path.write_bytes(b"docx bytes")
    (starter_dir / "notes.txt").write_text("ignored", encoding="utf-8")

    discovered = discover_starter_resumes(starter_dir)

    assert discovered == {
        "engineering": engineering_path,
        "project_management": project_management_path,
    }


def test_convert_starter_resumes_to_json_writes_every_discovered_category(
    tmp_path: Path,
) -> None:
    starter_dir = tmp_path / "starter_resumes"
    output_dir = tmp_path / "json_resumes"
    starter_dir.mkdir()
    (starter_dir / "starter_engineering.txt").write_text(
        "engineering resume",
        encoding="utf-8",
    )
    (starter_dir / "starter_project_management.txt").write_text(
        "project management resume",
        encoding="utf-8",
    )

    converted = convert_starter_resumes_to_json(
        starter_dir,
        output_dir,
        parser=lambda _raw_text, _category: VALID_RESUME_DATA,
    )

    assert set(converted) == {"engineering", "project_management"}
    assert (output_dir / "base_resume_engineering.json").exists()
    assert (output_dir / "base_resume_project_management.json").exists()
    engineering_data = json.loads(
        (output_dir / "base_resume_engineering.json").read_text(encoding="utf-8")
    )
    project_management_data = json.loads(
        (output_dir / "base_resume_project_management.json").read_text(encoding="utf-8")
    )
    BaseResumeSchema.model_validate(engineering_data)
    BaseResumeSchema.model_validate(project_management_data)


def test_convert_starter_resumes_to_json_reports_failure_context_and_keeps_successes(
    tmp_path: Path,
) -> None:
    starter_dir = tmp_path / "starter_resumes"
    output_dir = tmp_path / "json_resumes"
    starter_dir.mkdir()
    engineering_path = starter_dir / "starter_engineering.txt"
    construction_path = starter_dir / "starter_construction.txt"
    engineering_path.write_text("engineering resume", encoding="utf-8")
    construction_path.write_text("construction resume", encoding="utf-8")

    def parser(_raw_text: str, category: str) -> dict[str, object]:
        resume_data = copy.deepcopy(VALID_RESUME_DATA)
        if category == "construction":
            del resume_data["skills"]
        return resume_data

    with pytest.raises(BatchResumeConversionError) as exc_info:
        convert_starter_resumes_to_json(starter_dir, output_dir, parser=parser)

    error_message = str(exc_info.value)
    assert "construction" in error_message
    assert str(construction_path) in error_message
    assert "engineering" in exc_info.value.converted_resumes
    assert (output_dir / "base_resume_engineering.json").exists()
    assert not (output_dir / "base_resume_construction.json").exists()


def test_convert_starter_resumes_to_json_rejects_duplicate_categories(
    tmp_path: Path,
) -> None:
    starter_dir = tmp_path / "starter_resumes"
    output_dir = tmp_path / "json_resumes"
    starter_dir.mkdir()
    (starter_dir / "starter_engineering.txt").write_text(
        "engineering resume",
        encoding="utf-8",
    )
    (starter_dir / "starter_engineering.pdf").write_bytes(b"%PDF-1.4\n")

    with pytest.raises(DuplicateStarterResumeError, match="engineering"):
        convert_starter_resumes_to_json(
            starter_dir,
            output_dir,
            parser=lambda _raw_text, _category: VALID_RESUME_DATA,
        )

    assert not output_dir.exists()


def test_extract_resume_text_reads_txt_files(tmp_path: Path) -> None:
    source_path = tmp_path / "starter_engineering.txt"
    source_path.write_text("plain resume text", encoding="utf-8")

    assert extract_resume_text(source_path) == "plain resume text"


def test_convert_resume_file_to_json_routes_pdf_text_through_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "starter_project_management.pdf"
    source_path.write_bytes(b"%PDF-1.4\n")

    def fake_extract_pdf(path: Path) -> str:
        assert path == source_path
        return "extracted pdf resume text"

    def parser(raw_text: str, category: str) -> dict[str, object]:
        assert raw_text == "extracted pdf resume text"
        assert category == "project_management"
        return VALID_RESUME_DATA

    monkeypatch.setattr("src.resume_converter._extract_pdf_text", fake_extract_pdf)

    resume = convert_resume_file_to_json(
        source_path,
        "project_management",
        tmp_path,
        parser=parser,
    )

    assert resume.name == "Jane Candidate"
    assert (tmp_path / "base_resume_project_management.json").exists()


def test_convert_resume_file_to_json_routes_docx_text_through_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "starter_construction.docx"
    source_path.write_bytes(b"docx bytes")

    def fake_extract_docx(path: Path) -> str:
        assert path == source_path
        return "extracted docx resume text"

    def parser(raw_text: str, category: str) -> dict[str, object]:
        assert raw_text == "extracted docx resume text"
        assert category == "construction"
        return VALID_RESUME_DATA

    monkeypatch.setattr("src.resume_converter._extract_docx_text", fake_extract_docx)

    resume = convert_resume_file_to_json(
        source_path,
        "construction",
        tmp_path,
        parser=parser,
    )

    assert resume.name == "Jane Candidate"
    assert (tmp_path / "base_resume_construction.json").exists()


def test_convert_resume_file_to_json_rejects_unsupported_extension(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "starter_engineering.rtf"
    source_path.write_text("resume text", encoding="utf-8")

    with pytest.raises(UnsupportedResumeFormatError, match="Supported formats"):
        convert_resume_file_to_json(source_path, "engineering", tmp_path)

    assert not (tmp_path / "base_resume_engineering.json").exists()
