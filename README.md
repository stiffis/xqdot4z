# XQDot4Z — quantized dot products on RV32

Status: **M0 through M5 done**. The four variants (B1, B2, B3 and D) have
verified kernels under one frozen code-generation policy, and the registered
campaign ran **2280 of 2280 cases passing** in two simulators with none missing.
Results are in the ES/EN paper with their costs and their limits. No aggregate
speedup is computed and the grid has not been reduced; pooling regimes remains
forbidden by the manifest.

Pending: **M6**, synthesis and physical evidence — area, frequency and energy;
the **ZR** regime with zero points read at run time, which this interface cannot
express; and the **K and G** axes of RQ3, whose cost is measured and whose plan
is in [docs/EXTENSION_PLAN.md](docs/EXTENSION_PLAN.md).

The original teaching project is kept intact outside this repository; its
hash-pinned export lives in `baseline/upstream/`.

## Where to start

1. [Paper in Spanish](paper/main_es.pdf) · [source](paper/main_es.tex).
2. [Paper in English](paper/main_en.pdf) · [source](paper/main_en.tex).
3. [Why this IEEE format](docs/IEEE_FORMAT.md) and [editorial structure](docs/PAPER_PLAN.md).
4. [Kuntur: core changes and limits](kuntur/docs/CORE_CORRECTIONS.md).
5. [Reproducible verification](kuntur/verification/README.md) and [pinned evidence](docs/CORE_STATE.json).
6. [XQDot4Z numerical contract](model/SPEC.md), [Python reference](model/xqdot4z.py)
   and [how to run its tests](model/README.md).
7. [Verilog unit and the M2 battery](rtl/README.md), with [pinned evidence](docs/RTL_STATE.json).
8. [ISA interface and decisions](isa/SPEC.md), [M3a tests](tests/integration/README.md)
   and [integration evidence](docs/INTEGRATION_STATE.json).
9. [Shared MUL: core changes](kuntur/docs/SCALAR_MUL.md),
   [scalar tests](tests/scalar/README.md) and [evidence](docs/SCALAR_STATE.json).
10. [B3 arithmetic contract](rtl/packed/SPEC.md),
    [isolated B3 tests](tests/packed/README.md) and [evidence](docs/PACKED_STATE.json).
11. [B3 ISA](isa/packed/SPEC.md), [integration changes](kuntur/docs/PACKED_INTEGRATION.md),
    [in-core tests](tests/packed_integration/README.md) and
    [evidence](docs/PACKED_INTEGRATION_STATE.json).
12. [Campaign manifest and its checks](benchmarks/README.md), with the
    [single experimental protocol](docs/EXPERIMENT_PROTOCOL.md).
13. [Registration](docs/PREREGISTRATION.json) and [frozen policies](docs/POLICY_FREEZE.json),
    which fix where measuring may begin.
14. [Campaign evidence](docs/CAMPAIGN_STATE.json), [pilot](docs/PILOT_STATE.json),
    [kernels](docs/KERNEL_STATE.json) and [measurement events](docs/MEASUREMENT_STATE.json).

The two papers are equivalent versions of the same draft. They use IEEEtran in
conference mode: two columns, white background and monochrome TikZ diagrams, no
visual theme. The venue is still open. They report the registered campaign with
its costs and its limits; physical evidence — area, frequency and energy —
remains pending and is not anticipated. The earlier long-form report is kept in
`docs/archive/paper-v0.1/`.

## What this investigates

Under what conditions does fusing zero-point correction into four U4×S8 products
reduce the cost of running dot products and matrix–vector kernels, compared with
scalar multiplication and with a packed dot product corrected in factored form,
accounting for activation reuse and for the cost of delivering the zero point?

Correctness and RTL cycles first, with no board. Resources, physical time,
energy and the accuracy of a complete network need different evidence. The first
interface carries z and h as immediates, with two source GPRs and no hidden
state. It does not solve the delivery of zero points read at run time, and it is
not a standard extension.

## What each copy of the processor is for

- `baseline/upstream/`: historical export of 143 files, with its commit and a
  SHA-256 manifest. Provenance and defect reproduction only.
- `kuntur/`: Kuntur, the research core derived from kirky-arqui, versioned as an
  ordinary folder of this repository. Its previous Git history is preserved in a
  recoverable bundle. The corrections, the tests and their logs live here.
- Every variant shares those corrections, so improvements that come from fixing
  processor bugs are never credited to the extension.
- [CORE_PRE_M3.json](docs/CORE_PRE_M3.json) identifies an archived copy of the
  verified inputs of the corrected core, taken before the operation was
  integrated. It is neither another live core nor a replacement for the snapshot
  of the original project.

The corrected regression passes 26 historical programs, 28 483 decompression
vectors, 10 036 signed comparisons, policy and hazard tests, memory, registers,
four integration programs and lint. This **does not certify full RV32IC**: what
is unimplemented is delimited and rejected rather than ignored. MUL is available
with `ENABLE_MUL=1` and off by default; it is neither full M nor Zmmul. There is
no multi-cycle protocol. The memories remain combinational, 256 B each by
default, with parameterizable capacity.

## Layout

```text
xqdot4z/
├── baseline/       # untouched export, identity and hashes
├── audit/          # audit and evidence of the original
├── kuntur/         # Kuntur: corrected RTL, docs and verification/
├── docs/           # decisions, pinned evidence and the earlier report
├── paper/          # IEEE ES/EN, TikZ and bibliography
├── model/          # contract, Python reference and numerical evidence
├── isa/            # immediate ISA contract, encoder and GNU macro
├── rtl/            # XQDot4Z and packed/XQDot4 units; not another core
├── tests/          # model, unit and integration-program tests
├── benchmarks/     # manifest, kernels for the four variants and inventory
├── results/        # schema and campaign evidence; no aggregate speedup
└── scripts/        # audit and project checks
```

## Reproducing

From this directory:

```sh
make baseline-check   # integrity of the original snapshot
make audit            # replays the historical audit in a temporary copy
make core-test        # extended clone regression; fresh evidence
make model-test       # numerical reference: tests, logs and vectors
make rtl-test         # isolated unit, two simulators, lint and negative controls
make integration-test # immediate ISA and pipeline, extension on and off
make scalar-test      # isolated MUL, pipeline and coexistence with XQDot4Zi
make packed-test      # isolated B3, arithmetic comparison with D, reconstruction
make packed-integration-test # B3 ISA, eight configurations, correction in Kuntur
make kernel-test      # the four variants under the frozen policy, 188 arms
make measurement-test # measurement window, directed programs and harness mutations
make materialize      # rebuilds every planned case from its seed
make freeze-policies  # pins policy text, generators, tests and arm listings
make pilot            # the pre-registered pilot, 32 cases over 16 seed pairs
make campaign         # the registered campaign, 2280 cases in two simulators
make check            # identity, evidence hashes and ES/EN coherence
make paper            # builds main_es.pdf, main_en.pdf and main.pdf, and checks
                      # that no float leaves its column or reads out of order
```

Tools: Python 3, Icarus Verilog/vvp, Verilator and RISC-V binutils for the
tests; pdfLaTeX, latexmk, BibTeX, IEEEtran and TikZ for the papers; pdftotext
for the layout check. No network and no shell escape are needed to build.

M2/M3a, MUL and B3 also need make and C++ for the second simulator. `make audit`
checks historical execution rather than conformance: it preserves the defects
that were observed. `make check` verifies pinned evidence; it does not re-run a
simulation and does not replace the individual test targets above. After
changing the RTL, the model, its contract or its tests, the corresponding
evidence reference must be re-verified and updated deliberately.

## Evidence by milestone

M1 is done: contract, integer reference, 15 grouped tests, 524 288 single-term
insertions and 20 000 random dot products, pinned in
[MODEL_STATE.json](docs/MODEL_STATE.json).

M2 is done: 556 734 comparisons per simulator (Icarus and Verilator), eight
negative controls in each, four mutations detected in Icarus and strict lint
with no waivers. The arithmetic is combinational.

M3a is done: 25 programs in both simulators, 1056 operations in the integrated
numerical campaign, encoding checked against GNU, directed decoding, forwarding,
stalls, flush, reset and two mutations detected. Enabled with
`ENABLE_XQDOT4Z=1`, which defaults to 0. The full historical regression was
re-run with 0.

M3b is done. The optional scalar MUL passes 86 704 vectors per simulator, 49
programs in both and four MUL/XQDot4Zi configurations. Isolated B3 passes 67 910
vectors per simulator with ten negative controls each, and reconstructs 336
row/group outputs across 24 fixtures from 1680 RTL responses. Integrated B3
passes 123 programs in two simulators over eight configurations, with four
paired two-row fixtures producing eight matching outputs in B3 and D inside
Kuntur. Those programs check correctness; they are not optimized benchmarks.

M4 is done: [2280 planned cases](benchmarks/campaign.json) materialized and
recomputable from their seeds, both policies frozen against the tree, the
pre-measurement revision registered, and the campaign executed with 2280 of 2280
passing and no case missing. See [CAMPAIGN_STATE.json](docs/CAMPAIGN_STATE.json)
and [INVENTORY_STATE.json](docs/INVENTORY_STATE.json).

M5 is done: the ES/EN paper reports the central comparison per regime and phase,
decomposes the gap under a varying zero point with a structural twin, gives the
cost in code size and states three explicit limits. Every figure is pinned by a
macro and re-checked against the evidence.

What remains is M6 — synthesis, area, frequency and energy — the ZR regime,
which this interface cannot express, and the K and G axes of the sensitivity
question. None of them is a gap in what is reported; each is declared scope.

## Authorship and licence

Single author; no affiliation is claimed for now. Code and evidence are under
the MIT licence ([LICENSE](LICENSE), scope in
[docs/LICENSING.md](docs/LICENSING.md)), including the historical export, which
carries no header because it is hash-pinned and must stay byte-identical. The
**manuscript is deliberately left unlicensed** until a venue is agreed: an open
licence is easy to add and impossible to withdraw, and a later transfer of
rights may conflict with one already granted. Structure and naming conventions
were learned from Harris & Harris; no code from the book was used. Nothing has
been submitted or published to a venue.

[Charter](docs/RESEARCH_CHARTER.md), [protocol](docs/EXPERIMENT_PROTOCOL.md) and
[decisions](docs/DECISIONS.md) are revisable planning notes, not closed
commitments.

## Version control

This directory is a self-contained Git repository on `main`. Commits are small
and coherent, with Karma messages in English:
[convention](CONTRIBUTING.md). The
[organization and history record](docs/VERSION_CONTROL.md) explains how Kuntur's
earlier Git history is preserved without turning it into a submodule.
