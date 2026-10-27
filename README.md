# Climate Policy Agent — MCP, tools and skills

A research-support prototype for climate change, air pollution and environmental policy in India, including Goa-specific queries. The website and MCP server use the same live research functions.

## What is implemented
- Three live Serper searches per question: official-domain-focused, research-focused, and implementation/policy-focused.
- Public source-page fetching and text extraction where the publisher allows it.
- Relevance scoring and extraction of policy/action passages.
- Grouping similar passages and retaining their source citations; displays multiple-source, single-source and snippet-only support levels.
- MCP tools: `search_policy_sources`, `read_policy_source`, `research_policy_question`, `compare_policy_evidence`, `list_research_skills`, `load_research_skill`.
- Reusable Markdown skills: climate policy research, source quality review and evidence-linked policy synthesis.
- FastAPI web API, simple static website, tests and GitHub Actions workflow.

## Honest limitations
This project is not an LLM-based synthesizer. It extracts and groups relevant action statements; it cannot independently prove policy effectiveness or reliably resolve conflicting studies. Some sites block automated access. Source-domain classification is only a hint. Always open cited sources and check dates, jurisdiction, methods and legal status. Serper usage consumes account quota.

## Local setup (Windows PowerShell)
From the project root:
```powershell
cd backend
py -m venv .venv
.venv\\Scripts\\Activate.ps1
python -m pip install -r requirements.txt
$env:SERPER_API_KEY="YOUR_REAL_SERPER_KEY"
$env:FRONTEND_ORIGIN="*"
python -m uvicorn main:app --reload
```
Test `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`.

Open a second terminal from the repository root:
```powershell
cd website
python -m http.server 5500
```
Open `http://localhost:5500`. For local use, `website/app.js` defaults to `http://127.0.0.1:8000`.

## Run the MCP server locally
In another terminal:
```powershell
cd backend
.venv\\Scripts\\Activate.ps1
$env:SERPER_API_KEY="YOUR_REAL_SERPER_KEY"
python mcp_server.py
```
The default is MCP stdio transport, for MCP-compatible clients. Do not run this in the same terminal as Uvicorn.

## Deploy
1. Push this repository to a new GitHub repo. Do not overwrite the original.
2. Deploy the API using Render and the included `render.yaml`, or create a web service with root `backend`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`. Add `SERPER_API_KEY`.
3. Publish `website/` on GitHub Pages. If Pages cannot use a subfolder as its source, copy the three website files to the repository root or configure a Pages workflow.
4. Edit `website/app.js` and set `API_BASE_URL` to the actual deployed Render API URL.
5. Set `FRONTEND_ORIGIN` in Render to the GitHub Pages origin, e.g. `https://USERNAME.github.io` (origin only).
6. To deploy MCP as a separate Render web service, set root directory `backend`, build command `pip install -r requirements.txt`, start command `python mcp_server.py`, and environment `MCP_HTTP=1` plus `SERPER_API_KEY`. Use the deployed MCP endpoint with a compatible MCP client. Confirm the service's `/mcp` endpoint in Render logs and MCP client settings.

## GitHub Actions
On push and pull request, `.github/workflows/tests.yml` installs dependencies and runs the offline unit tests. Live search tests require a real Serper key and are intentionally not run in CI.

## Security
Never commit your Serper key or add it to frontend JavaScript. Set it only as a local environment variable or hosting secret. If exposed, revoke and rotate it.
