import os, re
from collections import Counter
from urllib.parse import urlparse
from typing import Any
import requests
from bs4 import BeautifulSoup

SERPER_URL = "https://google.serper.dev/search"
USER_AGENT = "ClimatePolicyAgent/2.0 (educational research prototype)"
STOPWORDS = set("""a an and are as at be by for from has have how in into is it its of on or our
that the their this to was what when where which who why will with could would should can
help reduce improve policy policies india indian goa about against""".split())
OFFICIAL_HINTS = (".gov.in", "cpcb.nic.in", "moef.gov.in", "pib.gov.in", "goa.gov.in",
                  "gspcb.goa.gov.in", "niti.gov.in", "who.int", "ipcc.ch", "unep.org", "worldbank.org")
RESEARCH_HINTS = ("nature.com", "sciencedirect.com", "springer.com", "pubmed.ncbi.nlm.nih.gov",
                  "frontiersin.org", "tandfonline.com", "wiley.com", ".edu", ".ac.in")

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")

def classify_source(host: str) -> str:
    h = host.lower()
    if any(x in h for x in OFFICIAL_HINTS):
        return "Official/intergovernmental domain — verify the specific document"
    if any(x in h for x in RESEARCH_HINTS):
        return "Research/academic publisher — verify study and methods"
    return "Other publisher — verify author, methods and date"

def tokens(text: str) -> list[str]:
    return [x.lower() for x in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text)
            if x.lower() not in STOPWORDS]

def make_queries(question: str, location: str) -> list[str]:
    q, loc = clean(question), clean(location)
    return [
        f'{q} {loc} site:gov.in OR site:cpcb.nic.in OR site:moef.gov.in policy',
        f'{q} {loc} research study evidence environmental policy',
        f'{q} {loc} implementation plan guidelines programme policy'
    ]

def search_web(query: str, limit: int = 5) -> list[dict[str, Any]]:
    key = os.getenv("SERPER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("SERPER_API_KEY is missing in the backend environment.")
    try:
        r = requests.post(SERPER_URL, headers={"X-API-KEY": key, "Content-Type": "application/json"},
                          json={"q": query, "gl": "in", "hl": "en", "num": limit}, timeout=25)
        if r.status_code == 401:
            raise RuntimeError("Serper rejected the key. Check the key in the backend environment.")
        if r.status_code == 429:
            raise RuntimeError("Serper quota/rate limit reached.")
        r.raise_for_status()
        payload = r.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Serper search failed: {exc.__class__.__name__}") from exc
    out = []
    for item in payload.get("organic", []):
        url, title = clean(item.get("link", "")), clean(item.get("title", ""))
        if title and url and urlparse(url).scheme in ("http", "https"):
            out.append({"title": title, "url": url, "snippet": clean(item.get("snippet", "")),
                        "date": item.get("date"), "source": domain(url)})
    return out

def fetch_page(url: str) -> dict[str, str]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT,
                                       "Accept": "text/html,application/xhtml+xml"},
                         timeout=12, allow_redirects=True)
        if r.status_code >= 400:
            return {"status": f"Page unavailable (HTTP {r.status_code})", "text": ""}
        if "html" not in r.headers.get("content-type", "").lower():
            return {"status": "Not an HTML page; use source link/snippet", "text": ""}
        soup = BeautifulSoup(r.text[:2_000_000], "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
            tag.decompose()
        area = soup.find("main") or soup.find("article") or soup.body or soup
        body = clean(area.get_text(" ", strip=True))[:20000]
        return {"status": "Page text extracted" if len(body) > 250 else "Little readable page text", "text": body}
    except requests.RequestException:
        return {"status": "Page blocked, timed out or could not be fetched", "text": ""}

def sentence_score(text: str, terms: set[str]) -> int:
    words = tokens(text)
    counts = Counter(words)
    overlap = sum(min(counts[t], 3) for t in terms if t in counts)
    policy_terms = {"policy","programme","program","plan","standard","regulation","monitoring",
                    "emission","pollution","climate","adaptation","mitigation","action","implementation",
                    "guideline","strategy","control","assessment","target","management","scheme",
                    "waste","segregation","collection","burning","transport","energy"}
    return overlap * 3 + min(sum(1 for w in words if w in policy_terms), 8)

def read_source(result: dict[str, Any], question: str) -> dict[str, Any]:
    page = fetch_page(result["url"])
    terms = set(tokens(question))
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", page["text"])
    passages = []
    for s in sentences:
        s = clean(s)
        if 80 <= len(s) <= 900:
            score = sentence_score(s, terms)
            if score > 0:
                passages.append((score, s))
    passages.sort(reverse=True)
    selected, seen = [], set()
    for score, s in passages:
        k = s.lower()[:120]
        if k not in seen:
            seen.add(k)
            selected.append({"text": s, "relevance_score": score})
        if len(selected) >= 4:
            break
    return {**result, "source_type": classify_source(result["source"]),
            "page_status": page["status"], "page_read": bool(page["text"]),
            "evidence_basis": "Extracted webpage text" if selected else "Search snippet only",
            "passages": selected}

def collect_evidence(question: str, location: str = "India", max_results: int = 8) -> dict[str, Any]:
    queries = make_queries(question, location)
    all_results, seen = [], set()
    for q in queries:
        for result in search_web(q, limit=5):
            key = result["url"].split("#")[0].rstrip("/").lower()
            if key not in seen:
                seen.add(key)
                all_results.append(result)
    if not all_results:
        raise RuntimeError("No search results found. Try a more specific question.")
    # Include official and research sources first, while retaining a variety of publishers.
    all_results.sort(key=lambda x: 0 if classify_source(x["source"]).startswith("Official") else
                     1 if classify_source(x["source"]).startswith("Research") else 2)
    selected = [read_source(x, question) for x in all_results[:max_results]]
    return {"question": question, "location": location, "queries": queries, "sources": selected}

ACTION_TERMS = ("should", "recommend", "promote", "reduce", "improve", "implement", "establish",
                "develop", "strengthen", "monitor", "adopt", "ensure", "support", "regulate",
                "control", "manage", "encourage", "require", "prioritize", "prioritise",
                "phase out", "prevent", "collect", "segregat", "enforce", "integrat")
POLICY_TERMS = ("policy", "plan", "programme", "program", "scheme", "emission", "pollution",
                "climate", "environment", "monitor", "standard", "adaptation", "mitigation",
                "waste", "transport", "energy", "forest", "conservation", "air quality",
                "guideline", "regulation", "burning", "collection", "segregation")

def compare_evidence(research: dict[str, Any]) -> dict[str, Any]:
    """Extract and group policy-action passages; retain every source citation."""
    question = research["question"]
    terms = set(tokens(question))
    candidates = []
    for src in research["sources"]:
        passages = src.get("passages") or []
        if not passages and src.get("snippet"):
            passages = [{"text": src["snippet"], "relevance_score": sentence_score(src["snippet"], terms)}]
        for p in passages:
            text = clean(p["text"])
            low = text.lower()
            if any(v in low for v in ACTION_TERMS) and any(v in low for v in POLICY_TERMS):
                candidates.append({"text": text, "source": src, "score": p.get("relevance_score", 0)})
    candidates.sort(key=lambda x: x["score"], reverse=True)
    # Group exact/near-identical text, then merge source references where similar tokens overlap.
    groups = []
    for cand in candidates:
        words = set(tokens(cand["text"]))
        match = None
        for group in groups:
            overlap = len(words & group["_words"]) / max(1, len(words | group["_words"]))
            if overlap >= 0.48:
                match = group
                break
        citation = {"title": cand["source"]["title"], "url": cand["source"]["url"],
                    "domain": cand["source"]["source"], "source_type": cand["source"]["source_type"],
                    "evidence_basis": cand["source"]["evidence_basis"]}
        if match:
            if citation["url"] not in {c["url"] for c in match["sources"]}:
                match["sources"].append(citation)
            match["supporting_passages"].append(cand["text"])
        else:
            groups.append({"recommendation": cand["text"], "sources": [citation],
                           "supporting_passages": [cand["text"]], "_words": words, "_score": cand["score"]})
    results = []
    for g in groups[:8]:
        count = len(g["sources"])
        results.append({
            "recommendation": g["recommendation"],
            "support_level": "Found in multiple sources" if count >= 2 else
                             ("Single source" if g["sources"][0]["evidence_basis"] == "Extracted webpage text"
                              else "Snippet only — weak support"),
            "source_count": count,
            "sources": g["sources"],
            "supporting_passages": list(dict.fromkeys(g["supporting_passages"]))[:3],
            "caution": "This is an extracted policy/action statement, not proof of effectiveness. Check the full source, date, jurisdiction and implementation context."
        })
    return {"recommendations": results, "recommendation_status":
            "Policy/action passages were extracted and grouped from retrieved sources." if results else
            "No clear action passages could be extracted. Review source links/snippets or ask a more specific question."}

def run_research(question: str, location: str = "India", max_results: int = 8) -> dict[str, Any]:
    collected = collect_evidence(question, location, max_results)
    comparison = compare_evidence(collected)
    return {**collected, **comparison,
            "limitations": [
                "Search results can be incomplete, outdated or taken out of context.",
                "Some websites block automated access; those sources may provide only a search snippet.",
                "Source-type labels are domain heuristics, not a quality guarantee.",
                "This version uses extractive evidence comparison, not an LLM that resolves contradictions.",
                "A passage mentioning a policy does not establish that the policy is effective.",
                "Three Serper queries are attempted per question, so API credits may be consumed."
            ],
            "method": "Multi-query Serper search + webpage extraction + relevance scoring + source-linked passage grouping"}
