# Reset-armed trace phase monitor

This standalone engineering artifact demonstrates a narrow instrumentation
failure and its fail-closed correction: a counter that logs before reset can
produce the ambiguous synthetic sequence `Q [0, 1, 0, 1]`; the public
`trace_phase_observer` arms only after an observed reset, emits no rows before
or during reset, and rejects reset after measurement starts.

All fixture values and names are **opaque synthetic labels**. They do not
represent ISA execution, CPU coverage, an architectural oracle, a qualified
RVFI integration, or evidence of an Ibex defect. No CPU bind, CPU source,
ELF, waveform, private trace, or private full-bind hash is included.

## Implementation

- [`trace_phase_observer.sv`](trace_phase_observer.sv) is the selected
  reset-armed instrument module.
- [`trace_monitor_fixture.sv`](trace_monitor_fixture.sv) drives delayed,
  initial-low, held, asynchronous,
  missing, repeated-reset, and fatal-text-then-hang cases.
- [`unarmed_trace_counterexample.sv`](unarmed_trace_counterexample.sv) is a
  minimal fixture-only counterexample that produces `Q [0, 1, 0, 1]`; it is
  not a CPU model.
- [`process_runner.py`](process_runner.py) records typed process outcomes,
  disables core dumps only in the owned child, bounds time, and distinguishes
  exit, signal, timeout, missing-tool, and spawn failures.
- [`trace_check.py`](trace_check.py) enforces exact row widths, consecutive
  physical row order, unsigned field syntax/ranges, event counts, and
  controlled PRE/POST/R phase and order associations.

An intended repeated-reset failure passes only when the model promptly emits
the exact diagnostic and terminates by `SIGABRT`. Timeout 124, conventional
watchdog 137 / signal 9, resource termination signal 15, missing-tool 127,
unknown signals, fatal text with exit 0, and malformed statuses fail closed.

## One-command validation

Offline contracts need only Python 3.12 and the standard library:

```sh
python -B -m monitor.run_all --mode offline
```

Validate a TSV from this controlled positive fixture without installing
Verilator:

```sh
python -B -m monitor.run_all --mode check --trace path/to/events.tsv
```

Check mode is intentionally not a generic CPU, ISA, or arbitrary observer
workload validator: it requires this fixture's exact values, counts, and
`Q/B/PRE/POST/Q/R` sequence. Input is UTF-8, tab-separated, and uses the exact
decimal/fixed-width hex schema emitted by the public observer. Success prints
one JSON record with the trace SHA-256 and row counts. Rejection
exits nonzero with a line, row kind, field name, or expected physical sequence;
negative values, loose or over-width hex, out-of-range bit/index fields,
partial/extra/duplicate rows, and reordered phases are rejected.

The real replay compiles the public observer and fixtures, then executes every
case through the same strict checker:

```sh
python -B -m monitor.run_all --mode real --output monitor-output
```

Real replay requires exactly Verilator 5.020 and a C++ compiler. Builds use
`-j 1`, a 120-second build bound, and a 3-second case bound. The dedicated
GitHub-hosted job installs Ubuntu 24.04's `verilator=5.020-1`; its hosted VM
policy is separate from the user's local 8 GiB experiment floor and neither
changes nor lowers that local policy.

Run all commands from the repository root with Python 3.12 or newer. Offline
and check modes use only the standard library and are supported on Windows and
Linux. Real mode is validated on the documented Ubuntu hosted image; other
platform/toolchain combinations are not claimed.

## Expected evidence and limitations

Four positive reset shapes each produce exactly `Q [0, 1]`, one `B`, one
`PRE`, one `POST`, and one `R`. PRE/POST are associated with synthetic cycle
0 and R with cycle 1. The no-reset empty trace and fresh unarmed duplicate-Q
trace must be rejected. Repeated reset must terminate with the intended fatal;
a model that prints and flushes the exact same diagnostic before hanging must
preserve that marker in captured output and be classified as `timeout:124`,
never as the expected fatal.

The real command writes raw stdout/stderr, typed status JSON, case TSV, tool
environment, public source hashes, and the compiled model hash. It deliberately
does not retain executables. Permanent hosted evidence is archived under
`monitor/evidence/` only after an actual successful GitHub-hosted run.
[`SOURCE_MANIFEST.json`](SOURCE_MANIFEST.json) hashes each public source as
text bytes after CRLF-to-LF normalization and rejects lone carriage returns;
these are declared canonicalized text seals that verify the same logical text
across Windows and Linux checkouts. They are not necessarily hashes of the raw
Git blob bytes: the pre-existing `evidence/.gitattributes` blob is intentionally
retained with CRLF bytes, while its source-manifest seal is computed after the
declared CRLF-to-LF normalization. In contrast, each evidence
`RAW_MANIFEST.json` fixes the exact observed/downloaded bytes with no text
normalization.

The first archived [verified run 36952633401](evidence/run-36952633401/) used
Ubuntu 24.04, Verilator 5.020-1, GCC 13.3.0, and Python 3.12.3. It compiled
both public fixtures without warning suppression and passed its then-current
checks. Its live `fatal_text_then_hang` output files are honestly empty, so it
proves timeout rejection but not capture of the intended marker. The directory
preserves the downloaded raw text artifact, including those empty files;
[`RAW_MANIFEST.json`](evidence/run-36952633401/RAW_MANIFEST.json) records every
byte length and SHA-256 plus the workflow, artifact, PR-head, and runner merge
commit identities. No executable or expiring artifact ZIP is retained.

The corrected [verified run 36953631262](evidence/run-36953631262/) is the
acceptance proof for the live output regression. Its archived stdout contains
exactly `TRACE_MONITOR_RESET_AFTER_START\n`; its typed status is `timeout:124`;
and its summary records `reset_diagnostic_captured: true` with
`expected_fatal: false`. Its
[`RAW_MANIFEST.json`](evidence/run-36953631262/RAW_MANIFEST.json) independently
fixes every downloaded byte length and SHA-256. The earlier archive remains
unchanged rather than being reconstructed.

Copyright 2026 Wei-Lun Hsu. Original module, fixtures, checker, runner, tests,
and documentation were prepared with GitHub Copilot App assistance and are
licensed under the repository's Apache-2.0 [`LICENSE`](../LICENSE). This is an
authorship and provenance statement, not a claim of independent human
verification. The historical package elsewhere in this repository is separate
and unchanged.
