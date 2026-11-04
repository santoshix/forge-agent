"""GitHub REST integration: bounded source snapshots, explicit draft PR publication."""

import base64, os, re
import httpx
from .policy import allowed, validate_snapshot, validate_edits, MAX_BYTES
from .runner import run_tests
from .workflow import draft


class GitHub:
    def __init__(self, client=None):
        token = os.environ.get("GITHUB_TOKEN", "")
        self.client = client or httpx.Client(
            base_url="https://api.github.com",
            timeout=30,
            follow_redirects=False,
            headers={
                "Accept": "application/vnd.github+json",
                **({"Authorization": "Bearer " + token} if token else {}),
            },
        )

    def call(self, method, path, **kw):
        r = self.client.request(method, path, **kw)
        if r.status_code >= 400:
            raise RuntimeError(
                f"GitHub returned HTTP {r.status_code}; check repository access, token permissions and rate limits."
            )
        return r.json()

    def snapshot(self, repo, issue_number):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Use owner/repository.")
        if issue_number < 1:
            raise ValueError("Issue number must be positive.")
        prefix = "/repos/" + repo
        info = self.call("GET", prefix)
        branch = info["default_branch"]
        from urllib.parse import quote

        ref = self.call("GET", prefix + "/git/ref/heads/" + quote(branch, safe=""))
        sha = ref["object"]["sha"]
        issue = self.call("GET", prefix + f"/issues/{issue_number}")
        if "pull_request" in issue:
            raise ValueError("Choose an issue, not a pull request.")
        tree = self.call("GET", prefix + "/git/trees/" + sha, params={"recursive": "1"})
        if tree.get("truncated"):
            raise ValueError("Repository tree is too large.")
        selected = [
            x for x in tree["tree"] if x["type"] == "blob" and allowed(x["path"])
        ]
        if len(selected) > 100:
            raise ValueError("Too many Python files (maximum 100).")
        if sum(x.get("size", 0) for x in selected) > MAX_BYTES:
            raise ValueError("Selected code exceeds 200 KB.")
        files = {}
        for entry in selected:
            if entry.get("mode") != "100644":
                raise ValueError(
                    "Only regular, non-executable Python source files are supported."
                )
            blob = self.call("GET", prefix + "/git/blobs/" + entry["sha"])
            if blob.get("encoding") != "base64":
                raise ValueError("Unsupported blob encoding.")
            files[entry["path"]] = base64.b64decode(
                blob["content"], validate=False
            ).decode("utf-8")
        validate_snapshot(files)
        text = (issue["title"] + "\n\n" + (issue.get("body") or ""))[:12000]
        return (
            text,
            files,
            {"repo": repo, "issue_number": issue_number, "base": branch, "sha": sha},
        )

    def publish(self, run):
        if run["mode"] != "ollama" or run["status"] != "review_ready":
            raise ValueError("Only a passing real-model run may be published.")
        src = run.get("source", {})
        if not {"repo", "sha", "issue_number", "base"} <= src.keys():
            raise ValueError("This run has no GitHub source snapshot.")
        _, original, current = self.snapshot(src["repo"], src["issue_number"])
        if current != src or original != run["original"]:
            raise ValueError("Base changed since analysis. Create a fresh run.")
        edits = validate_edits(original, run["edits"])
        verified = run_tests(original | edits, trusted=False)
        if not verified["passed"] or verified["tests"] != run["baseline"]["tests"]:
            raise ValueError("Publication verification failed.")
        # Build a new branch via Git objects; never push or overwrite the default branch.
        prefix = "/repos/" + src["repo"]
        branch = "forge/" + run["id"]
        from urllib.parse import quote

        latest = self.call(
            "GET", prefix + "/git/ref/heads/" + quote(src["base"], safe="")
        )
        if latest["object"]["sha"] != src["sha"]:
            raise ValueError("Base changed during verification. Create a fresh run.")
        parent = self.call("GET", prefix + "/git/commits/" + src["sha"])
        tree = self.call(
            "POST",
            prefix + "/git/trees",
            json={
                "base_tree": parent["tree"]["sha"],
                "tree": [
                    {"path": p, "mode": "100644", "type": "blob", "content": v}
                    for p, v in edits.items()
                ],
            },
        )
        commit = self.call(
            "POST",
            prefix + "/git/commits",
            json={
                "message": "Propose fix for issue #" + str(src["issue_number"]),
                "tree": tree["sha"],
                "parents": [src["sha"]],
            },
        )
        self.call(
            "POST",
            prefix + "/git/refs",
            json={"ref": "refs/heads/" + branch, "sha": commit["sha"]},
        )
        result = self.call(
            "POST",
            prefix + "/pulls",
            json={
                "title": f"Proposed fix for #{src['issue_number']}",
                "body": draft(run) + f"\nRelated issue: #{src['issue_number']}\n",
                "head": branch,
                "base": src["base"],
                "draft": True,
            },
        )
        return result["html_url"]
