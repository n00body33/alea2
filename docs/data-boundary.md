# Public source, local research

This scaffold defines storage and publication boundaries. It chooses no model,
architecture, training method, inference backend, or hardware stack.

| Location | Purpose | Publication rule |
| --- | --- | --- |
| `src/` | Reusable source code | No embedded private examples or inputs |
| `configs/` | Portable example configuration | Placeholders only; no real paths, endpoints, or credentials |
| `tests/fixtures/synthetic/` | Small, entirely invented text fixtures | Label synthetic; never paraphrase private archives |
| `tests/`, `scripts/`, `docs/` | Tests, tooling, and public methodology | Review comments, literals, examples, and metadata |
| `results/public/` | Deliberately reviewed text exports | Provenance record and disclosure review for each release |
| Outside this checkout (preferred), or ignored `local/`/`private/` | Archives, scans, recordings, transcripts, annotations, identity mappings | Local only |
| Ignored `models/`, `weights/`, `checkpoints/`, `adapters/` | Downloaded or derived model artifacts | Local only; no Git LFS exception |
| Ignored `runs/`, `outputs/`, `artifacts/`, `cache/`, `results/` outside `public/` | Raw generations, prompts, scores, logs, caches, intermediate exports | Local only until an explicit export/review |

Keep original evidence, transcriptions, annotations, reconstructions, and
synthetic material distinct in private storage. Do not turn a private example
into a public fixture by merely removing a name. Public synthetic examples
must originate independently of private material. Passing them demonstrates
software behavior only, not reconstruction fidelity.

## What the automated boundary enforces

`.gitignore` excludes common private directories, media, documents, weights,
archives, credentials, notebooks, and generated outputs. Git ignores do not
untrack an existing file or stop `git add -f`.

`scripts/check_public.py` separately checks the staged snapshot or a specified
commit tree. It rejects reserved directory names at any depth, unapproved root
paths or text types, files over 1 MiB, binary/non-UTF-8 content, symlinks,
submodules, Git LFS pointers, and several common credential signatures. Known
development/cache directories and credential filenames are also rejected.
The policy is intentionally conservative; supporting a new public text format
requires reviewing the guard and adding tests. Images, recordings, notebooks,
weights, and binary charts are not permitted by this initial policy. Publish
reviewed tables or text descriptions instead, or propose a narrow policy change.

This does not classify semantic privacy. A private letter saved as
`docs/method.md` or a real transcript in a `.json` fixture can pass. Small
aggregates can also identify people or disclose source content. Do not store
private material anywhere in an outgoing Git history, even temporarily.

## Separation during execution

Run private-data experiments locally, with explicit input/output paths outside
the checkout where practical. Supply secrets through local environment or
credential tooling; never print them into logs or serialize them into config.
Keep the exact private run manifest and evidence mapping private. Public
manifests must not include private filenames, absolute paths, identity mappings,
input hashes, excerpts, embeddings, prompts, per-person scores, or raw model
outputs. Hashing or pseudonymizing a record does not establish anonymity.

The CI workflow reads only the public checkout and runs synthetic tests. Do not
add private datasets, repository secrets, external inference calls, private
artifact downloads, or uploaded run traces to it. Use `pull_request`, not
`pull_request_target`, for this unprivileged job. GitHub Actions logs and
artifacts are part of the publication surface.
