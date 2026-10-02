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
  cycles, event counts, and controlled PRE/POST/R phase and order associations.

An intended repeated-reset failure passes only when the model promptly emits
the exact diagnostic and terminates by `SIGABRT`. Timeout 124, conventional
watchdog 137 / signal 9, resource termination signal 15, missing-tool 127,
unknown signals, fatal text with exit 0, and malformed statuses fail closed.

## One-command validation

Offline contracts need only Python 3.12 and the standard library:

```sh
python -B -m monitor.run_all --mode offline
```

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
the resulting values are therefore the actual committed LF-content hashes on
both Windows and Linux rather than hashes of platform checkout conversions.

The first archived [verified run 36952633401](evidence/run-36952633401/) used
Ubuntu 24.04, Verilator 5.020-1, GCC 13.3.0, and Python 3.12.3. It compiled
both public fixtures without warning suppression and passed its then-current
checks. Its live `fatal_text_then_hang` output files are honestly empty, so it
proves timeout rejection but not capture of the intended marker. The directory
preserves the downloaded raw text artifact, including those empty files;
[`RAW_MANIFEST.json`](evidence/run-36952633401/RAW_MANIFEST.json) records every
byte length and SHA-256 plus the workflow, artifact, PR-head, and runner merge
commit identities. No executable or expiring artifact ZIP is retained.

Copyright 2026 Wei-Lun Hsu. Original module, fixtures, checker, runner, tests,
and documentation were prepared with GitHub Copilot App assistance and are
licensed under the repository's Apache-2.0 [`LICENSE`](../LICENSE). This is an
authorship and provenance statement, not a claim of independent human
verification. The historical package elsewhere in this repository is separate
and unchanged.
