from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from src.state import ChildGraphState
from src.schemas import EvaluateFitOutput

# Define the prompt (T-1)
EVALUATE_FIT_PROMPT = """You are an expert technical recruiter and career coach.
Your task is to evaluate the fit between the candidate's base resume and the job description.

Key Directives:
1. Scoring: Provide a realistic 1-10 fit score. If the score is below a threshold of 3/10, set should_apply to false.
2. Gap Analysis: Identify key job requirements that are completely missing from the base resume.
3. Question Generation: For every missing critical requirement or missing context, generate a clarification question for the human in the loop. Avoid hallucinations by asking the human for missing facts instead of inventing them.
4. Always Provide LLM Option: Every multiple-choice question MUST include an option that exactly says "Let LLM decide".

Base Resume:
{base_resume}

Job Details:
{job_details}
"""

def evaluate_fit(state: ChildGraphState) -> Dict[str, Any]:
    """
    Evaluate fit between base resume and job description, and generate structured clarification questions.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(EvaluateFitOutput)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", EVALUATE_FIT_PROMPT),
        ("human", "Evaluate the fit and provide clarification questions if necessary.")
    ])
    
    chain = prompt | structured_llm
    
    response = chain.invoke({
        "base_resume": state.get("base_resume", {}),
        "job_details": state.get("job_details", {})
    })
    
    # For US-001/US-002, we return the parsed questions and update status
    if not response:
        return {"status": "EVALUATING", "clarification_questions": []}

    if not response.should_apply:
        status = "REJECTED"
    elif response.questions:
        status = "NEEDS_CLARIFICATION"
    else:
        status = "EVALUATING"
    
    return {"status": status, "clarification_questions": response.questions}
