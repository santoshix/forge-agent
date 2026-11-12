# ForgeAgent — AI-Assisted Software Engineering Workbench

**A local issue-to-patch engineering assistant** built with **Python, LangGraph, FastAPI, Docker, SQLite/PostgreSQL, and optional Ollama**. Inspect failing Python tests, propose bounded code changes, verify fixes, review diffs, and optionally create an explicitly approved **GitHub draft pull request**.

> **Important distinction:** ForgeAgent's included, no-cost **demo uses scripted fixes, not an LLM**. It executes real before/after unit tests and demonstrates the LangGraph pipeline. **Real AI mode** separately uses a local Ollama model to propose changes, but live model success rates and real remote PR publishing have **not** been established by the bundled demo evidence. This is a bounded portfolio prototype, not a production-ready autonomous programmer.

![ForgeAgent dashboard](reports/dashboard_desktop.png)

## Verified demo results

| Evaluation | Recorded result |
|---|---:|
| Bundled scripted cases | **3 / 3 review-ready** |
| Before-fix test status | **Failing** in all 3 cases |
| After-fix test status | **Passing** in all 3 cases |
| Automated Python test suite (delivery-time) | **42 passed** |

The three scripted examples cover an empty average, a discount calculation, and unique values. Results come from [`reports/demo_evaluation.json`](reports/demo_evaluation.json) and [`reports/verification.md`](reports/verification.md). They **are not an LLM benchmark**: the demo chooses known fixes and genuinely runs tests before and after applying them. Verify current repository CI separately in [GitHub Actions](https://github.com/santoshix/forge-agent/actions).

## What ForgeAgent does

- **LangGraph workflow:** inspect the issue and baseline → propose source changes → verify the patched code.
- **Real test evidence:** capture baseline and post-change unittest results; reject solutions without a reproduced failure.
- **Bounded patching:** allow limited replacements of existing Python source files, while preventing test edits, arbitrary commands, dependency changes, and path traversal.
- **Human review:** show unified diffs, logs, snapshots, execution traces, exported JSON evidence, and a draft PR description.
- **Local AI option:** use a locally running Ollama model to propose changes to a supported repository, then verify them inside Docker.
- **GitHub integration:** read an issue/default-branch snapshot; an **explicit, separate** publish command can create a branch and draft PR after rechecking the base and rerunning verification.
- **Dashboard and CLI:** FastAPI with a browser interface, SQLite by default, and optional PostgreSQL via Compose.

## Architecture

```text
Issue + source snapshot
          ↓
     LangGraph
          ↓
  Inspect existing tests ──→ baseline failure required
          ↓
  Propose code changes  ──→ scripted demo OR Ollama
          ↓
  Validate edit policy  ──→ existing source files only
          ↓
  Run patched tests     ──→ demo subprocess / Docker real mode
          ↓
  Diff + logs + draft   ──→ dashboard, JSON and export
          ↓
  Explicit user action  ──→ optional GitHub branch + DRAFT PR
```

**No automatic merging or changes to the analyzed repository's default branch.** Real mode is deliberately limited to standard-library-only Python repositories with `src/` and `tests/test*.py` unittest files. It supports at most five existing source modules per proposal; tests and dependency files cannot be modified. The standard local app is intended for a single user and is **not** a multi-tenant service.

## Start the free demo on Windows

No Docker, Ollama, cloud account, API key, or paid inference provider is needed for the scripted demo.

1. Install **64-bit Python 3.12**.
2. Clone this repository, or use GitHub **Code → Download ZIP** and extract it.
3. In the project directory, double-click **`setup_windows.bat`**.
4. Double-click **`START_FORGEAGENT.bat`** after setup completes.
5. Visit **http://127.0.0.1:8001**.
6. Select **Handle an empty average** → **Run engineering workflow**. Review the failing baseline, passing verification, patch, and PR draft. Try the other two cases.

```powershell
git clone https://github.com/santoshix/forge-agent.git
cd forge-agent
```

Keep the server window open. Press Ctrl+C to stop. Setup creates `.venv-forge`, separate from other Python projects.

### Command-line demo

```powershell
.venv-forge\Scripts\python.exe -m forge.cli demo --case average
.venv-forge\Scripts\python.exe -m forge.cli demo --case discount
.venv-forge\Scripts\python.exe -m forge.cli demo --case unique
.venv-forge\Scripts\python.exe -m pytest -q
```

Runs produce `changes.patch`, `PULL_REQUEST.md`, and `run.json` under `runtime/exports/<run-id>/`. The input repository is not modified by a demo run. On Linux, create the Python 3.12 environment using the provided setup documentation and launch with `sh start.sh`.

See [demo walkthrough and interview questions](docs/DEMO_AND_INTERVIEW.md) and [troubleshooting](docs/TROUBLESHOOTING.md).

## Try real AI-assisted code proposals

The optional AI mode requires **Ollama running locally**, a supported Python repository, and **Docker** to run its tests in an isolated container. A code-capable model must be downloaded separately; no model weights are bundled.

1. Install Ollama and Docker Desktop.
2. Download a compatible local model and configure the exact installed name in `OLLAMA_MODEL`.
3. Build the restricted runner image.
4. Run a local issue against an intentionally buggy example, inspect the diff and test output, and approve any GitHub publishing separately.

**Detailed commands and permissions:** [`docs/REAL_AI_SETUP.md`](docs/REAL_AI_SETUP.md).

**Boundaries:** The agent does not modify test files, install arbitrary dependencies, run model-chosen shell commands, or execute an autonomous multi-attempt repair loop. Passing tests support review; they do not guarantee correctness. Live Ollama effectiveness on unseen repositories is **not demonstrated** by the bundled scripted evaluation.

### GitHub draft PR flow

```text
Read authorized issue + snapshot → test baseline → propose and verify fix
       → human reviews patch → explicit publish --confirm
       → revalidate repository base + tests → create branch + DRAFT PR
```

Use a GitHub token restricted to a repository you own or have permission to edit. Never commit a token to this repository or paste it into issues, screenshots, or chat. Remote PR publishing requires live credentials and has **not been verified end to end** by the bundled validation report.

## API, data, and deployment

FastAPI serves the dashboard at http://127.0.0.1:8001 and API documentation at http://127.0.0.1:8001/docs. `GET /api/config` supplies a local session token; mutating requests include it as `X-Forge-Token`. This is a local request safeguard, **not real user authentication**.

| Component | Implementation |
|---|---|
| Workflow | LangGraph |
| API and dashboard | FastAPI + HTML/CSS/JavaScript |
| Optional local LLM | Ollama |
| Execution | Demo subprocess; Docker runner for real code |
| Persistence | SQLite; PostgreSQL supported |
| GitHub publication | Explicit draft PR only |
| Verification | unittest, pytest, GitHub Actions |

For the optional demo/PostgreSQL Docker stack:

```bash
docker compose up --build
```

Visit http://127.0.0.1:8001. The dashboard container does **not** mount the host Docker socket; real-mode execution runs via the host CLI. Compose retains PostgreSQL data in a volume, and the application is intended for local use only. Configure credentials before any broader exposure; **do not deploy this unmodified as a public multi-user service**.

## Code and evidence map

```text
forge/                   LangGraph workflow, API, policy, execution and CLI
web/                     Browser dashboard
examples/mini_repo/      Small intentionally buggy Python demo project
docs/                    Architecture, real AI setup, security and demo guides
reports/                 Demo evaluation, verification report and screenshots
tests/                   Unit and mocked integration tests
scripts/                 Helper scripts
Dockerfile               App container
Dockerfile.runner        Restricted test runner
compose.yaml             Optional dashboard/PostgreSQL stack
START_FORGEAGENT.bat     Windows startup
setup_windows.bat        Windows dependency installation
```

The initial validation reported **42 passing Python tests** and successful scripted browser workflows. The [verification report](reports/verification.md) distinguishes executed runs from **mocked** Ollama/GitHub/Docker integration checks and **unverified** live integrations.

## Internship interview summary

> Built ForgeAgent, a LangGraph-based Python software engineering workbench with FastAPI, local test execution, patch review, and optional Ollama-powered code proposals. Designed a bounded inspect–propose–verify workflow with test evidence, restricted edits, diff exports, and a guarded GitHub draft-pull-request integration. Validated three scripted demo cases and 42 automated tests; live LLM performance and remote PR publishing remain separate, unverified integrations.

## Limitations, safety and licensing

- **Deterministic demo ≠ LLM-generated fix.** The shipped reproducible demo uses scripted patches.
- **Tests passing ≠ a correct or safe patch.** Review code and use trusted repositories.
- **Local-first security.** The session token does not replace multi-user authentication; keep the app bound to loopback.
- **Docker is a safeguard, not a perfect sandbox.** Keep the Docker daemon protected and avoid exposing execution services publicly.
- **Not autonomous production software.** No auto-merge, general-purpose repository support, or demonstrated real-issue success rate.

Project source is licensed under [MIT](LICENSE). Dependencies and downloaded model weights have their own terms.
