"""MCP server exposing the same live research functions used by the website API.

Local default: stdio transport.
For a hosted MCP endpoint on Render, set MCP_HTTP=1; the server uses streamable HTTP.
"""
import os
from mcp.server.fastmcp import FastMCP
from policy_agent.research import search_web, read_source, run_research, collect_evidence, compare_evidence
from policy_agent.skills import list_skills, get_skill

mcp = FastMCP("Climate Policy Research Agent", host="0.0.0.0", port=int(os.getenv("PORT", "8001")))

@mcp.tool()
def search_policy_sources(query: str, limit: int = 5) -> list[dict]:
    """Search live web results through Serper. Returns titles, URLs, snippets, dates and domains."""
    return search_web(query, max(3, min(limit, 10)))

@mcp.tool()
def read_policy_source(title: str, url: str, snippet: str = "", date: str | None = None) -> dict:
    """Attempt to open one public source page and extract relevant text for policy research."""
    from policy_agent.research import domain
    result = {"title": title, "url": url, "snippet": snippet, "date": date, "source": domain(url)}
    return read_source(result, title)

@mcp.tool()
def research_policy_question(question: str, location: str = "India", max_results: int = 8) -> dict:
    """Run the full multi-query search, page extraction, and evidence-linked policy passage comparison."""
    return run_research(question, location, max(4, min(max_results, 10)))

@mcp.tool()
def compare_policy_evidence(question: str, location: str = "India", max_results: int = 8) -> dict:
    """Retrieve multiple sources and group similar policy-action passages with source citations."""
    evidence = collect_evidence(question, location, max(4, min(max_results, 10)))
    return compare_evidence(evidence)

@mcp.tool()
def list_research_skills() -> list[dict]:
    """List the policy research, source review and synthesis skills available to this agent."""
    return list_skills()

@mcp.tool()
def load_research_skill(name: str) -> dict:
    """Load a skill's full workflow instructions by name, for example policy-synthesis."""
    return get_skill(name)

if __name__ == "__main__":
    if os.getenv("MCP_HTTP", "0") == "1":
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
