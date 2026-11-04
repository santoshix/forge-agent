import json
import time
from pathlib import Path
import httpx
import pytest
from forge.fixtures import CASES, files
from forge.policy import allowed, validate_snapshot, validate_edits, read_local
from forge.runner import run_tests
from forge.store import Store
from forge.workflow import new_run, execute, draft


@pytest.fixture
def store(tmp_path):
    return Store("sqlite:///" + str(tmp_path / "runs.db"))


@pytest.mark.parametrize("case", list(CASES))
def test_complete_demo(case, store):
    r = new_run(case=case)
    original = dict(r["original"])
    store.save(r)
    result = execute(r, store)
    assert result["status"] == "review_ready"
    assert result["baseline"]["exit_code"] == 1 and not result["baseline"]["passed"]
    assert result["verification"]["passed"] and result["verification"]["tests"] == 3
    assert result["original"] == original
    assert [e["stage"] for e in result["events"]] == ["inspect", "propose", "verify"]
    assert "--- a/src/logic.py" in result["diff"]
    assert store.get(r["id"])["status"] == "review_ready"
    assert "Mode: demo" in draft(result)


@pytest.mark.parametrize(
    "path",
    [
        "../secret.py",
        "src/../../x.py",
        "/src/a.py",
        "C:/src/a.py",
        "src\\a.py",
        ".git/config.py",
        "src/.secret.py",
        "requirements.txt",
        "tests/a.txt",
    ],
)
def test_paths_denied(path):
    assert not allowed(path)


@pytest.mark.parametrize(
    "edit",
    [
        {"tests/test_logic.py": "pass\n"},
        {"src/new.py": "pass\n"},
        {"src/__init__.py": "pass\n"},
        {"../evil.py": "pass\n"},
        {},
        {"src/logic.py": 9},
    ],
)
def test_edit_scope(edit):
    with pytest.raises(ValueError):
        validate_edits(files("average"), edit)


def test_syntax_and_noop():
    original = files("average")
    with pytest.raises(SyntaxError):
        validate_edits(original, {"src/logic.py": "def (\n"})
    with pytest.raises(ValueError):
        validate_edits(original, {"src/logic.py": original["src/logic.py"]})


def test_snapshot_limits():
    with pytest.raises(ValueError):
        validate_snapshot({"src/a.py": "pass"})
    with pytest.raises(ValueError):
        validate_snapshot({"tests/test_x.py": "x" * 200001})
    with pytest.raises(ValueError):
        validate_snapshot({f"tests/test_{i}.py": "" for i in range(101)})


def test_runner_enforces_paths():
    with pytest.raises(ValueError):
        run_tests({"../escape.py": "pass", "tests/test_a.py": ""}, trusted=True)


def test_timeout():
    f = {"src/a.py": "", "tests/test_hang.py": "import time\ntime.sleep(10)\n"}
    r = run_tests(f, trusted=True, timeout=0.15)
    assert r["exit_code"] == 124 and not r["passed"]


def test_output_limit():
    f = {"src/a.py": "", "tests/test_noisy.py": 'print("x" * 100000)\n'}
    r = run_tests(f, trusted=True)
    assert r["exit_code"] == 125 and len(r["output"]) < 64100


def test_no_tests_never_pass():
    r = run_tests({"src/a.py": "", "tests/test_empty.py": ""}, trusted=True)
    assert not r["passed"] and r["tests"] == 0


def test_local_snapshot_does_not_read_secrets(tmp_path):
    for p, s in files("average").items():
        f = tmp_path / p
        f.parent.mkdir(exist_ok=True)
        f.write_text(s)
    (tmp_path / ".env").write_text("TOKEN=not-for-the-model")
    assert read_local(tmp_path) == files("average")


def test_symlink_rejected(tmp_path):
    (tmp_path / "real").mkdir()
    try:
        (tmp_path / "src").symlink_to(tmp_path / "real", target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks not available to this Windows account")
    with pytest.raises(ValueError):
        read_local(tmp_path)


def test_recover(store):
    r = new_run()
    store.save(r)
    store.recover()
    assert store.get(r["id"])["status"] == "interrupted"
    assert len(store.list()) == 1


def test_failed_proposal_preserves_baseline(store, monkeypatch):
    import forge.workflow as wf

    monkeypatch.setattr(
        wf,
        "propose",
        lambda *a: {"summary": "bad", "edits": {"tests/test_logic.py": "pass"}},
    )
    r = new_run()
    store.save(r)
    out = execute(r, store)
    assert out["status"] == "error" and out["baseline"]["tests"] == 3
    assert "immutable" in out["error"]


def test_incorrect_patch_fails(store, monkeypatch):
    import forge.workflow as wf

    monkeypatch.setattr(
        wf,
        "propose",
        lambda *a: {
            "summary": "bad",
            "edits": {"src/logic.py": "def average(values):\n    return 999\n"},
        },
    )
    r = new_run()
    store.save(r)
    out = execute(r, store)
    assert out["status"] == "tests_failed" and not out["verification"]["passed"]


def test_real_mode_uses_untrusted_runner(store, monkeypatch):
    import forge.workflow as wf

    seen = []

    def runner(f, **kw):
        seen.append(kw["trusted"])
        return {
            "passed": len(seen) > 1,
            "exit_code": 1 if len(seen) == 1 else 0,
            "tests": 3,
            "output": "mock",
            "runner": "mock Docker",
        }

    monkeypatch.setattr(wf, "run_tests", runner)
    monkeypatch.setattr(
        wf,
        "propose",
        lambda *a: {
            "summary": "model stub",
            "edits": {"src/logic.py": CASES["average"]["after"]},
        },
    )
    r = new_run("ollama", issue="Fix empty mean", files=files("average"))
    store.save(r)
    assert execute(r, store)["status"] == "review_ready" and seen == [False, False]


def test_ollama_request_contract(monkeypatch):
    from forge.provider import propose
    import forge.provider as provider

    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    real_client = httpx.Client

    def handle(request):
        body = json.loads(request.content)
        assert (
            body["model"] == "test-model"
            and body["stream"] is False
            and body["format"] == "json"
        )
        return httpx.Response(
            200,
            json={
                "response": json.dumps(
                    {
                        "summary": "fix",
                        "edits": {"src/logic.py": CASES["average"]["after"]},
                    }
                )
            },
        )

    monkeypatch.setattr(
        provider.httpx,
        "Client",
        lambda **kw: real_client(transport=httpx.MockTransport(handle)),
    )
    assert (
        propose("ollama", "average", "fix empty", files("average"))["summary"] == "fix"
    )


def test_ollama_missing_model(monkeypatch):
    from forge.provider import propose

    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    with pytest.raises(ValueError):
        propose("ollama", "average", "fix", files("average"))


def test_api_demo_and_guards(tmp_path, monkeypatch):
    import forge.api as api
    from fastapi.testclient import TestClient

    monkeypatch.setattr(api, "store", Store("sqlite:///" + str(tmp_path / "api.db")))
    with TestClient(api.app) as c:
        assert c.get("/").status_code == 200
        assert c.get("/docs").status_code == 200
        assert c.get("/openapi.json").status_code == 200
        assert c.get("/api/health").json()["status"] == "ok"
        assert c.get("/", headers={"Host": "evil.example"}).status_code == 400
        assert c.post("/api/runs", json={"mode": "demo"}).status_code == 403
        config = c.get("/api/config").json()
        h = {"X-Forge-Token": config["token"]}
        assert (
            c.post("/api/runs", json={"mode": "invalid"}, headers=h).status_code == 422
        )
        response = c.post(
            "/api/runs", json={"mode": "demo", "case": "discount"}, headers=h
        )
        assert response.status_code == 202
        rid = response.json()["id"]
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            run = c.get("/api/runs/" + rid).json()
            if run["status"] not in ["queued", "running"]:
                break
            time.sleep(0.05)
        assert run["status"] == "review_ready"
        assert "src/logic.py" in c.get("/api/runs/" + rid + "/patch").text
        assert "Mode: demo" in c.get("/api/runs/" + rid + "/draft").text
        assert len(c.get("/api/runs").json()) == 1
        assert c.get("/api/runs/missing").status_code == 404
        api.slot.acquire()
        try:
            assert c.post("/api/runs", json={}, headers=h).status_code == 409
        finally:
            api.slot.release()


def test_docker_command_has_isolation_controls(monkeypatch):
    import io
    import forge.runner as runner

    seen = []

    class Process:
        stdout = io.BytesIO(b"Ran 3 tests in 0.1s\nOK\n")

        def wait(self, timeout=None):
            return 0

        def kill(self):
            pass

    def start(cmd, **kw):
        seen.extend(cmd)
        assert "GITHUB_TOKEN" not in kw["env"]
        return Process()

    monkeypatch.setenv("GITHUB_TOKEN", "test-secret-never-pass")
    monkeypatch.setattr(runner.subprocess, "Popen", start)
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **kw: None)
    assert runner.run_tests(files("average"), trusted=False)["passed"]
    for flag in [
        "--read-only",
        "--cap-drop",
        "--security-opt",
        "--pids-limit",
        "--memory",
        "--cpus",
        "--user",
    ]:
        assert flag in seen
    assert seen[seen.index("--network") + 1] == "none"
    assert "readonly" in seen[seen.index("--mount") + 1]
    assert "/var/run/docker.sock" not in " ".join(seen)
