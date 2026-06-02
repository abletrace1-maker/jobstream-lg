import json
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.state import ChildGraphState

COVER_LETTER_GENERATOR_PROMPT = """You are an expert career coach and cover letter writer.
Your task is to draft a compelling, concise Cover Letter that complements the candidate's tailored resume.

Key Directives:
1. Targeting: Explicitly reference the `company_name` and `job_title` from the job details.
2. Alignment: Focus strictly on the requirements mentioned in the job description that match the candidate's tailored resume.
3. Tone: Maintain a professional, confident tone. Do NOT invent new experiences, hobbies, or traits. Avoid overly generic fluff ("I am a hard worker"). Keep it to 3-4 impactful paragraphs.

Tailored Resume JSON:
{tailored_resume}

Job Details JSON:
{job_details}

Strategy Markdown (For Context):
{strategy_markdown}
"""

def _to_json(value: Any) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump()
    return json.dumps(value, indent=2, default=str)

def cover_letter_generator(state: ChildGraphState) -> Dict[str, Any]:
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COVER_LETTER_GENERATOR_PROMPT),
            ("human", "Draft the cover letter in markdown format based on the tailored resume and job details."),
        ]
    )

    resume = state.get("tailored_resume") or state.get("base_resume")

    chain = prompt | llm | StrOutputParser()
    
    response = chain.invoke(
        {
            "tailored_resume": _to_json(resume),
            "job_details": _to_json(state.get("job_details", {})),
            "strategy_markdown": state.get("strategy_markdown", ""),
        }
    )

    return {
        "cover_letter_markdown": response,
    }
