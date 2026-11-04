# Execution boundaries and limitations

Bundled demo files and proposals are trusted, checked-in fixtures and run in a Python subprocess with timeout and bounded output. User/model code must use the Docker runner. Containers have no network, read-only root and source mounts, a non-root user, no capabilities, no privilege escalation, CPU/memory/PID limits and a small temporary filesystem. The Docker socket, host home and tokens are not mounted into the test container. Timeout cleanup forcibly removes the named container.

These controls reduce exposure; Docker is not a hardened hostile-code service. Run this local portfolio app only against code you are authorized to inspect and reasonably trust. There is no multi-tenant isolation, supply-chain verification, kernel hardening, production authentication, distributed queue or resource quota across multiple CLI processes.

Only src/tests Python files enter the model context. That does not make them non-sensitive: secrets embedded in source can still be sent to Ollama. The issue and file contents are untrusted model data. Path and edit restrictions are enforced outside the model, and tests cannot be changed through a proposal. A source module can still alter runtime behavior, game tests or fake output. Test logs/counts are not tamper-proof attestations. Human review and adequate regression coverage are required.

Real mode supports only standard-library dependencies and one patch attempt. It does not install repository dependencies, execute setup.py, fetch arbitrary URLs, run model-chosen commands, change test files, or automatically merge. Invalid JSON, oversized output, syntax errors, missing tests, no baseline failure and failing verification produce an error or tests_failed state. Results are retained locally under runtime and should not be committed.

The GitHub integration is a draft PR helper. No remote PR was created while validating this package. The token is read from the process environment and is not stored in run records or passed to the runner. Review repository permissions and remote branches after a failed publish before retrying.
