import argparse, json
from pathlib import Path
from .store import Store
from .workflow import new_run, execute, draft
from .policy import read_local
from .github import GitHub


def main():
    p = argparse.ArgumentParser(description="ForgeAgent CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument(
        "--case", choices=["average", "discount", "unique"], default="average"
    )
    local = sub.add_parser("local")
    local.add_argument("--repo", required=True)
    local.add_argument("--issue-file", required=True)
    gh = sub.add_parser("github")
    gh.add_argument("--repo", required=True)
    gh.add_argument("--issue", type=int, required=True)
    pub = sub.add_parser("publish")
    pub.add_argument("run_id")
    pub.add_argument(
        "--confirm", action="store_true", help="Create a remote branch and draft PR"
    )
    exp = sub.add_parser("export")
    exp.add_argument("run_id")
    a = p.parse_args()
    store = Store()
    try:
        if a.cmd == "publish":
            if not a.confirm:
                p.error(
                    "Review the diff first, then pass --confirm to create a GitHub branch and draft PR."
                )
            r = store.get(a.run_id)
            if not r:
                raise ValueError("Unknown run ID.")
            if r.get("pr_url"):
                print(r["pr_url"])
                return
            url = GitHub().publish(r)
            r["pr_url"] = url
            store.save(r)
            print(url)
            return
        if a.cmd == "export":
            r = store.get(a.run_id)
            if not r:
                raise ValueError("Unknown run ID.")
        else:
            if a.cmd == "demo":
                r = new_run(case=a.case)
            elif a.cmd == "local":
                r = new_run(
                    "ollama",
                    issue=Path(a.issue_file).read_text(),
                    files=read_local(a.repo),
                )
            else:
                issue, files, source = GitHub().snapshot(a.repo, a.issue)
                r = new_run("ollama", issue=issue, files=files, source=source)
            store.save(r)
            r = execute(r, store)
        out = Path("runtime/exports") / r["id"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "changes.patch").write_text(r.get("diff", ""), encoding="utf-8")
        (out / "PULL_REQUEST.md").write_text(draft(r), encoding="utf-8")
        (out / "run.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
        print(f"Run: {r['id']}\nStatus: {r['status']}\nArtifacts: {out}")
        if r.get("error"):
            print(r["error"])
        if r["status"] != "review_ready":
            raise SystemExit(1)
    except (ValueError, RuntimeError, OSError) as e:
        p.exit(1, str(e) + "\n")


if __name__ == "__main__":
    main()
