"""Integration tests using disposable Git repositories and invented content only."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/check_public.py"


class PublicBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.git("init", "-q")
        self.git("config", "user.name", "Boundary Test")
        self.git("config", "user.email", "boundary-test@example.invalid")
        shutil.copyfile(ROOT / ".gitignore", self.repo / ".gitignore")
        self.git("add", "--", ".gitignore")

    def git(self, *args, check=True):
        return subprocess.run(
            ["git", *args], cwd=self.repo, env=self.env, capture_output=True, check=check,
        )

    def write(self, path, content="invented test content\n"):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode() if isinstance(content, str) else content)

    def stage(self, path, content="invented test content\n"):
        self.write(path, content)
        self.git("add", "-f", "--", path)

    def guard(self, *args):
        return subprocess.run(
            [sys.executable, str(GUARD), *args], cwd=self.repo, env=self.env,
            capture_output=True, text=True,
        )

    def assert_rejected(self, reason):
        result = self.guard("--staged")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(reason, result.stderr)
        return result

    def test_public_source_synthetic_fixture_and_reviewed_result_pass(self):
        for path in ("src/example.py", "configs/example.json", "docs/method.md",
                     "tests/fixtures/synthetic/example.jsonl", "results/public/control/metrics.csv"):
            self.stage(path)
        result = self.guard()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ignored_private_material_stays_untracked(self):
        for path in ("private/letter.txt", "local/run.json", "src/data/sample.csv",
                     "recordings/voice.wav", "models/example.bin", "outputs/answer.txt",
                     "results/draft.csv", "configs/.env.production", "docs/scan.pdf",
                     "tests/fixtures/synthetic/recording.flac", "src/__pycache__/test.pyc"):
            with self.subTest(path=path):
                self.write(path)
                self.assertEqual(self.git("check-ignore", "-q", "--", path, check=False).returncode, 0)
        self.git("add", "--all")
        self.assertEqual(self.git("ls-files").stdout.decode().splitlines(), [".gitignore"])

    def test_force_added_reserved_directory_is_rejected(self):
        self.stage("docs/private/letter.txt")
        self.assert_rejected("reserved local/private directory")

    def test_case_variants_of_private_paths_are_rejected(self):
        self.stage("tests/fixtures/CoRpUs/note.json")
        self.assert_rejected("reserved local/private directory")

    def test_unknown_root_and_unreviewed_results_are_rejected(self):
        for path in ("notes.txt", "results/draft.csv", "unclassified/notes.md"):
            self.stage(path)
        self.assert_rejected("outside approved public paths")

    def test_media_weights_archives_notebooks_and_keys_are_rejected(self):
        for suffix in ("wav", "png", "pdf", "safetensors", "gguf", "pt", "pkl",
                       "npz", "parquet", "sqlite3", "zip", "ipynb", "pem", "log"):
            self.stage("docs/blocked." + suffix)
        result = self.assert_rejected("not an approved public text format")
        for suffix in ("wav", "png", "pdf", "safetensors", "gguf", "pt", "pkl",
                       "npz", "parquet", "sqlite3", "zip", "ipynb", "pem", "log"):
            self.assertIn("docs/blocked." + suffix, result.stderr)

    def test_environment_and_credential_filenames_are_rejected(self):
        for path in ("configs/.env", "configs/.env.production.json", "configs/secrets.json",
                     "configs/credentials.json", "docs/id_ed25519.txt"):
            self.stage(path)
        self.assert_rejected("credential/environment filename")

    def test_partial_staging_cannot_hide_secret(self):
        token = "ghp_" + "A" * 36
        self.stage("src/example.py", 'token = "' + token + '"\n')
        self.write("src/example.py", "# clean unstaged replacement\n")
        result = self.assert_rejected("GitHub token signature")
        self.assertNotIn(token, result.stderr + result.stdout)

    def test_unstaged_secret_does_not_contaminate_clean_index(self):
        self.stage("src/example.py", "# clean staged content\n")
        self.write("src/example.py", "ghp_" + "A" * 36)
        self.assertEqual(self.guard().returncode, 0)

    def test_multiple_credential_signatures_are_rejected_without_echo(self):
        samples = (
            ("private-key header", "-----BEGIN " + "OPENSSH PRIVATE KEY-----"),
            ("AWS access-key signature", "AKIA" + "A" * 16),
            ("GitHub token signature", "github_pat_" + "A" * 40),
            ("API token signature", "sk-proj-" + "a" * 32),
            ("Slack token signature", "xoxb-" + "1" * 30),
            ("Google API-key signature", "AIza" + "a" * 35),
            ("credential-bearing URL", "https://" + "invented:fake-password@example.invalid"),
            ("literal credential assignment", 'api_key = "' + "invented-value-0123456789" + '"'),
        )
        for reason, sample in samples:
            with self.subTest(reason=reason):
                self.stage("configs/example.txt", sample)
                result = self.assert_rejected(reason)
                self.assertNotIn(sample, result.stderr + result.stdout)

    def test_oversized_binary_and_non_utf8_blobs_are_rejected(self):
        self.stage("docs/large.txt", b"a" * (1024 * 1024 + 1))
        self.stage("docs/binary.txt", b"abc\x00def")
        self.stage("docs/encoding.txt", b"\xff")
        result = self.assert_rejected("1 MiB")
        self.assertIn("binary content", result.stderr)
        self.assertIn("non-UTF-8 content", result.stderr)

    def test_symlink_is_rejected_without_following_target(self):
        self.write("outside.txt", "invented local material\n")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/link.txt").symlink_to("../outside.txt")
        self.git("add", "--", "docs/link.txt")
        self.assert_rejected("symlink, submodule")

    def test_submodule_is_rejected(self):
        self.git("commit", "-qm", "test base")
        oid = self.git("rev-parse", "HEAD").stdout.decode().strip()
        self.git("update-index", "--add", "--cacheinfo", "160000," + oid + ",src/module")
        self.assert_rejected("symlink, submodule")

    def test_lfs_pointer_is_rejected_even_in_text_file(self):
        self.stage("docs/pointer.txt", "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 1\n")
        self.assert_rejected("Git LFS pointer")

    def test_committed_tree_ignores_clean_index_and_worktree(self):
        self.stage("src/example.py", "ghp_" + "A" * 36)
        self.git("commit", "-qm", "invented unsafe snapshot")
        self.stage("src/example.py", "# clean staged replacement\n")
        result = self.guard("--tree", "HEAD")
        self.assertEqual(result.returncode, 1)
        self.assertIn("GitHub token signature", result.stderr)
        self.assertEqual(self.guard("--staged").returncode, 0)

    def test_clean_commit_tree_passes(self):
        self.stage("docs/method.md")
        self.git("commit", "-qm", "public test snapshot")
        self.assertEqual(self.guard("--tree", "HEAD").returncode, 0)

    def test_unmerged_index_is_rejected(self):
        self.stage("docs/conflict.txt")
        oid = self.git("rev-parse", ":docs/conflict.txt").stdout.decode().strip()
        self.git("update-index", "--force-remove", "--", "docs/conflict.txt")
        subprocess.run(
            ["git", "update-index", "--index-info"], cwd=self.repo, env=self.env,
            input=f"100644 {oid} 1\tdocs/conflict.txt\n".encode(), check=True,
            capture_output=True,
        )
        self.assert_rejected("unmerged index entry")

    def test_unsafe_filename_is_escaped_in_diagnostics(self):
        self.stage("docs/newline\nname.txt")
        result = self.assert_rejected("control character")
        self.assertIn("newline\\nname", result.stderr)
        self.assertNotIn("newline\nname", result.stderr)

    def test_invalid_revision_and_non_repository_fail_closed(self):
        result = self.guard("--tree", "not-a-revision")
        self.assertEqual(result.returncode, 2)
        self.assertIn("refusing to pass", result.stderr)
        result = subprocess.run(
            [sys.executable, str(GUARD)], cwd=self.repo.parent, env=self.env,
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)

    def test_installed_hook_rejects_private_commit(self):
        hook_dir = self.repo / ".githooks"
        hook_dir.mkdir()
        shutil.copy2(ROOT / ".githooks/pre-commit", hook_dir / "pre-commit")
        (hook_dir / "pre-commit").chmod(0o755)
        (self.repo / "scripts").mkdir()
        shutil.copy2(GUARD, self.repo / "scripts/check_public.py")
        self.git("config", "core.hooksPath", ".githooks")
        self.stage("private/letter.txt")
        result = self.git("commit", "-qm", "must not commit", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"reserved local/private directory", result.stderr)
        self.assertNotEqual(self.git("rev-parse", "--verify", "HEAD", check=False).returncode, 0)


class SyntheticControlTests(unittest.TestCase):
    def test_control_reports_only_fixture_shape(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/synthetic_smoke.py")], capture_output=True,
            text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout), {"fixture_records": 1, "valid_records": 1})


if __name__ == "__main__":
    unittest.main()
