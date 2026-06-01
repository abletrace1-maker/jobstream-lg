import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.schemas import ResumeDiffSchema, StrategyGeneratorOutput
from src.state import ChildGraphState, JobStatus

STRATEGY_GENERATOR_PROMPT = """You are an expert resume strategist.
Generate a synchronized tailoring strategy and exact resume diffs for one job application.

Rules:
- The strategy_markdown must be human-readable and describe every proposed resume change.
- The resume_diffs must contain the exact same proposed changes using the ResumeDiffSchema field names.
- Use only grounded information from the base_resume, job_details, and user_clarification_answers.
- Do not invent employment history, education, credentials, dates, companies, titles, or contact details.
- Prefer concise, ATS-friendly wording aligned to the job requirements.

Base Resume JSON:
{base_resume}

Job Details JSON:
{job_details}

{clarification_guidance}
"""


def _to_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    return json.dumps(value, indent=2, default=str)


def _format_clarification_guidance(answers: Dict[str, str] | None) -> str:
    if not answers:
        return "No user clarification answers were provided. Generate the strategy from base_resume and job_details only."

    formatted_answers = "\n".join(f"- {question_id}: {answer}" for question_id, answer in answers.items())
    return f"HIGH-PRIORITY USER CLARIFICATION ANSWERS:\n{formatted_answers}"


def strategy_generator(state: ChildGraphState) -> Dict[str, Any]:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
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
        }
    )
    response = structured_llm.invoke(prompt_value)

    resume_diffs = response.resume_diffs
    if not isinstance(resume_diffs, ResumeDiffSchema):
        resume_diffs = ResumeDiffSchema.model_validate(resume_diffs)

    return {
        "strategy_markdown": response.strategy_markdown,
        "resume_diffs": resume_diffs,
        "status": JobStatus.STRATEGY_DRAFTED.value,
    }
