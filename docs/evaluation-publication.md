# Publishing reproducible evaluation results

The public repository can reproduce software behavior and evaluations on
public or synthetic inputs. Private-corpus findings have a different scope:
publish methodology and reviewed summaries without implying that outsiders can
reproduce the private inputs. Keep access restrictions explicit.

## Local experiment to reviewed export

1. Run the experiment locally. Record exact code revision, configuration,
   dependency versions, seeds, hardware/backend versions, metrics, and private
   input provenance in a private manifest. Store raw outputs outside Git.
2. Create a new export under `results/public/<release-id>/`; do not copy a run
   directory wholesale. Export only reviewed aggregate text tables and a
   `provenance.json` based on the synthetic example. Strip private paths,
   identifiers, samples, comments, raw prompts/generations, and file metadata.
   Review whether even aggregate values or small groups disclose private facts.
3. In the public provenance, identify the code revision and exact command,
   environment/dependency versions, seed, metric definitions, input class,
   public input references if applicable, and reproducibility limitations.
   Use `private` as the input class when appropriate; omit input references
   entirely for private sources. Keep private hashes/mappings in the local
   manifest. A seed alone does not guarantee deterministic inference.
4. For a public/synthetic evaluation, include small distributable fixtures and
   enough configuration and environment detail to rerun it. For a private
   evaluation, state that only the method or synthetic control is publicly
   reproducible. Distinguish controls from empirical reconstruction results.
5. Review every export file locally, then stage specific paths, inspect the
   complete staged diff, and run the guard and synthetic tests. Check every
   outgoing commit before publishing. Review is a human decision; passing the
   guard is not an approval or proof of privacy.

This scaffold contains no evaluation implementation, empirical result, or
claim about a reconstructed model. The example provenance and fixture describe
only a deterministic synthetic plumbing check. A future evaluation should
define its own metrics and evidence requirements without changing that label.

## Try the synthetic control

This command checks an invented record's shape and prints one aggregate.
It calls no model, reads no private file, writes no result, and tests no personal
fidelity. Run it at the code revision you record in a real public manifest:

```sh
python3 scripts/synthetic_smoke.py
```

Expected output: `{"fixture_records": 1, "valid_records": 1}`.
`configs/public-evaluation.example.json` shows the fields to populate for a
reviewed export; it is a template, not evidence that a release occurred.
