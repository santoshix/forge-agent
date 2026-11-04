"""Real Docker-sandbox smoke test, run by the dedicated CI Docker job."""
from forge.fixtures import CASES, files
from forge.runner import run_tests

def test_real_docker_runner_executes_untrusted_snapshot():
    before = files("average")
    baseline = run_tests(before, trusted=False, timeout=35)
    assert baseline["runner"] == "Docker (network disabled)"
    assert baseline["tests"] == 3
    assert not baseline["passed"] and baseline["exit_code"] == 1

    after = before | {"src/logic.py": CASES["average"]["after"]}
    result = run_tests(after, trusted=False, timeout=35)
    assert result["passed"], result["output"]
    assert result["tests"] == baseline["tests"]
