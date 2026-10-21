# Contributing to alea2

This is a public, MIT-licensed source repository. Treat every commit, branch,
pull request, issue, CI log, and uploaded artifact as public.

Start with [the data boundary](docs/data-boundary.md) and
[the evaluation publication workflow](docs/evaluation-publication.md).
The original README and license are preserved by this scaffold.

## Enable the local safeguard

Requires Git and Python 3.10 or later; no Python packages are needed.
From the repository root:

```sh
git config --local core.hooksPath .githooks
python3 scripts/check_public.py --staged
python3 -m unittest discover -s tests -v
```

Check `git config --get core.hooksPath` before setting it if you already use
hooks: integrate this guard with your existing pre-commit hook instead of
replacing it. Hooks are not enabled automatically by cloning or applying a
patch. On Windows, use a Git/Python environment where `python3` is available.

The hook checks the entire staged snapshot, including previously tracked files
and files force-added despite ignore rules. It reads Git blobs, so an unstaged
edit cannot hide staged content. It makes no network requests, changes no
files, and reports paths and rule names without printing matching content.
To check a commit instead: `python3 scripts/check_public.py --tree HEAD`.

## Before every public commit

1. Keep private archives, transcripts, recordings, weights, credentials, and
   raw runs outside the checkout. Ignored local directories are a convenience,
   not access control, encryption, or backup.
2. Stage specific public paths. Review `git diff --cached --name-status` and
   `git diff --cached --check`, then review the full staged diff locally for
   private text, identifiers, prompts, outputs, and metadata.
3. Run `python3 scripts/check_public.py --staged`. Fix the cause of a rejection;
   do not use `git add -f` or skip hooks as a publication workaround.
4. Commit only reviewed material. For results, include the public provenance
   record described in the evaluation workflow.

The guard is a heuristic tripwire. It cannot recognize arbitrary private prose,
identify a person, establish consent, or prove that a result is safe to release.
It checks the candidate snapshot, not earlier commits or other branches.
Review all outgoing commits before pushing; a clean tip cannot repair an
earlier leak. Local hooks can be bypassed. CI is a backstop after upload and
cannot prevent the initial disclosure to GitHub. No remote settings are changed
by this patch. A maintainer can separately require the `public-boundary` job
for merges and enable GitHub secret scanning/push protection where available.

If a private file was staged, use `git restore --staged -- path` (or
`git rm --cached -- path` for an already tracked file), then keep it local.
Removing it from the next commit does not remove it from existing history.
If a secret was published, revoke/rotate it promptly; coordinate removal from
history and any copies, logs, caches, or artifacts. Do not post the content in
a public issue to report the incident.

Changes to the guard, ignore rules, workflow, or permitted paths need the same
careful review as publication decisions. Add regression tests when changing
the boundary. Do not add a blanket skip switch or a broad data-file exemption.
