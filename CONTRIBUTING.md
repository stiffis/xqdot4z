# Commit conventions

Use Karma-style commit messages in English:

```text
<type>(<optional scope>): <imperative subject>

<optional explanation of the change and its motivation>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
Use a short, lowercase type, an imperative subject, and no trailing period.
Keep the subject concise; put context and verification details in the body.

Examples:

```text
feat(benchmarks): add the scalar matrix-vector kernel
fix(core): preserve operands across load-use stalls
test(isa): cover reserved packed instruction encodings
docs(paper): describe the measurement boundary in both languages
```

After the initial baseline, keep commits focused on one logical change.
Do not split an implementation from the tests or evidence required to make
its recorded state consistent. Preserve unrelated work and failed-run history.
Never describe a performance improvement without measurements.

## Before committing

Run the relevant verification targets after changing their inputs, review the
new evidence, and deliberately update the corresponding state files. Run
`make check` before committing a change to pinned evidence or manuscript claims.
For manuscript changes, update both languages and run `make paper`.

Review `git diff --cached` for unrelated files, secrets, generated build
intermediates, and unsupported claims. Keep source files, the manuscript PDFs,
and reproducibility evidence; exclude caches and disposable build output.

The root repository owns the complete project, including `kuntur/` as ordinary
files. See [the repository layout](docs/VERSION_CONTROL.md) for preserved
processor history. Creating commits does not authorize pushing or publishing.
