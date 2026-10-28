
import json
import os

from deepagents import create_deep_agent
from langchain_groq import ChatGroq


def create_policy_agent():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing in Render environment variables."
        )

    model = ChatGroq(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        api_key=api_key,
        temperature=0,
        max_retries=1,
    )

    instructions = """
You are a climate policy research assistant focused on India and Goa.
Use only the evidence supplied in the user's message.
Do not invent policies, dates, targets, statistics or sources.
Distinguish policy commitments from measured outcomes.
Mention uncertainty, missing evidence and implementation challenges.
Cite source titles and URLs provided in the evidence.
Do not claim a policy is effective without supporting evidence.
Keep the answer concise and structured.
"""

    # No extra tools are needed: research has already been performed.
    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=instructions,
    )


def synthesize_policy_question(
    question: str,
    location: str,
    research: dict,
) -> str:
    """Summarize a compact, source-linked selection of research evidence."""

    sources = []
    for source in research.get("sources", [])[:4]:
        passages = [
            item.get("text", "")[:350]
            for item in source.get("passages", [])[:1]
            if item.get("text")
        ]

        sources.append({
            "title": source.get("title", ""),
            "url": source.get("url", ""),
            "source_type": source.get("source_type", ""),
            "evidence_basis": source.get("evidence_basis", ""),
            "snippet": source.get("snippet", "")[:250],
            "passages": passages,
        })

    evidence = {
        "recommendations": [
            {
                "recommendation": item.get("recommendation", "")[:350],
                "support_level": item.get("support_level", ""),
                "sources": [
                    {
                        "title": source.get("title", ""),
                        "url": source.get("url", ""),
                    }
                    for source in item.get("sources", [])[:2]
                ],
            }
            for item in research.get("recommendations", [])[:4]
        ],
        "sources": sources,
        "limitations": research.get("limitations", [])[:3],
    }

    prompt = f"""
Question: {question}
Geographic focus: {location}

Evidence (JSON):
{json.dumps(evidence, ensure_ascii=False)}

Write a concise synthesis with:
1. Main policy actions.
2. Comparison of approaches.
3. Implementation challenges.
4. Evidence gaps and limitations.
5. Practical conclusion.

Cite source titles and URLs from the evidence.
If the evidence is insufficient, say so clearly.
Do not invent missing facts.
"""

    agent = create_policy_agent()
    result = agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    })

    for message in reversed(result.get("messages", [])):
        if getattr(message, "type", "") == "ai":
            content = message.content
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                parts = [
                    item["text"]
                    for item in content
                    if isinstance(item, dict)
                    and item.get("type") == "text"
                    and item.get("text")
                ]
                if parts:
                    return "\n".join(parts)

    return "No synthesis was returned. Check the Render API logs."
