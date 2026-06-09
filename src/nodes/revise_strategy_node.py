from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.schemas import StrategyGeneratorOutput, ResumeDiffSchema
from src.state import ChildGraphState, JobStatus
from src.nodes.strategy_generator_node import (
    _get_resume_constraints,
    _format_resume_constraints,
    _to_json,
    _validate_resume_diffs,
)

REVISE_STRATEGY_PROMPT = """You are an expert resume strategist.
The user has provided feedback on the current tailoring strategy and resume diffs.
Your objective is to update the strategy_markdown and resume_diffs to incorporate this feedback.

Rules:
- Treat the user_feedback as absolute priority. If they ask to undo a change, remove it from the diffs.
- The new strategy_markdown must be human-readable and describe the updated proposed changes.
- The new resume_diffs must contain the exact same proposed changes as the strategy, using the ResumeDiffSchema field names.
- Ensure the resulting JSON Diff still perfectly matches the templates.MD schema and targets valid JSON paths in the base resume.
- Do not invent employment history, education, credentials, dates, companies, titles, or contact details.

Resume modification constraints:
{resume_constraints}

Base Resume JSON:
{base_resume}

Job Details JSON:
{job_details}

Previous Strategy Markdown:
{previous_strategy}

Previous Resume Diffs:
{previous_diffs}

USER FEEDBACK:
{user_feedback}
"""

def revise_strategy(state: ChildGraphState) -> Dict[str, Any]:
    constraints = _get_resume_constraints(state)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
    structured_llm = llm.with_structured_output(StrategyGeneratorOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REVISE_STRATEGY_PROMPT),
            ("human", "Revise the tailoring strategy and resume diffs based on the user feedback."),
        ]
    )

    prompt_value = prompt.invoke(
        {
            "base_resume": _to_json(state.get("base_resume", {})),
            "job_details": _to_json(state.get("job_details", {})),
            "previous_strategy": state.get("strategy_markdown", ""),
            "previous_diffs": _to_json(state.get("resume_diffs", {})),
            "user_feedback": state.get("user_feedback", ""),
            "resume_constraints": _format_resume_constraints(constraints),
        }
    )
    response = structured_llm.invoke(prompt_value)

    resume_diffs = response.resume_diffs
    if not isinstance(resume_diffs, ResumeDiffSchema):
        resume_diffs = ResumeDiffSchema.model_validate(resume_diffs)
    resume_diffs = _validate_resume_diffs(resume_diffs, state.get("base_resume", {}), constraints)

    # Save resume_diffs to data/output/{job_id}/resume_diffs.json
    job_details = state.get("job_details")
    if job_details:
        job_id = job_details.get("job_id", "unknown_job") if isinstance(job_details, dict) else getattr(job_details, "job_id", "unknown_job")
        import os
        output_dir = os.path.join("data", "output", str(job_id))
        os.makedirs(output_dir, exist_ok=True)
        diffs_path = os.path.join(output_dir, "resume_diffs.json")
        try:
            with open(diffs_path, "w", encoding="utf-8") as f:
                f.write(_to_json(resume_diffs))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not save resume_diffs.json: {e}")

    return {
        "strategy_markdown": response.strategy_markdown,
        "resume_diffs": resume_diffs,
        "status": JobStatus.STRATEGY_DRAFTED.value,
        "user_feedback": "" # Clear the feedback after processing
    }
