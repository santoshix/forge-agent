import difflib, hashlib, json, time, uuid
from datetime import datetime, timezone
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from .fixtures import CASES, files as demo_files
from .policy import validate_snapshot, validate_edits
from .provider import propose
from .runner import run_tests


class State(TypedDict, total=False):
    id: str
    mode: str
    case: str
    issue: str
    original: dict
    edits: dict
    baseline: dict
    verification: dict
    summary: str
    diff: str
    events: list
    status: str
    error: str
    created: str
    elapsed: float
    source: dict


def new_run(mode="demo", case="average", issue="", files=None, source=None):
    if mode not in ("demo", "ollama"):
        raise ValueError("Unknown mode.")
    if mode == "demo":
        if case not in CASES:
            raise ValueError("Unknown demo case.")
        issue = CASES[case]["issue"]
        files = demo_files(case)
    if not issue.strip() or len(issue) > 12_000:
        raise ValueError("Issue must contain 1–12000 characters.")
    validate_snapshot(files or {})
    return State(
        id=uuid.uuid4().hex,
        mode=mode,
        case=case,
        issue=issue,
        original=files,
        source=source or {},
        status="queued",
        created=datetime.now(timezone.utc).isoformat(),
        events=[],
    )


def execute(run, store):
    start = time.monotonic()

    def stage(name, fn):
        def call(s):
            s["events"] = [
                *s["events"],
                {"stage": name, "time": datetime.now(timezone.utc).isoformat()},
            ]
            s["status"] = "running"
            store.save(s)
            result = fn(s)
            s.update(result)
            store.save(s)
            return s

        return call

    def inspect(s):
        validate_snapshot(s["original"])
        return {"baseline": run_tests(s["original"], trusted=s["mode"] == "demo")}

    def plan(s):
        if s["baseline"]["tests"] == 0:
            raise ValueError(
                "No unittest tests executed. Check runner and test discovery."
            )
        if s["baseline"]["passed"]:
            raise ValueError(
                "Baseline already passes. Add a failing regression test before requesting a fix."
            )
        if s["baseline"]["exit_code"] != 1:
            raise ValueError(
                "Baseline could not run normally; resolve runner errors first."
            )
        p = propose(s["mode"], s["case"], s["issue"], s["original"])
        edits = validate_edits(s["original"], p.get("edits"))
        diff = "".join(
            "".join(
                difflib.unified_diff(
                    s["original"][path].splitlines(True),
                    content.splitlines(True),
                    fromfile="a/" + path,
                    tofile="b/" + path,
                )
            )
            for path, content in sorted(edits.items())
        )
        return {"edits": edits, "summary": p["summary"], "diff": diff}

    def verify(s):
        result = run_tests(s["original"] | s["edits"], trusted=s["mode"] == "demo")
        return {
            "verification": result,
            "status": (
                "review_ready"
                if result["passed"] and result["tests"] == s["baseline"]["tests"]
                else "tests_failed"
            ),
        }

    graph = StateGraph(State)
    for name, fn in [("inspect", inspect), ("propose", plan), ("verify", verify)]:
        graph.add_node(name, stage(name, fn))
    graph.add_edge(START, "inspect")
    graph.add_edge("inspect", "propose")
    graph.add_edge("propose", "verify")
    graph.add_edge("verify", END)
    try:
        result = graph.compile().invoke(run)
    except Exception as e:
        result = store.get(run["id"]) or run
        # HTTP error strings may include endpoints; never store tokens or response bodies.
        result.update(status="error", error=f"{type(e).__name__}: {str(e)[:500]}")
    result["elapsed"] = round(time.monotonic() - start, 2)
    store.save(result)
    return result


def draft(r):
    v = r.get("verification", {})
    b = r.get("baseline", {})
    return (
        f"# Proposed fix\n\n{r['issue']}\n\n## Change\n{r.get('summary','No proposal')}\n\n"
        f"## Validation\nBaseline: {b.get('tests',0)} tests, passed={b.get('passed',False)}.\n"
        f"After: {v.get('tests',0)} tests, passed={v.get('passed',False)}.\n"
        f"Runner: {v.get('runner','not run')}.\nMode: {r['mode']}.\n\n"
        "Review the diff and test coverage before merging. Passing the included tests is not proof of correctness.\n"
    )


def fingerprint(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
