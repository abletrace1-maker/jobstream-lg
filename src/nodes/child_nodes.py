from typing import Any, Dict
import logging
from src.state import ChildGraphState
from src.nodes.evaluate_fit_node import evaluate_fit as evaluate_fit
from src.nodes.strategy_generator_node import strategy_generator as strategy_generator
from src.nodes.revise_strategy_node import revise_strategy as revise_strategy
from src.utils.diff_applier import apply_diffs
from src.schemas import BaseResumeSchema

logger = logging.getLogger(__name__)

def clarification(state: ChildGraphState) -> Dict[str, Any]:
    """Stub for handling human-in-the-loop clarification."""
    return {}

def human_review(state: ChildGraphState) -> Dict[str, Any]:
    """Stub for human-in-the-loop review of the strategy."""
    return {}

def apply_changes(state: ChildGraphState) -> Dict[str, Any]:
    """Applies diffs to the base resume."""
    base_resume = state.get("base_resume")
    resume_diffs = state.get("resume_diffs")
    
    if not base_resume:
        logger.warning("No base_resume found in state.")
        return {}
        
    if not resume_diffs or not hasattr(resume_diffs, "changes") or not resume_diffs.changes:
        logger.info("No resume_diffs to apply. Keeping original resume.")
        return {"tailored_resume": base_resume}
        
    # Convert models to dicts
    if hasattr(base_resume, "model_dump"):
        base_resume_dict = base_resume.model_dump()
    elif hasattr(base_resume, "dict"):
        base_resume_dict = base_resume.dict()
    else:
        base_resume_dict = base_resume
        
    diffs_list = []
    for change in resume_diffs.changes:
        if hasattr(change, "model_dump"):
            diffs_list.append(change.model_dump())
        elif hasattr(change, "dict"):
            diffs_list.append(change.dict())
        else:
            diffs_list.append(change)
            
    tailored_resume_dict = apply_diffs(base_resume_dict, diffs_list)
    
    # Parse back to BaseResumeSchema to match state type
    try:
        tailored_resume_obj = BaseResumeSchema.model_validate(tailored_resume_dict)
    except Exception as e:
        logger.error(f"Failed to validate tailored resume: {e}")
        tailored_resume_obj = tailored_resume_dict
        
    return {"tailored_resume": tailored_resume_obj}


def pdf_compiler(state: ChildGraphState) -> Dict[str, Any]:
    """Stub for compiling tailored resume and cover letter to PDF."""
    return {}
