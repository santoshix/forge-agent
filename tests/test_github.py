import base64
import httpx
import pytest
from forge.github import GitHub
from forge.fixtures import files, CASES


def test_snapshot_http_contract():
    original = files("average")
    blobs = {str(i): text for i, text in enumerate(original.values())}

    def handle(req):
        path = req.url.path
        if path == "/repos/person/project":
            data = {"default_branch": "main"}
        elif "/git/ref/" in path:
            data = {"object": {"sha": "base"}}
        elif "/issues/" in path:
            data = {"title": "Bug", "body": "Fix empty list"}
        elif "/git/trees/" in path:
            data = {
                "truncated": False,
                "tree": [
                    {
                        "type": "blob",
                        "mode": "100644",
                        "path": p,
                        "sha": str(i),
                        "size": len(s),
                    }
                    for i, (p, s) in enumerate(original.items())
                ]
                + [{"type": "blob", "path": ".env", "mode": "100644", "sha": "secret"}],
            }
        else:
            data = {
                "encoding": "base64",
                "content": base64.b64encode(
                    blobs[path.rsplit("/", 1)[1]].encode()
                ).decode(),
            }
        return httpx.Response(200, json=data)

    g = GitHub(
        httpx.Client(
            base_url="https://api.github.com", transport=httpx.MockTransport(handle)
        )
    )
    issue, snapshot, source = g.snapshot("person/project", 1)
    assert snapshot == original and source["sha"] == "base" and issue.startswith("Bug")


def ready():
    return {
        "id": "a" * 32,
        "mode": "ollama",
        "status": "review_ready",
        "source": {
            "repo": "person/project",
            "issue_number": 1,
            "base": "main",
            "sha": "base",
        },
        "original": files("average"),
        "edits": {"src/logic.py": CASES["average"]["after"]},
        "baseline": {"tests": 3, "passed": False},
        "verification": {"tests": 3, "passed": True},
        "issue": "Fix empty mean",
        "summary": "Guard empty input",
    }


@pytest.mark.parametrize(
    "mode,status",
    [("demo", "review_ready"), ("ollama", "tests_failed"), ("ollama", "error")],
)
def test_publish_gate(mode, status):
    r = ready()
    r.update(mode=mode, status=status)
    with pytest.raises(ValueError):
        GitHub(httpx.Client(trust_env=False)).publish(r)


def test_publish_is_draft_and_separate_branch(monkeypatch):
    import forge.github as module

    r = ready()
    calls = []
    g = GitHub(httpx.Client(trust_env=False))
    monkeypatch.setattr(
        g, "snapshot", lambda *args: ("issue", r["original"], r["source"])
    )

    def runner(*args, **kw):
        assert kw["trusted"] is False
        return {"passed": True, "tests": 3}

    monkeypatch.setattr(module, "run_tests", runner)

    def call(method, path, **kw):
        calls.append((method, path, kw.get("json")))
        if "/git/ref/heads/" in path:
            return {"object": {"sha": "base"}}
        if method == "GET":
            return {"tree": {"sha": "tree0"}}
        if path.endswith("/pulls"):
            return {"html_url": "https://github.com/person/project/pull/1"}
        return {"sha": "object"}

    monkeypatch.setattr(g, "call", call)
    assert g.publish(r).endswith("/pull/1")
    assert calls[-1][2]["draft"] is True
    assert calls[-1][2]["head"] == "forge/" + r["id"]
    assert calls[-2][2]["ref"].startswith("refs/heads/forge/")
    assert all(method != "PATCH" for method, _, _ in calls)


def test_base_drift_prevents_write(monkeypatch):
    r = ready()
    g = GitHub(httpx.Client(trust_env=False))
    source = r["source"] | {"sha": "new"}
    monkeypatch.setattr(g, "snapshot", lambda *a: ("", r["original"], source))
    monkeypatch.setattr(g, "call", lambda *a, **kw: pytest.fail("Must not write"))
    with pytest.raises(ValueError, match="Base changed"):
        g.publish(r)


def test_drift_during_verification_prevents_write(monkeypatch):
    import forge.github as module

    r = ready()
    g = GitHub(httpx.Client(trust_env=False))
    monkeypatch.setattr(g, "snapshot", lambda *a: ("", r["original"], r["source"]))
    monkeypatch.setattr(
        module, "run_tests", lambda *a, **kw: {"passed": True, "tests": 3}
    )

    def call(method, path, **kw):
        assert method == "GET"
        return {"object": {"sha": "moved"}}

    monkeypatch.setattr(g, "call", call)
    with pytest.raises(ValueError, match="during verification"):
        g.publish(r)


def test_failed_reverification_prevents_publish(monkeypatch):
    import forge.github as module

    r = ready()
    g = GitHub(httpx.Client(trust_env=False))
    monkeypatch.setattr(g, "snapshot", lambda *a: ("", r["original"], r["source"]))
    monkeypatch.setattr(
        module, "run_tests", lambda *a, **kw: {"passed": False, "tests": 3}
    )
    monkeypatch.setattr(g, "call", lambda *a, **kw: pytest.fail("Must not write"))
    with pytest.raises(ValueError, match="verification failed"):
        g.publish(r)
