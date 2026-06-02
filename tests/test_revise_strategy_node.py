from unittest.mock import MagicMock, patch


from src.nodes.revise_strategy_node import revise_strategy
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


def _state(feedback: str = "Please undo the summary changes.", config: dict | None = None) -> ChildGraphState:
    state = ChildGraphState(
        base_resume=_resume(),
        job_details=_job(),
        status=JobStatus.EVALUATING,
        clarification_questions=[],
        user_clarification_answers={},
        strategy_markdown="## Strategy\n- Align summary to Python APIs.",
        resume_diffs=ResumeDiffSchema(
            changes=[
                {
                    "action": "replace",
                    "section": "professional_summary",
                    "old_value": "Backend engineer with Python experience.",
                    "new_value": "Senior Python engineer specializing in API services.",
                    "reason": "Aligns the summary with the target role.",
                }
            ]
        ),
        user_feedback=feedback,
        tailored_resume=None,
        cover_letter_markdown="",
        resume_pdf_path="",
        cover_letter_pdf_path="",
    )
    if config is not None:
        state["config"] = config
    return state


def _output(change: dict | None = None) -> StrategyGeneratorOutput:
    changes = [change] if change else []
    return StrategyGeneratorOutput(
        strategy_markdown="## Updated Strategy\n- No summary changes.",
        resume_diffs=ResumeDiffSchema(changes=changes),
    )


def test_revise_strategy_returns_updated_markdown_and_diffs_and_clears_feedback():
    with patch("src.nodes.revise_strategy_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = _output()
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        updates = revise_strategy(_state())

    assert updates["strategy_markdown"] == "## Updated Strategy\n- No summary changes."
    assert isinstance(updates["resume_diffs"], ResumeDiffSchema)
    assert len(updates["resume_diffs"].changes) == 0
    assert updates["status"] == JobStatus.STRATEGY_DRAFTED.value
    assert updates["user_feedback"] == "" # Verify feedback is cleared
    mock_instance.with_structured_output.assert_called_once_with(StrategyGeneratorOutput)


def test_revise_strategy_prompt_includes_previous_strategy_diffs_and_feedback():
    with patch("src.nodes.revise_strategy_node.ChatGoogleGenerativeAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.invoke.return_value = _output()
        mock_instance.with_structured_output.return_value = mock_structured
        mock_chat.return_value = mock_instance

        revise_strategy(_state("Make the summary more aggressive."))

    prompt_text = mock_structured.invoke.call_args.args[0].to_string()
    assert "Make the summary more aggressive." in prompt_text
    assert "## Strategy" in prompt_text
    assert "Senior Python engineer specializing in API services." in prompt_text

