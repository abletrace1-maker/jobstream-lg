import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from docx import Document
from pydantic import ValidationError
from pypdf import PdfReader

from src.schemas import BaseResumeSchema

Parser = Callable[[str, str], BaseResumeSchema | Mapping[str, Any]]
SUPPORTED_RESUME_EXTENSIONS = {".txt", ".pdf", ".docx"}
STARTER_RESUME_PATTERN = re.compile(r"^starter_(?P<category>[A-Za-z0-9][A-Za-z0-9_]*)$")


class ResumeConversionError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        category: str | None = None,
        source_path: Path | str | None = None,
    ) -> None:
        context = []
        if category:
            context.append(f"category='{category}'")
        if source_path:
            context.append(f"source_path='{source_path}'")
        if context:
            message = f"{message} ({', '.join(context)})"
        super().__init__(message)
        self.category = category
        self.source_path = Path(source_path) if source_path else None


class ResumeValidationError(ResumeConversionError):
    pass


class BatchResumeConversionError(ResumeConversionError):
    def __init__(
        self,
        failures: Mapping[str, ResumeConversionError],
        converted_resumes: Mapping[str, BaseResumeSchema],
    ) -> None:
        failure_details = "; ".join(
            f"{category}: {error}" for category, error in failures.items()
        )
        super().__init__(
            f"One or more starter resume conversions failed: {failure_details}"
        )
        self.failures = dict(failures)
        self.converted_resumes = dict(converted_resumes)


class UnsupportedResumeFormatError(ResumeConversionError):
    pass


class DuplicateStarterResumeError(ResumeConversionError):
    pass


def discover_starter_resumes(
    starter_dir: Path | str = Path("data/starter_resumes"),
) -> dict[str, Path]:
    discovered: dict[str, Path] = {}
    directory = Path(starter_dir)
    if not directory.exists():
        return discovered

    for source_path in sorted(path for path in directory.iterdir() if path.is_file()):
        if not source_path.stem.startswith("starter_"):
            continue
        if source_path.suffix.lower() not in SUPPORTED_RESUME_EXTENSIONS:
            supported_formats = ", ".join(sorted(SUPPORTED_RESUME_EXTENSIONS))
            raise UnsupportedResumeFormatError(
                f"Unsupported starter resume format '{source_path.suffix}' for "
                f"{source_path}. Supported formats: {supported_formats}."
            )
        match = STARTER_RESUME_PATTERN.fullmatch(source_path.stem)
        if not match:
            raise ValueError(
                f"Starter resume filename must match starter_[category].[ext]: "
                f"{source_path.name}"
            )
        category = match.group("category")
        if category in discovered:
            raise DuplicateStarterResumeError(
                f"Duplicate starter resumes for category '{category}': "
                f"{discovered[category]} and {source_path}"
            )
        discovered[category] = source_path

    return discovered


def convert_starter_resumes_to_json(
    starter_dir: Path | str = Path("data/starter_resumes"),
    output_dir: Path | str = Path("data/json_resumes"),
    parser: Parser | None = None,
) -> dict[str, BaseResumeSchema]:
    converted_resumes: dict[str, BaseResumeSchema] = {}
    failures: dict[str, ResumeConversionError] = {}
    for category, source_path in discover_starter_resumes(starter_dir).items():
        try:
            converted_resumes[category] = convert_resume_file_to_json(
                source_path,
                category,
                output_dir,
                parser,
            )
        except ResumeConversionError as error:
            failures[category] = error
        except Exception as error:
            failures[category] = ResumeConversionError(
                f"Starter resume conversion failed: {error}",
                category=category,
                source_path=source_path,
            )
    if failures:
        raise BatchResumeConversionError(failures, converted_resumes)
    return converted_resumes


def convert_resume_text(
    raw_text: str,
    category: str,
    parser: Parser | None = None,
) -> BaseResumeSchema:
    try:
        if parser:
            parsed_resume = parser(raw_text, category)
        else:
            parsed_resume = parse_plain_text_resume(raw_text, category)
        return validate_resume_data(parsed_resume, category=category)
    except ResumeConversionError:
        raise
    except Exception as error:
        raise ResumeConversionError(
            f"Resume conversion failed: {error}",
            category=category,
        ) from error


def validate_resume_data(
    resume_data: BaseResumeSchema | Mapping[str, Any],
    *,
    category: str,
    source_path: Path | str | None = None,
) -> BaseResumeSchema:
    if isinstance(resume_data, BaseResumeSchema):
        return resume_data
    try:
        return BaseResumeSchema.model_validate(resume_data)
    except ValidationError as error:
        raise ResumeValidationError(
            f"Converted resume failed BaseResumeSchema validation: {error}",
            category=category,
            source_path=source_path,
        ) from error


def write_base_resume_json(
    resume: BaseResumeSchema | Mapping[str, Any],
    category: str,
    output_dir: Path | str = Path("data/json_resumes"),
    source_path: Path | str | None = None,
) -> Path:
    validated_resume = validate_resume_data(
        resume,
        category=category,
        source_path=source_path,
    )
    output_path = Path(output_dir) / f"base_resume_{category}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        validated_resume.model_dump(),
        indent=2,
        ensure_ascii=False,
    ) + "\n"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            delete=False,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
        ) as temp_file:
            temp_file.write(payload)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = Path(temp_file.name)
        os.replace(temp_path, output_path)
    except Exception as error:
        if temp_path and temp_path.exists():
            temp_path.unlink()
        raise ResumeConversionError(
            f"Failed to write base resume JSON: {error}",
            category=category,
            source_path=source_path,
        ) from error
    return output_path


def convert_resume_text_to_json(
    raw_text: str,
    category: str,
    output_dir: Path | str = Path("data/json_resumes"),
    parser: Parser | None = None,
    source_path: Path | str | None = None,
) -> BaseResumeSchema:
    try:
        if parser:
            parsed_resume = parser(raw_text, category)
        else:
            parsed_resume = parse_plain_text_resume(raw_text, category)
        resume = validate_resume_data(
            parsed_resume,
            category=category,
            source_path=source_path,
        )
        write_base_resume_json(resume, category, output_dir, source_path)
    except ResumeConversionError:
        raise
    except Exception as error:
        raise ResumeConversionError(
            f"Resume conversion failed: {error}",
            category=category,
            source_path=source_path,
        ) from error
    return resume


def convert_resume_file_to_json(
    source_path: Path | str,
    category: str,
    output_dir: Path | str = Path("data/json_resumes"),
    parser: Parser | None = None,
) -> BaseResumeSchema:
    try:
        raw_text = extract_resume_text(source_path)
        return convert_resume_text_to_json(
            raw_text,
            category,
            output_dir,
            parser,
            source_path,
        )
    except UnsupportedResumeFormatError as error:
        raise UnsupportedResumeFormatError(
            str(error),
            category=category,
            source_path=source_path,
        ) from error
    except ResumeConversionError:
        raise
    except Exception as error:
        raise ResumeConversionError(
            f"Resume file conversion failed: {error}",
            category=category,
            source_path=source_path,
        ) from error


def extract_resume_text(source_path: Path | str) -> str:
    path = Path(source_path)
    extension = path.suffix.lower()
    if extension == ".txt":
        return path.read_text(encoding="utf-8")
    if extension == ".pdf":
        return _extract_pdf_text(path)
    if extension == ".docx":
        return _extract_docx_text(path)
    supported_formats = ", ".join(sorted(SUPPORTED_RESUME_EXTENSIONS))
    raise UnsupportedResumeFormatError(
        f"Unsupported starter resume format '{extension}' for {path}. "
        f"Supported formats: {supported_formats}."
    )


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(path)
    page_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(text for text in page_text if text)


def _extract_docx_text(path: Path) -> str:
    document = Document(str(path))
    return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text)


def parse_plain_text_resume(raw_text: str, category: str) -> BaseResumeSchema:
    lines = [line.strip() for line in raw_text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    if len(non_empty_lines) < 2:
        raise ValueError("Resume text must include a name and contact line")

    sections = _split_sections(non_empty_lines)
    contact_info = _parse_contact_line(non_empty_lines[1])
    experience_lines = sections.get("professional_experience", [])
    education_lines = sections.get("education", [])
    other_points = _parse_other_points(sections.get("awards", []), education_lines)

    resume = {
        "name": non_empty_lines[0],
        "contact_info": contact_info,
        "professional_summary": sections.get("professional_summary", ""),
        "skills": _parse_skills(sections.get("skills", [])),
        "professional_experience": _parse_professional_experience(experience_lines),
        "educational_experience": _parse_education(education_lines),
        "other_points": other_points,
    }
    return BaseResumeSchema.model_validate(resume)


def _split_sections(lines: list[str]) -> dict[str, Any]:
    sections: dict[str, Any] = {
        "professional_summary": "",
        "skills": [],
        "professional_experience": [],
        "education": [],
        "awards": [],
    }
    current_section: str | None = None

    for line in lines[2:]:
        normalized = line.lower()
        if normalized.startswith("professional summary"):
            sections["professional_summary"] = line.removeprefix("Professional Summary").strip()
            current_section = "professional_summary"
            continue
        if normalized == "core competencies & technical proficiencies":
            current_section = "skills"
            continue
        if normalized == "professional experience":
            current_section = "professional_experience"
            continue
        if normalized.startswith("education"):
            current_section = "education"
            education_remainder = line.removeprefix("Education").strip()
            if education_remainder:
                sections["education"].append(education_remainder)
            continue
        if normalized == "awards":
            current_section = "awards"
            continue

        if current_section == "professional_summary":
            sections["professional_summary"] = _join_text(sections["professional_summary"], line)
        elif current_section in {"skills", "professional_experience", "education", "awards"}:
            sections[current_section].append(line)

    return sections


def _parse_contact_line(contact_line: str) -> dict[str, str]:
    parts = [part.strip() for part in contact_line.split("|")]
    location = parts[0] if len(parts) > 0 else ""
    phone = parts[1] if len(parts) > 1 else ""
    email = parts[2] if len(parts) > 2 else ""
    linkedin = parts[3] if len(parts) > 3 else ""
    return {
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "location": location,
    }


def _parse_skills(skill_lines: list[str]) -> dict[str, list[str]]:
    skills: dict[str, list[str]] = {}
    for line in skill_lines:
        if ":" not in line:
            continue
        category, values = line.split(":", 1)
        skills[_normalize_skill_category(category)] = [
            value.strip().rstrip(".")
            for value in values.split(",")
            if value.strip()
        ]
    return skills


def _parse_professional_experience(experience_lines: list[str]) -> list[dict[str, Any]]:
    experiences: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in experience_lines:
        header = _parse_experience_header(line)
        if header:
            if current:
                experiences.append(current)
            current = header
            continue
        if current is not None:
            current["highlights"].append(line)

    if current:
        experiences.append(current)
    return experiences


def _parse_experience_header(line: str) -> dict[str, Any] | None:
    parts = [part.strip() for part in line.split("|")]
    if len(parts) != 3:
        return None
    company, location_and_title, date_range = parts
    location, job_title = _split_location_and_title(location_and_title)
    start_date, end_date = _split_date_range(date_range)
    return {
        "job_title": job_title,
        "company": company,
        "location": location,
        "start_date": start_date,
        "end_date": end_date,
        "highlights": [],
    }


def _split_location_and_title(value: str) -> tuple[str, str]:
    title_starters = (
        "Operations",
        "Project",
        "Founder",
        "Lead",
        "Senior",
        "Software",
        "Client",
        "Delivery",
        "Program",
        "Product",
        "Technical",
        "Architect",
        "Consultant",
        "Coordinator",
        "Manager",
        "Engineer",
        "Developer",
        "Analyst",
        "Specialist",
        "Director",
    )
    first_match: tuple[int, str] | None = None
    for starter in title_starters:
        marker = f" {starter}"
        index = value.find(marker)
        if index != -1 and (first_match is None or index < first_match[0]):
            first_match = (index, starter)
    if first_match:
        index, starter = first_match
        location = value[:index]
        title = value[index + 1 :]
        return location.strip(), title.strip()
    return value.strip(), ""


def _split_date_range(value: str) -> tuple[str, str]:
    parts = re.split(r"\s+[–-]\s+", value, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return value.strip(), ""


def _parse_education(education_lines: list[str]) -> list[dict[str, Any]]:
    if not education_lines:
        return []

    education_text = " ".join(education_lines)
    education_text = education_text.split("Certifications:", 1)[0].strip()
    if " – " in education_text:
        school, degree = education_text.split(" – ", 1)
    elif " - " in education_text:
        school, degree = education_text.split(" - ", 1)
    else:
        school, degree = education_text, ""

    return [
        {
            "degree": degree.strip(),
            "school": school.strip(),
            "start_date": "",
            "end_date": "",
            "awards": [],
        }
    ]


def _parse_other_points(award_lines: list[str], education_lines: list[str]) -> list[str]:
    other_points = [line for line in award_lines if line]
    education_text = " ".join(education_lines)
    if "Certifications:" in education_text:
        certification_text = education_text.split("Certifications:", 1)[1].strip()
        if certification_text:
            other_points.insert(0, f"Certification: {certification_text}")
    return other_points


def _normalize_skill_category(category: str) -> str:
    return category.strip().lower().replace(" & ", "_").replace(" ", "_")


def _join_text(existing: str, line: str) -> str:
    if existing:
        return f"{existing} {line}"
    return line
