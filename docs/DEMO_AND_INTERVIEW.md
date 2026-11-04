# Demo and interview guide

## Two-minute demonstration

1. Start ForgeAgent and point out the scripted demo label.
2. Select the empty-average bug and run the workflow.
3. Show the baseline test failure, then the source diff adding the empty-input guard.
4. Show the same three tests passing after the patch. Download the diff and PR description.
5. Open history and compare with the discount and order-preserving deduplication cases.
6. Explain that real mode replaces the scripted proposal with an Ollama response, and requires Docker to execute repository code. Demonstrate real mode only after actually running it locally.

## Honest portfolio description

Built a local Python issue-to-patch agent workbench using FastAPI, LangGraph and SQLAlchemy. Added bounded source snapshots, immutable tests, before/after verification, a review dashboard, and an explicit GitHub draft-PR publishing workflow. Implemented an Ollama adapter and Docker execution path, with three deterministic demonstration cases and automated tests.

Do not describe the three scripted fixes as LLM success rate. Do not claim production readiness, arbitrary repository support, live deployment, or a real model benchmark until you have measured those separately. Record your own model tag, hardware, issues, failing baselines and final test results for an AI evaluation.

## Be ready to explain

- Why baseline failure matters: a passing suite cannot show that the issue was reproduced.
- Why tests are immutable: the proposer should fix the code rather than weaken the assertions.
- Why one attempt: bounded work and transparent failure; a retry loop would need budgets and independent verification.
- Why snapshot the commit: keep the patch tied to the code actually analyzed.
- Why a draft PR: a developer reviews semantics and test coverage before merge.
- Why SQLite first: simpler local setup; PostgreSQL is an optional persistence backend.
- What remains: broader test runners, dependency isolation, resumable jobs, model evaluation and stronger execution isolation.

## GitHub upload

Create an empty repository named `forge-agent` on GitHub. In this project directory run `git init`, `git add .`, `git commit -m "Add ForgeAgent issue-to-patch workbench"`, then `git branch -M main`. Add the remote URL copied from your new repository and push. Before committing, inspect `git status --short`; `.venv-forge`, runtime files and `.env` should not appear. Do not add model weights or tokens.
