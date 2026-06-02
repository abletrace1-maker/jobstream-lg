import json
import re
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from src.schemas import ResumeChange, ResumeDiffSchema, StrategyGeneratorOutput
from src.state import ChildGraphState, JobStatus

STRATEGY_GENERATOR_PROMPT = """You are an expert resume strategist.
Generate a synchronized tailoring strategy and exact resume diffs for one job application.

Rules:
- The strategy_markdown must be human-readable and describe every proposed resume change.
- The resume_diffs must contain the exact same proposed changes using the ResumeDiffSchema field names.
- Use only grounded information from the base_resume, job_details, and user_clarification_answers.
- Do not invent employment history, education, credentials, dates, companies, titles, or contact details.
- Prefer concise, ATS-friendly wording aligned to the job requirements.

Resume modification constraints:
{resume_constraints}

Base Resume JSON:
{base_resume}

Job Details JSON:
{job_details}

{clarification_guidance}
"""

DEFAULT_RESUME_CONSTRAINTS = {
    "allowed_sections_to_alter": [
        "professional_summary",
        "experience.highlights",
        "skills",
    ],
    "forbidden_sections": [
        "name",
        "contact_info",
        "experience.title",
        "experience.company",
        "experience.dates",
        "education",
    ],
    "rules": [
        "Never invent job experience or skills not present or implied in the base resume.",
        "Maintain the professional tone of the original resume.",
        "Match the stylistic structure of the starter resume.",
    ],
}

PATH_TOKEN_PATTERN = re.compile(r"([^.[\]]+)|\[(\d+)\]")


def _to_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    return json.dumps(value, indent=2, default=str)


def _format_clarification_guidance(answers: Dict[str, str] | None) -> str:
    if not answers:
        return "No user clarification answers were provided. Generate the strategy from base_resume and job_details only."

    formatted_answers = "\n".join(f"- {question_id}: {answer}" for question_id, answer in answers.items())
    return f"HIGH-PRIORITY USER CLARIFICATION ANSWERS:\n{formatted_answers}"


def _get_resume_constraints(state: ChildGraphState) -> dict[str, Any]:
    config = state.get("config", {})
    constraints = config.get("resume_constraints", {}) if isinstance(config, dict) else {}
    return {
        "allowed_sections_to_alter": constraints.get(
            "allowed_sections_to_alter",
            DEFAULT_RESUME_CONSTRAINTS["allowed_sections_to_alter"],
        ),
        "forbidden_sections": constraints.get(
            "forbidden_sections",
            DEFAULT_RESUME_CONSTRAINTS["forbidden_sections"],
        ),
        "rules": constraints.get("rules", DEFAULT_RESUME_CONSTRAINTS["rules"]),
    }


def _format_resume_constraints(constraints: dict[str, Any]) -> str:
    return _to_json(constraints)


def _parse_section_path(section: str) -> list[str | int]:
    tokens: list[str | int] = []
    for match in PATH_TOKEN_PATTERN.finditer(section):
        name, index = match.groups()
        if name is not None:
            tokens.append(name)
        else:
            tokens.append(int(index))
    if not tokens:
        raise ValueError(f"Invalid resume diff section path: {section}")
    return tokens


def _normalize_section_tokens(tokens: list[str | int]) -> list[str]:
    aliases = {
        "experience": "professional_experience",
        "education": "educational_experience",
        "title": "job_title",
        "dates": "date",
    }
    return [aliases.get(token, token) for token in tokens if isinstance(token, str)]


def _constraint_tokens(path: str) -> list[str]:
    return _normalize_section_tokens(_parse_section_path(path))


def _tokens_start_with(tokens: list[str], prefix: list[str]) -> bool:
    return tokens[: len(prefix)] == prefix


def _is_allowed_section(section_tokens: list[str], allowed_sections: list[str]) -> bool:
    for allowed_section in allowed_sections:
        allowed_tokens = _constraint_tokens(allowed_section)
        if allowed_tokens == ["professional_experience", "highlights"]:
            if (
                len(section_tokens) >= 2
                and section_tokens[0] == "professional_experience"
                and section_tokens[-1] == "highlights"
            ):
                return True
        elif _tokens_start_with(section_tokens, allowed_tokens):
            return True
    return False


def _is_forbidden_section(section_tokens: list[str], forbidden_sections: list[str]) -> bool:
    if any(token in {"job_title", "company", "start_date", "end_date", "date"} for token in section_tokens):
        return True

    for forbidden_section in forbidden_sections:
        forbidden_tokens = _constraint_tokens(forbidden_section)
        if forbidden_tokens == ["professional_experience", "date"]:
            if section_tokens[:1] == ["professional_experience"] and any(
                token in {"start_date", "end_date", "date"} for token in section_tokens
            ):
                return True
        elif _tokens_start_with(section_tokens, forbidden_tokens):
            return True
    return False


def _resolve_resume_path(base_resume: Any, tokens: list[str | int]) -> Any:
    current = base_resume.model_dump() if isinstance(base_resume, BaseModel) else base_resume
    for token in tokens:
        if isinstance(token, int):
            if not isinstance(current, list) or token >= len(current):
                raise ValueError(f"Resume diff section path does not exist: {tokens}")
            current = current[token]
            continue

        if not isinstance(current, dict) or token not in current:
            raise ValueError(f"Resume diff section path does not exist: {tokens}")
        current = current[token]
    return current


def _old_value_matches(target_value: Any, old_value: str) -> bool:
    if isinstance(target_value, list):
        return old_value in target_value
    return str(target_value) == old_value


def _validate_resume_change(
    change: ResumeChange,
    base_resume: Any,
    constraints: dict[str, Any],
) -> None:
    path_tokens = _parse_section_path(change.section)
    section_tokens = _normalize_section_tokens(path_tokens)
    allowed_sections = constraints["allowed_sections_to_alter"]
    forbidden_sections = constraints["forbidden_sections"]

    if _is_forbidden_section(section_tokens, forbidden_sections):
        raise ValueError(f"Unsafe resume diff targets forbidden section: {change.section}")

    if not _is_allowed_section(section_tokens, allowed_sections):
        raise ValueError(f"Unsafe resume diff targets non-allowed section: {change.section}")

    if change.action == "replace":
        target_value = _resolve_resume_path(base_resume, path_tokens)
        if not _old_value_matches(target_value, change.old_value):
            raise ValueError(f"Unsafe resume diff old_value does not match base_resume at {change.section}")


def _validate_resume_diffs(
    resume_diffs: ResumeDiffSchema,
    base_resume: Any,
    constraints: dict[str, Any],
) -> ResumeDiffSchema:
    for change in resume_diffs.changes:
        _validate_resume_change(change, base_resume, constraints)
    return resume_diffs


def strategy_generator(state: ChildGraphState) -> Dict[str, Any]:
    constraints = _get_resume_constraints(state)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
    structured_llm = llm.with_structured_output(StrategyGeneratorOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", STRATEGY_GENERATOR_PROMPT),
            ("human", "Draft the tailoring strategy and strict resume diffs."),
        ]
    )

    prompt_value = prompt.invoke(
        {
            "base_resume": _to_json(state.get("base_resume", {})),
            "job_details": _to_json(state.get("job_details", {})),
            "clarification_guidance": _format_clarification_guidance(
                state.get("user_clarification_answers", {})
            ),
            "resume_constraints": _format_resume_constraints(constraints),
        }
    )
    response = structured_llm.invoke(prompt_value)

    resume_diffs = response.resume_diffs
    if not isinstance(resume_diffs, ResumeDiffSchema):
        resume_diffs = ResumeDiffSchema.model_validate(resume_diffs)
    resume_diffs = _validate_resume_diffs(resume_diffs, state.get("base_resume", {}), constraints)

    return {
        "strategy_markdown": response.strategy_markdown,
        "resume_diffs": resume_diffs,
        "status": JobStatus.STRATEGY_DRAFTED.value,
    }
