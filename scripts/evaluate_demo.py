"""Measure bundled scripted fixtures, not LLM accuracy. Run from project root."""

import json
import platform
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from forge.fixtures import CASES
from forge.store import Store
from forge.workflow import new_run, execute


def main():
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        store = Store("sqlite:///" + str(Path(tmp) / "evaluation.db"))
        for case in CASES:
            r = new_run(case=case)
            store.save(r)
            r = execute(r, store)
            results.append(
                {
                    "case": case,
                    "status": r["status"],
                    "baseline_tests": r.get("baseline", {}).get("tests", 0),
                    "baseline_passed": r.get("baseline", {}).get("passed", False),
                    "after_tests": r.get("verification", {}).get("tests", 0),
                    "after_passed": r.get("verification", {}).get("passed", False),
                    "elapsed_seconds": r["elapsed"],
                }
            )
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "scope": "Scripted proposals with actual unittest execution; NOT an LLM benchmark.",
        "cases": results,
        "passed_cases": sum(r["status"] == "review_ready" for r in results),
        "total_cases": len(results),
    }
    out = Path("reports/demo_evaluation.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["passed_cases"] != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
