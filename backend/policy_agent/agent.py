
import json
import os
from pathlib import Path

from deepagents import create_deep_agent
from langchain_groq import ChatGroq
from langchain_core.tools import tool

from policy_agent.research import (
    search_web,
    run_research,
    collect_evidence,
    compare_evidence,
)
from policy_agent.skills import list_skills, get_skill


@tool
def search_policy_sources(query: str, limit: int = 5) -> list[dict]:
    """Search the web for climate and environmental policy sources."""
    return search_web(query, max(3, min(limit, 10)))


@tool
def research_policy_question(
    question: str,
    location: str = "India",
    max_results: int = 6,
) -> dict:
    """Research a climate policy question using linked sources."""
    return run_research(
        question, location, max(4, min(max_results, 8))
    )


@tool
def compare_policy_evidence(
    question: str,
    location: str = "India",
    max_results: int = 6,
) -> dict:
    """Compare policy actions extracted from multiple sources."""
    evidence = collect_evidence(
        question, location, max(4, min(max_results, 8))
    )
    return compare_evidence(evidence)


@tool
def load_research_skill(name: str) -> dict:
    """Load a project skill, such as policy-synthesis."""
    return get_skill(name)


@tool
def list_research_skills() -> list[dict]:
    """List the available climate policy research skills."""
    return list_skills()


def create_policy_agent():
    api_key = os.getenv("GROQ_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing in Render environment variables."
        )

    model_name = os.getenv(
        "GROQ_MODEL", "openai/gpt-oss-120b"
    )

    model = ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=0,
        max_retries=2,
    )

    skills_folder = (
        Path(__file__).resolve().parent.parent / "skills"
    )

    skill_files = sorted(skills_folder.glob("*.md"))
    skill_text = "\n\n".join(
        f"### {path.stem}\n"
        f"{path.read_text(encoding='utf-8')}"
        for path in skill_files
    )

    instructions = """
You are a climate policy research assistant focused on India and Goa.

Use research tools when current evidence is needed.
Use the supplied project skills to guide your research.
Never invent policies, dates, targets, statistics, sources or quotations.
Distinguish policy commitments from measured outcomes.
Identify conflicting evidence, missing information and implementation
challenges.
Prefer official government sources and reputable academic research.
Clearly identify information based only on a search snippet.
Cite source titles and URLs supplied by the research tools.
Do not claim that a policy is effective merely because a source describes it.
Give a clear, concise, evidence-based answer.
"""

    return create_deep_agent(
        model=model,
        tools=[
            search_policy_sources,
            research_policy_question,
            compare_policy_evidence,
            load_research_skill,
            list_research_skills,
        ],
        system_prompt=(
            instructions + "\n\nPROJECT SKILLS:\n" + skill_text
        ),
    )


def synthesize_policy_question(
    question: str,
    location: str,
    research: dict,
) -> str:
    """Synthesize retrieved climate-policy evidence with Deep Agents."""

    agent = create_policy_agent()

    prompt = f"""
Research question: {question}
Geographic focus: {location}

Retrieved research evidence:
{json.dumps(research, ensure_ascii=False)[:24000]}

Write a synthesis covering:
1. Main policy actions and targets.
2. Comparison of relevant approaches.
3. Implementation challenges.
4. Conflicting, weak or missing evidence.
5. Practical conclusion.

Base factual claims on the supplied evidence. You may use the research
tools if more evidence is needed. Include source titles and URLs.
Do not claim causation or policy effectiveness without supporting evidence.
"""

    result = agent.invoke({
        "messages": [
            {"role": "user", "content": prompt}
        ]
    })

    for message in reversed(result.get("messages", [])):
        if getattr(message, "type", "") == "ai":
            content = message.content

            if isinstance(content, str) and content.strip():
                return content

            if isinstance(content, list):
                text_parts = [
                    item["text"]
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") == "text"
                    and item.get("text")
                ]
                if text_parts:
                    return "\n".join(text_parts)

    return "The agent did not return a synthesis. Check the Render logs."
