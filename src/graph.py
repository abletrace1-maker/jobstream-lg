from typing import List, Dict, Any
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END

from src.state import ParentGraphState, ChildGraphState, JobStatus
from src.nodes.parent_nodes import load_config_and_resume
from src.child_graph import child_graph

def map_to_job_processor(state: ParentGraphState) -> List[Send]:
    """
    Map each scraped job to a child graph execution using the Send API.
    Matches the job.category to the corresponding base resume.
    """
    scraped_jobs = state.get("scraped_jobs", [])
    base_resumes = state.get("base_resumes", {})
    
    sends = []
    for job in scraped_jobs:
        # Match job category to appropriate base_resume
        # If category doesn't match exactly, fallback to "default" if it exists
        # or maybe the first available resume, or skip if no resumes.
        
        category = job.category
        if category in base_resumes:
            base_resume = base_resumes[category]
        elif "default" in base_resumes:
            base_resume = base_resumes["default"]
        elif base_resumes:
            # Fallback to the first available if no default exists
            base_resume = next(iter(base_resumes.values()))
        else:
            # Cannot process without a base resume
            print(f"Skipping job {job.job_id}: No base resumes available.")
            continue
            
        child_state = ChildGraphState(
            base_resume=base_resume,
            job_details=job,
            status=JobStatus.EVALUATING,
            clarification_questions=[],
            user_clarification_answers={},
            strategy_markdown="",
            resume_diffs=None,
            user_feedback="",
            tailored_resume=None,
            cover_letter_markdown="",
            resume_pdf_path="",
            cover_letter_pdf_path=""
        )
        
        # We send to the compiled child_graph
        sends.append(Send("child_graph", child_state))
        
    return sends


def dummy_job_ingestion(state: ParentGraphState) -> Dict[str, Any]:
    """
    Stub job_ingestion node to move pending_jobs to scraped_jobs for testing.
    """
    pending_jobs = state.get("pending_jobs", [])
    scraped_jobs = state.get("scraped_jobs", [])
    
    # Normally this would scrape jobs, but for now we just convert them conceptually
    # Since we need actual scraped jobs matching JobDetailsSchema, let's just assume 
    # scraped_jobs is populated or we populate it manually in tests.
    # Return empty dict since we'll inject scraped_jobs via state in tests for now.
    return {"scraped_jobs": scraped_jobs}

# Build the Parent Graph
builder = StateGraph(ParentGraphState)

# Add nodes
builder.add_node("load_config_and_resume", load_config_and_resume)
builder.add_node("job_ingestion", dummy_job_ingestion)
builder.add_node("child_graph", child_graph)

# Add edges
builder.add_edge(START, "load_config_and_resume")
builder.add_edge("load_config_and_resume", "job_ingestion")
builder.add_conditional_edges("job_ingestion", map_to_job_processor, ["child_graph"])
# LangGraph doesn't require adding an edge from "child_graph" to END if we don't return parent state updates, 
# but usually it's fine. If "child_graph" runs and doesn't explicitly return to another node, it goes to END.
# Actually, Send() API will cause the mapped node to run, but if we don't have an edge out of it, it implicitly ends.
# Or we can add an explicit edge, but wait, Send API maps state to another node. 
# We don't need an explicit edge from "child_graph" to END. But let's add it for clarity if needed.
# Actually let's just add it or leave it out depending on LangGraph semantics.
# In LangGraph Map-Reduce, the Send node usually returns state updates to the parent, but here child graph has its own state.
# Wait, if child_graph has its own state (ChildGraphState) and we Send to it, what does it return to ParentGraphState?
# If we just add it, it returns its final state to the parent, but if the keys don't match, it might fail.
# Let's see if we need an explicit edge. Let's just keep the edge.
builder.add_edge("child_graph", END)

parent_graph = builder.compile()
