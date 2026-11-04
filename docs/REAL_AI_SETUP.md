# Real AI mode on Windows

First finish the README demo. The following setup is optional and uses local compute. It may require several GB of disk and RAM depending on the model. Model speed and quality depend on your hardware and chosen weights. No model is bundled.

## 1. Prepare Docker and Ollama

Install Docker Desktop from https://docs.docker.com/desktop/setup/install/windows-install/ and start it with **Linux containers**. Install Ollama from https://ollama.com/download/windows. Follow its quickstart at https://docs.ollama.com/quickstart to download a code-capable model appropriate for your laptop. `ollama list` shows installed tags. Use that exact tag below, replacing `YOUR_INSTALLED_MODEL`.

In the extracted `forge-agent` folder, click File Explorer's address bar, type `cmd`, and press Enter. Run:

```bat
docker build -t forge-runner:1 -f Dockerfile.runner .
set "OLLAMA_MODEL=YOUR_INSTALLED_MODEL"
.venv-forge\Scripts\python.exe -m forge.cli local --repo examples\mini_repo --issue-file examples\issue.txt
```

Do not type `YOUR_INSTALLED_MODEL` unchanged. Set it to a model that `ollama list` shows. Ensure Ollama is running. The runner image uses Python 3.12 and the standard library only. Real code is copied into a temporary snapshot, mounted read-only, and run with a fixed unittest command; the model does not select shell commands.

If tests fail, review the exported logs and patch. The model makes one attempt; it does not silently retry or edit tests. A passing test count is review evidence, not proof of correctness.

## 2. Use real mode in the dashboard

Stop the dashboard with Ctrl+C first. In the same command prompt where you set `OLLAMA_MODEL`, run:

```bat
set "FORGE_REPO_PATH=%CD%\examples\mini_repo"
.venv-forge\Scripts\python.exe -m uvicorn forge.api:app --host 127.0.0.1 --port 8001
```

Open the dashboard, choose real mode, and enter: `Fix average([]) so it returns 0 without changing nonempty averages.` Replace the repository path with your own only after understanding the supported layout. The selected code and issue text are sent to the configured Ollama endpoint. The default endpoint is local; changing it may send code elsewhere.

## 3. Analyze a GitHub issue

Use a repository you own or have permission to work on. It must use the supported src/tests layout, with a failing unittest regression test already committed on the default branch. The included `examples/mini_repo` is a starting point for a separate tiny repository.

Create a GitHub fine-grained token limited to that repository. Reading needs repository contents and issues access; publishing needs contents and pull requests write access. Enter it locally, not in chat or tracked files:

```bat
set "GITHUB_TOKEN=YOUR_TOKEN"
.venv-forge\Scripts\python.exe -m forge.cli github --repo OWNER/REPOSITORY --issue 1
```

This reads the issue and source snapshot, asks the model for a fix, and tests it. It does **not** publish anything. Open the reported `runtime\exports\RUN_ID` folder. Review all three files.

## 4. Publish an explicitly requested draft PR

Only after reviewing the diff and passing tests:

```bat
.venv-forge\Scripts\python.exe -m forge.cli publish RUN_ID --confirm
```

Replace RUN_ID with the actual run ID. This command checks that the base snapshot still matches, re-runs Docker verification, and checks the base ref again before creating `forge/RUN_ID` and a **draft** pull request. It never auto-merges. If the base has moved, analyze a fresh run.

Publishing is not transactional: network or GitHub permission failures can leave an orphan branch after it was created. If the command fails after branch creation, inspect GitHub before retrying; you can manually open a draft PR from that branch. The tool does not force-push or delete branches. Repository-level permissions may prohibit draft PRs or branch creation.

Clear the token when done:

```bat
set GITHUB_TOKEN=
```

## Documentation references

- Ollama API: https://docs.ollama.com/api
- LangGraph StateGraph: https://reference.langchain.com/python/langgraph/graph/state/StateGraph/
- Docker execution controls: https://docs.docker.com/engine/containers/run/
- Docker network isolation: https://docs.docker.com/engine/network/drivers/none/
- GitHub Git trees: https://docs.github.com/en/rest/git/trees
- GitHub pull requests: https://docs.github.com/en/rest/pulls/pulls
