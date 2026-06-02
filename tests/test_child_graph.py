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
        evaluate_response = EvaluateFitOutput(questions=[], fit_score=8, should_apply=True, missing_requirements=[])
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



def test_child_graph_human_review_approval_triggers_apply_changes():
    test_graph = _compile_graph()
    config = {"configurable": {"thread_id": "child-graph-apply-changes"}}

    # Initial state mimicking what's passed from strategy_generator
    initial_state = _state()
    initial_state["status"] = JobStatus.STRATEGY_DRAFTED
    initial_state["strategy_markdown"] = "Some strategy"
    initial_state["resume_diffs"] = ResumeDiffSchema(
        changes=[
            {
                "action": "replace",
                "section": "professional_summary",
                "old_value": "Backend engineer with Python experience.",
                "new_value": "Senior Python engineer specializing in API services.",
                "reason": "Aligns the summary with the target role.",
            }
        ]
    )

    # We manually push the state up to human_review
    # Actually, we can just run a single node or start from human_review.
    # Since human_review is a HITL interrupt, if we provide the state to stream with None it starts from the beginning.
    # Better approach: initialize checkpointer with a state where next is apply_changes, or simulate resume.
    
    # Let's mock nodes so we can do a full run from start to apply_changes
    with (
        mock.patch("src.nodes.evaluate_fit_node.ChatOpenAI") as mock_evaluate_chat,
        mock.patch("src.nodes.strategy_generator_node.ChatOpenAI") as mock_strategy_chat,
        mock.patch("src.nodes.cover_letter_generator_node.ChatOpenAI") as mock_cover_letter_chat,
        mock.patch("src.nodes.child_nodes.pdf_compiler") as mock_pdf_compiler
    ):
        evaluate_instance = mock.MagicMock()
        evaluate_structured = mock.MagicMock()
        eval_resp = EvaluateFitOutput(questions=[], fit_score=8, should_apply=True, missing_requirements=[])
        evaluate_structured.invoke.return_value = eval_resp
        evaluate_structured.return_value = eval_resp
        evaluate_instance.with_structured_output.return_value = evaluate_structured
        mock_evaluate_chat.return_value = evaluate_instance

        strategy_instance = mock.MagicMock()
        strategy_structured = mock.MagicMock()
        strat_resp = StrategyGeneratorOutput(
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
        strategy_structured.invoke.return_value = strat_resp
        strategy_structured.return_value = strat_resp
        strategy_instance.with_structured_output.return_value = strategy_structured
        mock_strategy_chat.return_value = strategy_instance
        
        from langchain_core.messages import AIMessage
        mock_cover_llm_instance = mock.MagicMock()
        mock_cover_llm_instance.invoke.return_value = AIMessage(content="Letter")
        mock_cover_llm_instance.return_value = AIMessage(content="Letter")
        mock_cover_letter_chat.return_value = mock_cover_llm_instance
        mock_pdf_compiler.return_value = {"resume_pdf_path": "resume.pdf"}

        # Run to human_review interrupt
        for _ in test_graph.stream(_state(), config=config):
            pass

        state_snapshot = test_graph.get_state(config)
        assert state_snapshot.next == ("human_review",)
        
        # Now simulate user approving by updating state and resuming
        test_graph.update_state(config, {"status": JobStatus.APPROVED})
        for _ in test_graph.stream(None, config=config):
            pass
            
        final_state = test_graph.get_state(config)
        # Graph should have completed
        assert not final_state.next
        
        tailored_resume = final_state.values.get("tailored_resume")
        assert tailored_resume is not None
        
        # It's a BaseResumeSchema
        from src.schemas import BaseResumeSchema
        if isinstance(tailored_resume, dict):
            tailored_resume = BaseResumeSchema.model_validate(tailored_resume)
            
        assert tailored_resume.professional_summary == "Senior Python engineer specializing in API services."

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
            questions=[ClarificationQuestion(id="1", type="text", question="Q", options=[])],
            fit_score=8, should_apply=True, missing_requirements=[]
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
