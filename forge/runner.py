"""Trusted fixtures may run locally. All model-generated code requires Docker."""

import os, re, subprocess, sys, tempfile, uuid, threading
from .policy import validate_snapshot
from pathlib import Path


def run_tests(files, *, trusted=False, timeout=45):
    validate_snapshot(files)
    with tempfile.TemporaryDirectory(prefix="forge-test-") as tmp:
        root = Path(tmp)
        for p, s in files.items():
            f = root / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(s, encoding="utf-8")
        name = "forge-" + uuid.uuid4().hex
        if trusted:
            cmd = [
                sys.executable,
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ]
        else:
            # No credentials, Docker socket, host home, or network are exposed to tests.
            cmd = [
                "docker",
                "run",
                "--rm",
                "--name",
                name,
                "--network",
                "none",
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                "64",
                "--memory",
                "256m",
                "--cpus",
                "1",
                "--user",
                "65534:65534",
                "--tmpfs",
                "/tmp:rw,noexec,nosuid,size=32m",
                "--mount",
                f"type=bind,source={root},target=/workspace,readonly",
                "-w",
                "/workspace",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                os.environ.get("FORGE_RUNNER_IMAGE", "forge-runner:1"),
                "python",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            ]
            # tempfile uses mode 700 on Unix; grant the container read/traverse access.
            root.chmod(0o755)
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            in (
                "PATH",
                "SYSTEMROOT",
                "WINDIR",
                "TEMP",
                "TMP",
                "HOME",
                "DOCKER_HOST",
                "DOCKER_CONTEXT",
                "DOCKER_CONFIG",
            )
        }
        try:
            # Drain continuously, stop at 64 KB, and cap execution time.
            proc = subprocess.Popen(
                cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
            )
            captured = bytearray()
            overflow = threading.Event()

            def consume():
                while True:
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    room = 64_000 - len(captured)
                    captured.extend(chunk[:room])
                    if len(chunk) > room:
                        overflow.set()
                        proc.kill()
                        break

            reader = threading.Thread(target=consume, daemon=True)
            reader.start()
            try:
                code = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                code = 124
            reader.join(timeout=2)
            if overflow.is_set():
                code = 125
            output = captured.decode("utf-8", errors="replace")
            if code == 124:
                output += "\nExecution timed out."
            if code == 125:
                output += "\nOutput exceeded 64 KB."
            match = re.search(r"Ran (\d+) tests?", output)
            count = int(match.group(1)) if match else 0
            return {
                "passed": code == 0 and count > 0,
                "exit_code": code,
                "tests": count,
                "output": output,
                "runner": (
                    "trusted-fixture subprocess"
                    if trusted
                    else "Docker (network disabled)"
                ),
            }
        except FileNotFoundError:
            raise RuntimeError(
                "Docker is required for real code. Install/start Docker Desktop and build forge-runner:1."
            ) from None
        finally:
            if not trusted:
                try:
                    subprocess.run(
                        ["docker", "rm", "-f", name],
                        capture_output=True,
                        timeout=10,
                        env=env,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
