from unittest.mock import MagicMock, patch

import pytest

from src.nodes import child_nodes
from src.nodes.strategy_generator_node import strategy_generator
from src.schemas import BaseResumeSchema, JobDetailsSchema, ResumeDiffSchema, StrategyGeneratorOutput
from src.state import ChildGraphState, JobStatus


def _resume() -> BaseResumeSchema:
    return BaseResumeSchema(
        name="Jane Doe",
        contact_info={"email": "jane@example.com", "phone": "123", "linkedin": "", "location": "Remote"},
        professional_summary="Backend engineer with Python experience.",
        skills={"languages": ["Python"], "tools": ["Docker"]},
        professional_experience=[
            {
                "job_title": "Software Engineer",
                "company": "Tech Corp",
                "location": "Remote",
                "start_date": "2020-01",
                "end_date": "Present",
                "highlights": ["Built Python services."],
            }
        ],
        educational_experience=[],
        other_points=[],
    )


def _job() -> JobDetailsSchema:
    return JobDetailsSchema(
        job_title="Senior Python Engineer",
        company="Acme",
        location="Remote",
        job_id="job-1",
        category="engineering",
        requirements=["Python", "APIs"],
        nice_to_haves=["Docker"],
        responsibilities=["Build backend services"],
        raw_text="Python API role",
    )


def _state(answers: dict[str, str] | None = None, config: dict | None = None) -> ChildGraphState:
    state = ChildGraphState(
        base_resume=_resume(),
        job_details=_job(),
        status=JobStatus.EVALUATING,
        clarification_questions=[],
        user_clarification_answers=answers or {},
        strategy_markdown="",
        resume_diffs=None,
        user_feedback="",
        tailored_resume=None,
        cover_letter_markdown="",
        resume_pdf_path="",
        cover_letter_pdf_path="",
    )
    if config is not None:
        state["config"] = config
    return state


def _output(change: dict | None = None) -> StrategyGeneratorOutput:
    return StrategyGeneratorOutput(
        strategy_markdown="## Strategy\n- Align summary to Python APIs.",
        resume_diffs=ResumeDiffSchema(
            changes=[
                change
                or {
                    "action": "replace",
                    "section": "professional_summary",
                    "old_value": "Backend engineer with Python experience.",
                    "new_value": "Senior Python engineer specializing in API services.",
                    "reason": "Aligns the summary with the target role.",
                }
            ]
        ),
    )


def test_strategy_generator_returns_markdown_diffs_and_status():
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = _output()
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        updates = strategy_generator(_state())

    assert updates["strategy_markdown"] == "## Strategy\n- Align summary to Python APIs."
    assert isinstance(updates["resume_diffs"], ResumeDiffSchema)
    assert updates["resume_diffs"].changes[0].section == "professional_summary"
    assert updates["status"] == JobStatus.STRATEGY_DRAFTED.value
    mock_instance.with_structured_output.assert_called_once_with(StrategyGeneratorOutput)


def test_strategy_generator_prompt_includes_clarification_answers_as_high_priority():
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = _output()
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        strategy_generator(_state({"q1": "Emphasize API platform work."}))

    prompt_text = mock_structured.invoke.call_args.args[0].to_string()
    assert "HIGH-PRIORITY USER CLARIFICATION ANSWERS" in prompt_text
    assert "q1: Emphasize API platform work." in prompt_text


def test_strategy_generator_prompt_handles_missing_clarification_answers():
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = _output()
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        updates = strategy_generator(_state())

    prompt_text = mock_structured.invoke.call_args.args[0].to_string()
    assert "No user clarification answers were provided" in prompt_text
    assert updates["status"] == JobStatus.STRATEGY_DRAFTED.value


def test_strategy_generator_prompt_includes_resume_constraints_from_config():
    config = {
        "resume_constraints": {
            "allowed_sections_to_alter": ["professional_summary"],
            "forbidden_sections": ["name", "contact_info"],
            "rules": ["Only update explicitly allowed sections."],
        }
    }
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = _output()
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        strategy_generator(_state(config=config))

    prompt_text = mock_structured.invoke.call_args.args[0].to_string()
    assert "allowed_sections_to_alter" in prompt_text
    assert "forbidden_sections" in prompt_text
    assert "Only update explicitly allowed sections." in prompt_text


def test_strategy_generator_allows_default_highlight_edit_with_matching_old_value():
    output = _output(
        {
            "action": "replace",
            "section": "professional_experience[0].highlights[0]",
            "old_value": "Built Python services.",
            "new_value": "Built Python API services aligned to product needs.",
            "reason": "Emphasizes API experience for the target role.",
        }
    )
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = output
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        updates = strategy_generator(_state())

    assert updates["resume_diffs"].changes[0].section == "professional_experience[0].highlights[0]"
    assert updates["status"] == JobStatus.STRATEGY_DRAFTED.value


def test_strategy_generator_rejects_forbidden_immutable_edit_without_drafted_status():
    output = _output(
        {
            "action": "replace",
            "section": "professional_experience[0].company",
            "old_value": "Tech Corp",
            "new_value": "Acme",
            "reason": "Unsafe company edit.",
        }
    )
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = output
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        with pytest.raises(ValueError, match="forbidden section"):
            strategy_generator(_state())


def test_strategy_generator_rejects_mismatched_old_value_without_drafted_status():
    output = _output(
        {
            "action": "replace",
            "section": "professional_summary",
            "old_value": "Wrong summary.",
            "new_value": "Senior Python engineer specializing in API services.",
            "reason": "Aligns the summary with the target role.",
        }
    )
    with patch("src.nodes.strategy_generator_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = output
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        with pytest.raises(ValueError, match="old_value does not match"):
            strategy_generator(_state())


def test_child_nodes_strategy_generator_delegates_to_implementation():
    assert child_nodes.strategy_generator is strategy_generator
