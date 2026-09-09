# Repository layout and preserved history

On 2026-09-09, the research directory became one Git repository on `main`,
starting with a single baseline commit. Future work follows the
[English Karma-style convention](../CONTRIBUTING.md).

`kuntur/` is tracked as ordinary files, not a submodule or an embedded Git
link. A clone of the root repository therefore contains the current processor,
its verification inputs, and the selected research evidence without relying
on a local path or an unpublished remote repository.

## Earlier Kuntur repository

Kuntur previously had an independent repository on `research/core-corrections`.
Its existing commits were preserved without rewriting them in
[kuntur-history.bundle](../baseline/kuntur-history.bundle), created with
`git bundle create --all` and verified before the layout change. This is a
portable archive of its committed history, not an additional commit in the
root repository's ancestry. The current processor files are also tracked
directly in the root repository.

The archived Kuntur HEAD is `b6ddb1072c3639952daee2400901db311d4307f7`.
The bundle's SHA-256 is
`af9cbaef3470fbde162bd3f66a3faaf9cb212dfa3008ecefe3022895ca86a772`.

The previous local Git metadata was moved, without deletion, from
`kuntur/.git/` to the root's `.git/kuntur-history.git/`. That metadata remains
local and is not needed by a clone of this project. The portable bundle is
tracked; the local metadata is not. To inspect the latter:

```sh
git --git-dir=.git/kuntur-history.git --work-tree=kuntur log --oneline
```

To recover the committed history separately, choose a new, unused destination:

```sh
git clone baseline/kuntur-history.bundle /path/to/new/kuntur-history
```

The original teaching project and `baseline/upstream/` were not changed.
`kuntur/UPSTREAM.json` records the original clone's provenance; older notes
describing an independent working repository refer to that earlier layout.

## Files and reproducibility

Source code, documentation, PDFs, historical snapshots and verification
artifacts are versioned. Temporary builds, Python caches and disposable LaTeX
intermediates are not. Frozen snapshots, evidence files and files already
tracked in the earlier Kuntur repository are retained even where an inherited
ignore rule would normally hide one; this includes a historical presentation
auxiliary file. The archived research draft keeps its sources and PDF without
its disposable TeX intermediates. No working files are deleted by these rules.

`.gitattributes` disables automatic line-ending conversion: verification state
files pin exact byte hashes, which must survive a checkout. Do not apply
bulk formatting to frozen evidence. Do not edit old runs to make a new state
appear verified; create new evidence and update its references explicitly.

No remote is configured or publication performed by this initialization.
