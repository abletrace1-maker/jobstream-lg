from unittest import mock

from langgraph.checkpoint.memory import MemorySaver

from src.child_graph import child_builder, child_graph
from src.schemas import (
    BaseResumeSchema,
    ClarificationQuestion,
    EvaluateFitOutput,
    JobDetailsSchema,
    ResumeDiffSchema,
    StrategyGeneratorOutput,
)
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



def _state() -> ChildGraphState:
    return ChildGraphState(
        base_resume=_resume(),
        job_details=_job(),
        status=JobStatus.EVALUATING,
        clarification_questions=[],
        user_clarification_answers={},
        strategy_markdown="",
        resume_diffs=None,
        user_feedback="",
        tailored_resume=None,
        cover_letter_markdown="",
        resume_pdf_path="",
        cover_letter_pdf_path="",
    )



def _compile_graph():
    return child_builder.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["clarification", "human_review"],
    )



def test_child_graph_compiles_with_expected_nodes():
    assert child_graph is not None
    nodes = child_graph.nodes.keys()
    expected_nodes = {
        "evaluate_fit",
        "clarification",
        "strategy_generator",
        "human_review",
        "apply_changes",
        "cover_letter",
        "pdf_compiler",
    }

    for node in expected_nodes:
        assert node in nodes



def test_child_graph_no_clarification_path_reaches_human_review_with_strategy_state():
    test_graph = _compile_graph()
    config = {"configurable": {"thread_id": "child-graph-no-clarification"}}

    with (
        mock.patch("src.nodes.evaluate_fit_node.ChatOpenAI") as mock_evaluate_chat,
        mock.patch("src.nodes.strategy_generator_node.ChatOpenAI") as mock_strategy_chat,
    ):
        evaluate_instance = mock.MagicMock()
        evaluate_structured = mock.MagicMock()
        evaluate_response = EvaluateFitOutput(questions=[])
        evaluate_structured.return_value = evaluate_response
        evaluate_structured.invoke.return_value = evaluate_response
        evaluate_instance.with_structured_output.return_value = evaluate_structured
        mock_evaluate_chat.return_value = evaluate_instance

        strategy_instance = mock.MagicMock()
        strategy_structured = mock.MagicMock()
        strategy_structured.invoke.return_value = StrategyGeneratorOutput(
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
        )
        strategy_instance.with_structured_output.return_value = strategy_structured
        mock_strategy_chat.return_value = strategy_instance

        for _ in test_graph.stream(_state(), config=config):
            pass

    state_snapshot = test_graph.get_state(config)
    assert state_snapshot.next == ("human_review",)
    assert state_snapshot.values["status"] == JobStatus.STRATEGY_DRAFTED.value
    assert state_snapshot.values["strategy_markdown"] == "## Strategy\n- Align summary to Python APIs."

    resume_diffs = ResumeDiffSchema.model_validate(state_snapshot.values["resume_diffs"])
    assert resume_diffs.changes[0].section == "professional_summary"
    assert state_snapshot.values["clarification_questions"] == []



def test_child_graph_clarification_path_interrupts_before_strategy_generation():
    test_graph = _compile_graph()
    config = {"configurable": {"thread_id": "child-graph-needs-clarification"}}

    with (
        mock.patch("src.nodes.evaluate_fit_node.ChatOpenAI") as mock_evaluate_chat,
        mock.patch("src.nodes.strategy_generator_node.ChatOpenAI") as mock_strategy_chat,
    ):
        evaluate_instance = mock.MagicMock()
        evaluate_structured = mock.MagicMock()
        evaluate_response = EvaluateFitOutput(
            questions=[ClarificationQuestion(id="1", type="text", question="Q", options=[])]
        )
        evaluate_structured.return_value = evaluate_response
        evaluate_structured.invoke.return_value = evaluate_response
        evaluate_instance.with_structured_output.return_value = evaluate_structured
        mock_evaluate_chat.return_value = evaluate_instance

        for _ in test_graph.stream(_state(), config=config):
            pass

    state_snapshot = test_graph.get_state(config)
    assert state_snapshot.next == ("clarification",)
    assert state_snapshot.values["status"] == JobStatus.NEEDS_CLARIFICATION.value
    assert len(state_snapshot.values["clarification_questions"]) == 1
    assert state_snapshot.values["strategy_markdown"] == ""
    assert state_snapshot.values["resume_diffs"] is None
    mock_strategy_chat.assert_not_called()
