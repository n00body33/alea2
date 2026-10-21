#!/usr/bin/env python3
"""Offline heuristic boundary check of Git blobs, never working-tree contents."""

import argparse
import re
import subprocess
import sys
from pathlib import PurePosixPath

MAX_BYTES = 1024 * 1024
PUBLIC_ROOT_FILES = {
    "README.md", "LICENSE", "CONTRIBUTING.md", ".gitignore", ".gitattributes",
}
PUBLIC_ROOTS = {"src", "tests", "scripts", "configs", "docs", ".github", ".githooks"}
TEXT_SUFFIXES = {
    ".py", ".md", ".rst", ".txt", ".json", ".jsonl", ".csv", ".tsv",
    ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".js", ".ts",
    ".jsx", ".tsx", ".html", ".css", ".xml", ".lock",
}
RESERVED_DIRS = {
    "private", "local", "data", "datasets", "corpus", "archives", "recordings",
    "transcripts", "checkpoints", "weights", "adapters", "models", "credentials",
    "secrets", "artifacts", "outputs", "runs", "traces", "cache", ".cache",
    ".aws", ".ssh", ".gnupg", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".ipynb_checkpoints", "htmlcov", "build",
    "dist", "node_modules",
}
CREDENTIAL_NAMES = {"credentials.json", "secrets.json", ".netrc", ".pypirc"}
# Signatures are tripwires, not comprehensive secret or privacy detection.
SECRET_PATTERNS = (
    ("private-key header", re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("AWS access-key signature", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GitHub token signature", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("API token signature", re.compile(rb"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b")),
    ("Slack token signature", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("Google API-key signature", re.compile(rb"\bAIza[A-Za-z0-9_-]{35}\b")),
    ("credential-bearing URL", re.compile(rb"(?:https?|postgres(?:ql)?|mysql|redis)://[^/\s:@]+:[^/\s@]+@")),
    ("literal credential assignment", re.compile(
        rb"(?im)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)"
        rb"\b[\"']?\s*[:=]\s*[\"']([^\"'\s]{16,})[\"']"
    )),
)


class InspectionError(Exception):
    """Git inspection failed; fail closed without echoing subprocess output."""


def git(*args: str, cwd=None) -> bytes:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)
    if result.returncode:
        raise InspectionError("Git could not inspect the requested snapshot.")
    return result.stdout


def path_problem(path: str) -> str | None:
    try:
        path.encode("utf-8")
    except UnicodeEncodeError:
        return "filename is not UTF-8"
    if any(ord(char) < 32 or ord(char) == 127 for char in path) or "\\" in path:
        return "control character or backslash in filename"
    parts = PurePosixPath(path).parts
    lowered = [part.lower() for part in parts]
    if any(part in RESERVED_DIRS or part.endswith(".egg-info") for part in lowered[:-1]):
        return "reserved local/private directory"
    name = lowered[-1]
    if (name in CREDENTIAL_NAMES or name == ".env" or name.startswith(".env.")
            or name.endswith(".env") or name.startswith(("id_rsa", "id_ed25519"))):
        return "credential/environment filename"
    if path in PUBLIC_ROOT_FILES or path in {".githooks/pre-commit", "results/README.md"}:
        return None
    if not (parts[0] in PUBLIC_ROOTS or (len(parts) >= 3 and parts[:2] == ("results", "public"))):
        return "outside approved public paths"
    if PurePosixPath(path).suffix.lower() not in TEXT_SUFFIXES:
        return "file type is not an approved public text format"
    return None


def content_problem(data: bytes) -> str | None:
    if b"\x00" in data:
        return "binary content"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "non-UTF-8 content"
    if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
        return "binary/control-character content"
    if text.lstrip("\ufeff \t\r\n").startswith("version https://git-lfs.github.com/spec/v1"):
        return "Git LFS pointer (no artifact exemption)"
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(data):
            return label
    return None


def snapshot_entries(root: str, revision: str | None):
    if revision is None:
        listing = git("ls-files", "--stage", "--full-name", "-z", cwd=root)
    else:
        commit = git("rev-parse", "--verify", "--end-of-options", revision + "^{commit}", cwd=root).strip().decode("ascii")
        listing = git("ls-tree", "-r", "-z", "--full-tree", commit, cwd=root)
    for record in listing.split(b"\x00"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        first, second, third = metadata.decode("ascii").split()
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if revision is None:
            yield path, first, second, third != "0"
        else:
            yield path, first, third, False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="check the whole index (default)")
    mode.add_argument("--tree", metavar="REV", help="check all files at a commit revision")
    args = parser.parse_args()
    failures = []
    count = 0
    try:
        root = git("rev-parse", "--show-toplevel").decode().rstrip("\n")
        for path, file_mode, oid, unmerged in snapshot_entries(root, args.tree):
            count += 1
            problem = path_problem(path)
            if unmerged:
                problem = "unmerged index entry"
            elif file_mode not in {"100644", "100755"}:
                problem = "symlink, submodule, or unsupported Git mode"
            if not problem:
                size = int(git("cat-file", "-s", oid, cwd=root))
                if size > MAX_BYTES:
                    problem = "blob exceeds the 1 MiB public-file limit"
                else:
                    problem = content_problem(git("cat-file", "blob", oid, cwd=root))
            if problem:
                failures.append((path, problem))
    except (InspectionError, OSError, ValueError) as error:
        # Do not print captured Git output, paths from exceptions, or file content.
        print("Public boundary: unable to inspect snapshot; refusing to pass.", file=sys.stderr)
        print(type(error).__name__, file=sys.stderr)
        return 2
    if failures:
        print("Public boundary: rejected snapshot (matching content is never printed).", file=sys.stderr)
        for path, problem in failures:
            print(f"  {ascii(path)}: {problem}", file=sys.stderr)
        print("Unstage private material; see CONTRIBUTING.md and docs/data-boundary.md.", file=sys.stderr)
        return 1
    print(f"Public boundary: {count} Git blobs passed heuristic checks; human review still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
