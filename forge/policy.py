import ast
from pathlib import PurePosixPath, Path

MAX_FILES = 100
MAX_BYTES = 200_000


def allowed(path):
    p = PurePosixPath(path)
    return (
        not p.is_absolute()
        and ".." not in p.parts
        and "\\" not in path
        and ":" not in path
        and len(p.parts) > 1
        and p.parts[0] in ("src", "tests")
        and all(not x.startswith(".") for x in p.parts)
        and p.suffix == ".py"
    )


def validate_snapshot(files):
    if not files or len(files) > MAX_FILES:
        raise ValueError("Repository requires 1–100 selected Python files.")
    if any(not allowed(p) or not isinstance(v, str) for p, v in files.items()):
        raise ValueError("Only src/ and tests/ Python files are supported.")
    if sum(len(s.encode()) for s in files.values()) > MAX_BYTES:
        raise ValueError("Selected repository exceeds 200 KB.")
    if not any(p.startswith("tests/test") for p in files):
        raise ValueError("Add unittest tests in tests/test*.py first.")
    return files


def read_local(root):
    root = Path(root).resolve()
    result = {}
    for name in ("src", "tests"):
        base = root / name
        if base.is_symlink():
            raise ValueError("Symlink directories are not allowed.")
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.is_symlink():
                raise ValueError("Symlinks are not allowed.")
            if p.is_file() and p.suffix == ".py":
                rel = p.relative_to(root).as_posix()
                if not allowed(rel):
                    continue
                if p.stat().st_size > MAX_BYTES:
                    raise ValueError("File exceeds size limit.")
                result[rel] = p.read_text(encoding="utf-8")
                if len(result) > MAX_FILES:
                    raise ValueError("Too many files.")
    return validate_snapshot(result)


def validate_edits(original, edits):
    if not isinstance(edits, dict) or not 1 <= len(edits) <= 5:
        raise ValueError("Propose 1–5 file replacements.")
    for p, text in edits.items():
        if (
            p not in original
            or not allowed(p)
            or not p.startswith("src/")
            or p.endswith("__init__.py")
        ):
            raise ValueError(
                "Only existing src Python modules may be edited; tests and package initializers are immutable."
            )
        if not isinstance(text, str) or len(text.encode()) > 50_000:
            raise ValueError("Invalid or oversized file replacement.")
        ast.parse(text, filename=p)
    if all(original[p] == v for p, v in edits.items()):
        raise ValueError("Proposal contains no change.")
    validate_snapshot(original | edits)
    return edits
