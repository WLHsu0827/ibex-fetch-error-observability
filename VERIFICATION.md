# Verification evidence: package, automated RTL, and human boundaries

## Public package and fresh hosted gate

`python3 -B scripts/verify.py` verifies the frozen public package and checker
contracts offline. It is **not a new RTL execution**. The separate
[workflow](.github/workflows/replay.yml) installs tools from public package
sources on GitHub-hosted Ubuntu 24.04, then stages, rebuilds, replays, lints
and strictly compares against the unchanged public observations.

**Hosted execution status: pending.** No passing hosted run is claimed yet.
An actual run URL, checked commit, installed environment, job outcomes and
per-suite pass counts will be recorded only after inspecting the run and
its public evidence artifact. A new automated host is not independent
human validation. **Independent end-user manual RTL execution remains
unverified**, as do binary reproducibility and the cause of historical
binary differences.

**Preserved failed hosted attempt:** [run 36885980667](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/36885980667)
tested `be309fb4e54363b6f39e7e2b4401486d6a89a27c`. The package job passed
all 12 tests; the freshly built standalone cache passed **3/3** and its
JSON hash matched the frozen cache. The whole-core pre-build tool-version
hook failed with `ModuleNotFoundError: No module named 'packaging'`.
Whole-core replay, default-off lint and final comparison were **not run**;
this is not a passing RTL gate. The public failure artifact includes the
actual environment, commands/exit codes, cache JSON and failure log.
The follow-up pins the missing public Python dependency and the exact
observed apt package revisions; the upstream tool check is not bypassed.

The checker upgrade rejects duplicate JSON keys and JSON boolean/numeric
type substitutions rather than silently accepting them. The audit now
locks all eight existing observation/replay JSON files to their recorded
byte hashes. Its legitimate Git-worktree support verifies the bundle root
and publication history; only app-private `refs/copilot/checkpoints/*`
(not pushed by a normal branch push) are excluded. Other reachable refs
remain audited. No frozen source, manifest, patch, observation, historical
dataset or license/notice bytes were rewritten.

## Original agent-executed RTL verification on the same WSL host

**Executed**, with the corrected Copyright 2026 Wei-Lun Hsu / Apache-2.0
experiment headers. The four earlier raw JSONs are preserved, unchanged,
under [historical/](historical/README.md); their source hashes are *not*
used for the present source or replay.

## Inputs and isolation

On Ubuntu 24.04.5 LTS (WSL2), with Python 3.12.3, Verilator 5.020,
FuseSoC 2.4.3, Edalize 0.6.8 and g++ 13.3.0, the public upstream
`https://github.com/lowRISC/ibex.git` was **network-cloned twice** into
separate ignored directories outside this bundle:
`build/fetch_error_pilot/release_record/ibex` and
`build/fetch_error_pilot/release_replay/ibex` within the *isolated*
worktree. Each clone had its own `.git`, `core.autocrlf=true` set **locally**,
an initially clean tree and a detached checkout at
`7cd891ef267e8db36813b29cb8851142ab2636d5`. Nothing from either
checkout's `.git`, compiled binaries, output directory or VCD is included
in this repository.

For each checkout, `scripts/stage.py` verified the bundle's
[source manifest](SOURCE_MANIFEST.json), the pinned upstream RTL hashes
and patched Simple System hashes, then applied only the two-file opt-in
patch and copied four experiment files from this bundle. The post-stage
Git status in the second checkout had only the two Simple System changes
and the four new fixture files. The generated output was written
exclusively to **that checkout's** ignored `build/fetch_error_pilot/`.
The exact clone/pin/stage/build/replay/lint/compare commands are in
[REPRODUCE.md](REPRODUCE.md).

This WSL host **did not** have system-wide Verilator/FuseSoC or libelf
development headers. Execution used the already provisioned Verilator,
FuseSoC/Edalize and libelf-dev *tools* from a separate ignored
`build/fetch_error_pilot/tools/` directory in the worktree; no tool
bundle was included in this repository. An initial opt-in build failed
because `libelf.h` was not on the compiler include path; supplying the
host's existing development header/library resolved it. The second
clone's first opt-in build attempt hit a transient DrvFS `stat: Cannot
allocate memory` error despite available memory; a retry with a single
make job passed. These failed attempts are not counted as passing tests.

## Measured results and recorded bytes

| Check | Newly recorded source | Fresh isolated replay |
| --- | --- | --- |
| Standalone I-cache `run.py --trace` | 3/3 PASS | 3/3 PASS |
| Opt-in Simple System `--target=sim --ICache=1 --FetchFaultPilot=1` | Newly built model | Independently newly built model |
| Whole-core `run_core.py` with RVFI/CSR truth | 3/3 PASS | 3/3 PASS |
| Default-off Simple System `--target=lint --ICache=1` | PASS | PASS |
| `scripts/compare.py` on **current** JSON | N/A | PASS: complete source hashes, case events, expectations and checker classifications agree |

Unabridged [cache raw JSON](observations/results.json) SHA-256:
`440a64d2eb4fd3b9ebbb956eb3c7ea0f4daa4859ace7935d846d7afc1cfe291f`.
The independently [replayed cache JSON](verification/replayed_cache.json)
has **the same SHA-256 and is byte-identical**. The new
[whole-core raw JSON](observations/core_results.json) SHA-256 is
`48fd2235e5472c88d4935577dc1322590dbfbfe9174c218501c408207d3ff2c3`;
the [whole-core replay JSON](verification/replayed_core.json) is
`cb843d8296b220757bc0f79cb1e9e206a110fd9d921ae26b281ccfc8c85b40da`.
They are **not** byte-identical: the freshly built binary hashes are
`b92eb8d302b4ed7f3272741e88fc3548d59d0da150ecc7a24d5b121a54d416c3`
and `e4e7d98990b3615f60bad17ffc18286e58c0031bfae2b1e864e364b797914010`
respectively. All other parsed JSON fields match, including exact
cycle-tagged events. The cause of the binary-byte difference was **not
established**.

Relative to the [older raw JSON](historical/README.md), the current
source hashes changed for the three author-corrected source files
`tb.sv`, `run.py`, `run_core.py` and newly annotated
`core_program.vmem`. Both freshly generated suites have the **same
per-case events and classifications as the historical measurements**;
the older raw results were not rewritten or attributed to the new code.
For the three deliberately chosen whole-core cases, with target-PC RVFI
trap/retirement as independent truth, bus TP/FP/FN/TN = **1/1/0/1** and
cache-to-IF = **1/0/0/2**. Warm speculative bus error remains an
architectural negative (NOP retires without trap); cold demanded miss
traps with `mcause=1`, `mepc=mtval=0x00100100`.

**Those historical runs did not verify:** fresh tool installation, another
host/OS or CI, end-user independent manual execution, or security/legal
review. Merely hosting those measurements does not constitute a new RTL
run on GitHub; hosted evidence, if available, is recorded separately above. The
checked scenarios are three directed trials, not a population-level
fault rate, novel Ibex bug or paper.

A separate local package-only copy was staged in a brand-new Git repo
with zero commits and remotes and a *repository-local* GitHub noreply
identity. Its 29 candidate files were copied byte-for-byte (including
19 Git `-text`-protected source, data and notice blobs), and
`scripts/audit.py` plus `scripts/compare.py` passed **from that copy**.
From this *copied package*, `scripts/stage.py` also succeeded against
a **third, clean, pinned** upstream checkout (cloned locally from the
publicly fetched source); only the two patch targets and four fixture
files appeared as changes. This was a **staging-only** packaging check,
not a third compilation/replay. It tests the future independent folder
repository layout; it was not a fresh-system toolchain or
post-distribution RTL test.
