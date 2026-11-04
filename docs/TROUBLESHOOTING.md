# Troubleshooting

**Python not found:** open Command Prompt and run `py -3.12 --version`. If unavailable and you have Python install manager, run `pymanager install 3.12`, open a new prompt, then retry setup. Python 3.14 alone does not satisfy the launcher.

**ZIP folder:** extract all files first. Run setup from the extracted folder, not inside the ZIP preview.

**Setup failed:** keep the error visible. Check internet access, available disk space and the first pip error. Do not run START until setup succeeds. The project does not require PyTorch.

**Page will not open:** keep the start terminal open and wait for `Application startup complete`. Use http://127.0.0.1:8001, not InspectAI's port 8000. If port 8001 is in use, close the earlier ForgeAgent terminal or start uvicorn manually on 8002 and use that URL.

**Session token error:** refresh the page after restarting the server. Old browser tabs hold old tokens.

**Docker missing/unavailable:** real mode requires Docker Desktop running with Linux containers, plus `docker build -t forge-runner:1 -f Dockerfile.runner .`. Demo mode works without Docker. A remote Docker daemon cannot mount the local temporary snapshot; use a local Docker context.

**Model not configured:** use `ollama list`, set `OLLAMA_MODEL` to an installed tag in the same terminal, then launch the app from that terminal. The `.env` file is not read by Python. A new Command Prompt does not inherit variables set in a separate prompt.

**Ollama timeout/invalid JSON:** confirm Ollama is running; choose a model suited to your hardware and structured code edits. Inspect the error. There is no automatic retry; start a new run after resolving the cause.

**Baseline already passes:** add a failing unittest regression test to your source repository before running real mode. The agent does not invent tests or modify them.

**No tests executed:** use tests/test*.py and standard-library unittest. Source should be importable as src.module. Pytest-only tests and third-party application dependencies are outside this runner's scope.

**Interrupted record:** start a new run. Closing the server during processing does not resume work on restart.

**GitHub HTTP error:** check owner/repository, issue number, token permissions and rate limits. A successful local run does not publish; publication is the separate `publish RUN_ID --confirm` command.

**Git author identity unknown:** configure your real Git name and email locally before committing. Never paste a token into a commit or chat.
