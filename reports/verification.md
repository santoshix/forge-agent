# Original delivery verification report (historical snapshot)

Validation date: 2026-11-02. Environment: Linux, Python 3.12.14.

## Executed successfully

- Automated Python suite: **42 passed**. Actual result: tests.txt.
- Three complete LangGraph demo workflows: each reproduced a failure, applied a scripted source fix, then passed the same three unittest tests. See demo_evaluation.json. These are demonstration results, not LLM accuracy.
- Policy checks: path traversal, immutable tests/initializers, nonexistent source files, size limits, syntax errors, no-op patches and symlinks.
- Actual subprocess timeout, output cap and zero-test handling.
- API request validation, host checks, session-token checks, overlapping-run rejection, full demo execution and artifact downloads.
- CLI demo and export of patch, draft description and JSON evidence.
- Chromium browser: completed demo, diff/log/draft tabs, history selection, patch download and no JavaScript page errors. Desktop 1440-pixel and mobile 390-pixel layouts inspected; no horizontal page overflow.
- Dependency consistency: pip check passed.

## Mocked integration checks

- Ollama JSON request/response contract; no actual LLM was called.
- GitHub snapshot retrieval, draft flag/separate branch, failed-run gates, base drift before/after verification and failed reverification. No remote writes were made.
- Docker command isolation controls and omission of GitHub credentials from the runner environment.

## Not live-verified here

- Windows batch execution and package installation. Launchers target Python 3.12. At original delivery time, Windows/Ubuntu GitHub CI had not run remotely yet; see the live Actions link below for its current results.
- Docker execution, Compose build, PostgreSQL and live Ollama inference. These services were unavailable in the build environment.
- GitHub token permissions and actual remote draft PR creation.

The demo is validated end to end. Optional integrations are implemented and documented with the boundaries above. This is a bounded portfolio prototype, not a production-readiness claim.

## Later repository publication

The repository is now publicly hosted at https://github.com/santoshix/forge-agent. See https://github.com/santoshix/forge-agent/actions for subsequent GitHub Actions runs. A passing GitHub CI run does not itself verify the live Ollama workflow, Docker runner, remote draft PR publication, or production readiness. The original executed-versus-mocked distinctions above still apply.
