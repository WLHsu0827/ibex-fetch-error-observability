# RVFI next-PC inputs: PRE-HDL STOP / NOT_QUALIFIED

**PRE-HDL STOP / NOT_QUALIFIED: zero real CPU builds.** Both
authorized preparation attempts are consumed. The second failed the strict
Python dependency-closure gate, so there was no RTL checkout, stock bind lint,
HDL miniature, program compilation, OFF/ON CPU build or pair dispatch.
Sampler qualification and ISA execution are **NOT_RUN**; strict RVFI next-PC
conformance is **NOT_QUALIFIED**, neither PASS nor FAIL. No third preparation
or another pair is authorized. No HDL was built/simulated locally.
This is a candid partial owner-repository artifact, not acceptance of a
working/qualified whole-core reproducer. It is independent of the original
bundle and open, unmerged public PR1/PR2; neither is a build dependency.

## Actual bounded result and immutable identities

| Identity/stage | Actual result |
| --- | --- |
| Final attempted input source | `c50b3975c188eea33bb7e92cb75b21bc9a04f9e2` |
| Distinct evidence archive commit | `1203b53e7715dfcc8b1e30987dd247cec7127751` |
| [Preparation 1](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37037708980) / input `b25f2d215e1652e3d102f3aa4f2478ad64b42a13` | STOP: unavailable guessed cross-tool pins; original artifact also INCOMPLETE (one hidden source file omitted) |
| [Preparation 2](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37039019400) / final input above | STOP: nine unpinned Python transitive dependencies; complete raw archive integrity PASS, scientific result NOT_QUALIFIED |
| Real program/CPU/pair attempts | 0 program compilations, 0 OFF/ON CPU builds, 0 pair dispatches |
| Actual core retirements / branches | 0 / 0 **because no core run occurred**, not an empty passing trace |
| Actual widths / outcome cells | Not measured; the eight cells below are goals, not achieved coverage |
| Pre-run ISA path, tool/model/config freeze | Not created; preparation did not qualify |

The second run passed all 16 hosted pure-stdlib contracts, including prompt
POSIX fatal and fatal-marker-plus-hang rejection. It recorded Ubuntu 24.04
and dpkg identities Verilator=5.020-1, cross GCC=13.2.0-11ubuntu1+12 and
binutils=2.42-1ubuntu1+6. The subsequent actual-executable-version stages were
**not reached**; package identities must not be called executable qualification.
The unpinned closure was `jsonschema 4.26.0`, `zipfile2 0.0.12`,
`jsonschema2md 1.7.0`, `babel 2.18.0`, `jsonschema-specifications 2025.9.1`,
`markdown 3.11`, `referencing 0.37.0`, `rpds-py 2026.6.3` and
`typing-extensions 4.16.0`. These are a remaining tooling blocker, not a DUT
or metadata finding. No closure/oracle gate was weakened to continue.

The [machine-computed evidence index](evidence/INDEX.json) records the exact
run/artifact/source/manifest identities and zero-real-attempt journal.
Preparation 1 artifact `11241097111` has Actions digest
`sha256:9ec08523d2713395fdddb43a14d406d3a466f1d93e6978b23d66ea7b517b8a0e`;
its original RAW_MANIFEST SHA256 is
`75f9f813c11ea9b4c2781033fdc8cee93dd90c680fd41f98a890e258993a9744`.
Preparation 2 artifact `11241379084` has Actions digest
`sha256:eb9385c0fa0e3fc5fa257c5f131b57af535ebc83f18491754c12ed435a59f656`;
its RAW_MANIFEST SHA256 is
`06750c5684d6b45bd8690653de1d4eb08d2a05d35f25f55fa2572f70516ab10a`.
Outer artifact digests identify the uploaded ZIP, while raw manifests identify
their member bytes; they are not interchangeable. Final documentation head
and its exact-head offline CI are recorded on the owner PR, not self-hashed
into these prior immutable receipts.

Initial source `f80fa2b5beca8d0777b88ae574f69ad7b972bedf` and failed
[push offline run](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37037318099) /
[PR offline run](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37037374236)
are retained unchanged. They were offline source-seal failures, not additional
authorized preparation or CPU attempts. Further hosted qualification requires
fresh approval routed through the coordinator; this work does not claim that
approval or coordinator acceptance.

The first input-only push exposed Windows CRLF versus Git blob LF hashing
in offline CI; it is retained in history, not amended or represented as HDL
evidence. The source seal uses Git's LF-normalized new-text representation;
the existing LICENSE keeps its original byte identity. Hosted source exports,
program and raw evidence still use actual byte lengths/SHA256, never line
ending normalization of observed streams.

Preparation 1's original artifact is also preserved **INCOMPLETE**, not
rewritten/reconstructed or promoted to full integrity PASS: upload-artifact's
default hidden-file exclusion omitted `input/.github/workflows/rvfi-nextpc.yml`,
although the original raw manifest references it. A separate collection
receipt identifies that precise pre-HDL source gap and original manifest/
artifact identities; every retained byte is still checked. The workflow now
explicitly includes hidden files from its reviewed output-only staging area.
This exception cannot admit missing observed records or any real CPU attempt.

## Scope and preregistration

Pinned public stock Ibex:
[`4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8`](https://github.com/lowRISC/ibex/tree/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8).
The DUT is the full `ibex_top`, including the unmodified stock core and
register file. FuseSoC exports stock dependencies, fetched only on ephemeral
GitHub-hosted runners. No DUT RTL is vendored, patched or oracle-weakened.

The controlled pair uses RVFI=1, RV32ZC=RV32Zca, WritebackStage=0,
BranchTargetALU=0, ICache=0, RV32MFast, and BranchPredictor=0/1.
**The ON configuration is a custom combination outside the named supported
set.** The stock `experimental-branch-predictor` configuration instead uses
WritebackStage=1, BranchTargetALU=1 and RV32ZcaZcbZcmp. The feature is
experimental and known/not-yet-verified functionality must not be presented
as a production guarantee. No named-config extra pair is authorized here.

`program.S` is freshly authored: four backward loops with a last not-taken
iteration (`c.beqz`, `c.bnez`, `beq`, `bne`), plus forward taken/not-taken
controls for each comparison form. Coverage is preregistered as all **eight
width (16/32) x direction (backward/forward) x actual outcome (0/1) cells**.
No inherited trace lengths, branch counts, hashes or expected mismatch
counts are used. `isa.py` separately decodes instruction bits, executes
RV32I/Zca semantics and freezes the complete dynamic ISA path, writebacks,
operands, branch outcomes and required successor PCs from the fresh binary
**before OFF compilation**. Branch outcome is not inferred from symbol names,
prediction, trace labels or the DUT's `pc_wdata`.

The linked start is `0x80000080`; the boot input is `0x80000000` (stock
Ibex boots at +0x80). The first RVFI record must be dynamic order 0 at the
fresh start, with no earlier record silently discarded. All program records,
three explicit 32-bit NOP drain instructions, and four terminal `jal x0,0`
retirements are retained and checked. The binary ends at the terminal word.
Other ROM words are explicit NOP fill for speculative fetch, not an accepted
extra retirement. The driver exits only after the fourth terminal retirement,
after both sampling phases; the cycle budget is 20000 and run wall time is
60 seconds. No traps, interrupts, halt, data traffic or DUT alerts are allowed.

## Independent output-port sampling

`sample.hpp` reads exported DUT ports in C++ immediately after rising-edge
`eval()` convergence. Separately, `rvfi_observer.sv` is **bound directly to
the stock `ibex_top` output ports** and reads them at the following falling
edge, before the next rising-edge state update. Each writes its own complete,
flushed raw TSV stream; neither reads the other, reconstructs next-PC, alters
the DUT or controls termination. They join by dynamic RVFI order/PC/instruction
and compare every recorded retirement field, never by cycles or static PC.
The Q stream observes reset, software/timer/external/fast/NMI/debug request
inputs and RVFI debug-mode state. R records contain actual trap/halt/intr,
operand/writeback and interrupt/debug RVFI extension fields.
SV also records asynchronous reset assertion; Q indices/counts are therefore
local to each sampler and deliberately are not used to join retirements.

This rules out a disagreement specific to these two port readers/phases when
they agree. It does **not** establish simulator-independent sampling, exclude
all binding/NBA/model semantic errors, prove the core's intended RVFI capture
contract, independently verify the instrumentation by a human, or establish
architectural misexecution. A successful synthetic three-retirement miniature,
missing-reset fatal, reset-after-start fatal, marker-plus-hang timeout rejection,
and full stock-interface/bind fatal-warning lint are hosted preparation gates.
Only the unchanged stock lint waiver file is inherited; no new warning
suppression/nonfatal switch is added. Upstream diagnostics cause STOP, not
an excuse to modify the DUT or suppress warnings.

`check.py` rejects malformed, duplicate, missing or reordered records,
missing/reasserted reset, unexpected controls, sampler disagreement,
program/ISA/writeback mismatch, premature exit and extra records. Strict
next-PC conformance is checked separately against decoded ISA successors and
the following retirement where one exists, including the explicit drain and
terminal. ON mismatches are retained as **intrinsic strict metadata FAIL**;
archive closure or a green workflow is not a pair/scientific PASS.

## Bounded hosted operation

Normal push, pull-request and evidence-head CI is **offline/archive-only**.
Only explicit `workflow_dispatch` can install tools or perform HDL work.
The workflow requires the full immutable input SHA and the exact authorization
identity in `AUTHORIZATION.json`. GitHub run history, run-attempt=1 and an
exclusive receipt gate at most two preparation-only dispatches and one pair.
Preparation source changes require another same-source preparation. There
are no automatic retries; after OFF compilation begins the harness, program,
oracle, sampler, source and tools are frozen and no retry/refreeze is allowed.
ON can build only after qualified OFF execution, independent sampler agreement
and strict OFF next-PC PASS. If any gate fails, the remaining pipeline stops.

Ubuntu 24.04, Verilator **5.020-1**, cross GCC **13.2.0-11ubuntu1+12** /
binutils **2.42-1ubuntu1+6**, and the requested Python dependencies
are version-pinned. Complete closure equality is enforced, not assumed
(and was the final STOP here). Planned actual versions, package license provenance,
wheel URLs/hashes, reported affinity CPUs/memory/cgroup/disk, source exports,
configs, commands and typed statuses are retained. All compilation uses
`-j1`, recursive make inherits `MAKEFLAGS=-j1`, each real build is bounded
to 1500 seconds, and the job to 60 minutes (pipeline budget 55 minutes).
Reported hosted resource values are not local Windows/WSL floors, exclusive
host ownership, or performance/PPA measurements.

The fresh program is compiled once per authorized pair; exactly the same
binary is loaded OFF/ON. Its ELF/binary/hash/disassembly, bit-decoded pre-run
contract, source/tool/config hashes and equivalence checks are frozen before
OFF. Exported source bytes and EDAM must match except BranchPredictor.
`freeze.json` is exclusively created before the first CPU build. That receipt
is an execution-order record backed by public CI history, **not a trusted
timestamp or a claim that a posthoc hash proves pre-run history**.

`process.py` writes stdout/stderr directly as bytes to exclusive files. Typed
`exited`, `signaled`, `timed_out` and `spawn_error` receipts preserve command,
duration, timeout, lengths and SHA256. A fatal marker followed by a hang stays
timed_out; an intentional fatal fixture requires prompt SIGABRT plus marker.
Python failure closure is independent of the scientific comparison and retains
attempted stages, exception, summary and `RAW_MANIFEST.json`. The outer Actions
artifact identity and later Git archive commit close the manifest without a
self-hash cycle. Abrupt host loss/job cancellation cannot guarantee Python
finally/upload execution: missing closure is an unqualified STOP, not success.

## Entry points

Offline, pure stdlib, on Linux (no installs, HDL or GitHub credentials):

```sh
python3 -B -m rvfi_nextpc.seal && python3 -B -m unittest rvfi_nextpc.tests -v && python3 -B -m rvfi_nextpc.archive
```

The agent uses `py -3.12 -B` for the same lightweight checks on Windows.
The real hosted entry point is an explicit one-command Linux `gh` dispatch
(placeholders require immutable, qualified identities and fresh approval;
the current exhausted authorization cannot run it successfully):

```sh
gh workflow run rvfi-nextpc.yml --repo WLHsu0827/ibex-fetch-error-observability --ref OWNER_BRANCH_AT_INPUT_SHA -f mode=pair -f source_sha=INPUT_SHA -f authorization=WLHsu0827-2026-10-03-rvfi-nextpc-one-pair -f preparation_attempt=0 -f preparation_run=SUCCESSFUL_SAME_SOURCE_PREPARATION_RUN
```

Preparation uses the same command with `mode=prepare`,
`preparation_attempt=1` (or the sole permitted second attempt) and no
preparation_run. **These commands do not grant another pair.** After the
authorized pair/STOP, independent humans need new explicit authorization
and a distinct attempt identity; the existing workflow rejects reruns.
GitHub dispatch requires a branch/tag ref (a bare SHA dispatch was rejected
with HTTP 422 and created no run); checkout/source qualification still requires
the full immutable source SHA and exact dispatch head match.

## Public contract, source support and limitations

The [RVFI PC contract](https://github.com/SymbioticEDA/riscv-formal/blob/4f29e83a8387a81467716548f165fd97045af617/docs/rvfi.md#L59-L64)
and pinned ISA
[Zca](https://github.com/riscv/riscv-isa-manual/blob/51c1291fc8168bf36530de3386d3f452069ce327/src/unpriv/zca.adoc) /
[RV32](https://github.com/riscv/riscv-isa-manual/blob/51c1291fc8168bf36530de3386d3f452069ce327/src/unpriv/rv32.adoc)
are the independent semantic references.
Stock [RVFI capture](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/rtl/ibex_core.sv#L2078-L2093)
includes `pc_set ? branch_target_ex : pc_if`; this is a source-supported
metadata candidate, not proof of a DUT bug.
The [fetch reference](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/doc/03_reference/instruction_fetch.rst#L31-L45),
[RVFI caveats](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/doc/03_reference/rvfi.rst#L1-L15)
(I/C not yet formally verified), and
[experimental config](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/ibex_configs.yaml#L184-L211)
limit interpretation. No inspected documentation grants a speculative
next-PC RVFI contract exception.

Related [lowRISC/ibex#2231](https://github.com/lowRISC/ibex/issues/2231)
(mret/dret metadata), [lowRISC/ibex#2331](https://github.com/lowRISC/ibex/issues/2331)
(controller-only prediction/flush report; whole-core reproduction requested),
and [lowRISC/ibex#1462](https://github.com/lowRISC/ibex/issues/1462) /
[lowRISC/ibex#1469](https://github.com/lowRISC/ibex/issues/1469)
(older execution-path cases) are not this confirmed case. Bounded searches
cannot establish novelty. This owner-repository observation makes no new-bug,
novel-method, paper, general error-rate, PPA or human-replication claim and
does not submit anything upstream or merge itself.

## Rights and publication boundary

Original fresh code/program/tests/prose: Copyright 2026 Wei-Lun Hsu,
Apache-2.0 under [../LICENSE](../LICENSE). GitHub Copilot App assisted;
agent-executed checks are not human attestation. See [NOTICE](NOTICE) and
[REVIEW.md](REVIEW.md). Public stock RTL/generators retain their existing
copyright, licenses and notices. No private experiment, ELF, log, receipt,
personal/corporate file, original bundle change or sibling checkout is input
to this unit.
