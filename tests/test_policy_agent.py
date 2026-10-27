from policy_agent.research import classify_source, make_queries, compare_evidence

def test_search_queries_cover_policy_and_research():
    queries = make_queries("reduce air pollution", "Goa, India")
    assert len(queries) == 3
    assert any("site:gov.in" in q for q in queries)
    assert any("research study" in q for q in queries)

def test_source_classification_is_cautious():
    assert classify_source("cpcb.nic.in").startswith("Official")
    assert classify_source("nature.com").startswith("Research")
    assert "verify" in classify_source("facebook.com").lower()

def test_evidence_grouping_keeps_citations():
    evidence = {"question":"waste burning policy", "sources":[
        {"title":"Report A","url":"https://a.gov.in/a","source":"a.gov.in",
         "source_type":"Official", "evidence_basis":"Extracted webpage text",
         "snippet":"","passages":[{"text":"Cities should improve waste collection and prevent open waste burning through local action plans.","relevance_score":10}]},
        {"title":"Report B","url":"https://b.org/b","source":"b.org",
         "source_type":"Other", "evidence_basis":"Extracted webpage text",
         "snippet":"","passages":[{"text":"Cities should improve waste collection and prevent open waste burning through local action plans.","relevance_score":9}]}
    ]}
    result = compare_evidence(evidence)
    assert result["recommendations"]
    assert result["recommendations"][0]["source_count"] == 2
