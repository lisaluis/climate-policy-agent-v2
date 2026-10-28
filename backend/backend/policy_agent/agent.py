
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
    """Search multiple sources and return evidence-linked policy findings."""
    return run_research(
        question, location, max(4, min(max_results, 8))
    )


@tool
def compare_policy_evidence(
    question: str,
    location: str = "India",
    max_results: int = 6,
) -> dict:
    """Compare extracted policy actions across multiple sources."""
    evidence = collect_evidence(
        question, location, max(4, min(max_results, 8))
    )
    return compare_evidence(evidence)


@tool
def load_research_skill(name: str) -> dict:
    """Load a project skill by name, such as policy-synthesis."""
    return get_skill(name)


@tool
def list_research_skills() -> list[dict]:
    """List the available climate policy research skills."""
    return list_skills()


def create_policy_agent():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing in Render environment variables.")

    model_name = os.getenv(
        "GROQ_MODEL", "openai/gpt-oss-120b"
    )

    model = ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=0,
        max_retries=2,
    )

    skill_folder = Path(__file__).resolve().parent.parent / "skills"
    skill_files = sorted(skill_folder.glob("*.md"))
    skill_text = "\n\n".join(
        f"### {p.stem}\n{p.read_text(encoding='utf-8')}"
        for p in skill_files
    )

    instructions = """
You are a climate policy research assistant focused on India and Goa.

Use the available research tools when current evidence is needed.
Use the project research skills supplied below.
Never invent policies, dates, targets, statistics, sources, or quotations.
Distinguish official policy commitments from evidence of actual outcomes.
Identify disagreements, missing evidence, and implementation challenges.
Prefer primary government sources and reputable academic research.
Clearly explain when a source provides only a search snippet.

Return a concise, evidence-based synthesis. Cite sources using their
provided titles and URLs. Do not claim that a policy is effective merely
because a source describes it.
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
        system_prompt=instructions + "\n\nPROJECT SKILLS:\n" + skill_text,
    )


def synthesize_policy_question(question: str, location: str, research: dict) -> str:
    """Use Deep Agents to synthesize retrieved evidence."""
    agent = create_policy_agent()

    prompt = f"""
Research question: {question}
Geographic focus: {location}

Retrieved evidence in JSON:
{json.dumps(research, ensure_ascii=False)[:24000]}

Synthesize the evidence into:
1. Main policy actions and targets.
2. Comparison of the relevant approaches.
3. Implementation challenges.
4. Conflicting, weak, or missing evidence.
5. Practical conclusion.

Use only facts supported by the supplied evidence. You may call the research
tools if more evidence is needed. Include source titles and URLs when relevant.
Do not claim that a policy caused a measured result unless the evidence supports it.
"""

    result = agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    messages = result.get("messages", [])
    for message in reversed(messages):
        if getattr(message, "type", "") == "ai" and message.content:
            if isinstance(message.content, str):
                return message.content
            return json.dumps(message.content, ensure_ascii=False)

    return "The agent did not return a synthesis. Please inspect the API logs."
