# Architecture and design decisions

A request creates an immutable source snapshot plus issue text. LangGraph invokes inspect, propose and verify in order. Each stage saves an event and intermediate state. Inspect runs the existing unittest suite; propose requests structured JSON from Ollama (or chooses a known demo fix); policy checks restrict replacements; verify runs the same tests on the patched snapshot. The dashboard polls the saved record and exposes evidence downloads.

The API uses one worker and rejects overlapping requests with HTTP 409. SQLite is convenient for local use; SQLAlchemy also supports PostgreSQL. Runs are stored as JSON payloads for easy evidence export. The UI shows the newest 100 runs. This simple storage design is not optimized for large production workloads or multiple server processes. Use one uvicorn worker; do not run multiple dashboard instances against the same database.

Run states: queued → running → review_ready / tests_failed / error. Startup marks unfinished recent records interrupted; interrupted runs must be started again. There is no resume mechanism or automatic repair loop.

The GitHub workflow snapshots the default branch at a commit SHA, reads only bounded regular Python files under src/tests, and ignores other files such as .env. A separate publish command revalidates the snapshot, edits and tests, creates Git tree/commit/ref objects, then opens a draft PR. A base branch can still move after the final check; GitHub review/merge checks remain authoritative. No merge operation is implemented.

## API examples

GET `/api/config` returns the temporary dashboard session token. POST `/api/runs` requires that value in `X-Forge-Token` and JSON `{"mode":"demo","case":"average"}`. Poll GET `/api/runs/{id}`. Downloads are GET `/api/runs/{id}/patch` and `/api/runs/{id}/draft`. Local API documentation is at `/docs`, with an OpenAPI schema at `/openapi.json`.

The token protects state-changing local browser requests; it is not user authentication. No CORS access is enabled. Host validation rejects unexpected hostnames, and CSP disallows external scripts. Keep this app bound to localhost.
