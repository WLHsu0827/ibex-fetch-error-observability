# Ibex instruction-fetch error observability

> **Independent research repository by Wei-Lun Hsu (WLHsu0827).** This
> self-contained experiment bundle is not an official Ibex repository,
> hardware result, Ibex fix, new-bug report, or paper.
> The original material is Apache-2.0 under [LICENSE](LICENSE) and
> [NOTICE](NOTICE); upstream Ibex attribution is retained separately.

## Question, precedent, and contribution

With a single error injected on a one-cycle instruction-bus response at a
fixed address, when does a bus-error checker disagree with the
cache-to-IF accepted error and the **architectural RVFI trap/retirement**?
[Ibex issue #1451](https://github.com/lowRISC/ibex/issues/1451) described
the speculative-request/cache-hit behavior in **2021** and proposed observing
cache-to-IF. The [upstream I-cache reference](https://github.com/lowRISC/ibex/blob/7cd891ef267e8db36813b29cb8851142ab2636d5/doc/03_reference/icache.rst)
documents errors, cache hits, and speculative fills. The contribution here
is a repeatable, directed **open-source RTL pilot** that measures this known
boundary in a standalone cache fixture **and** in full-core Simple System
execution with independent RVFI/CSR observations. It does not establish
novelty or a new defect.

## Measured whole-core result

In each reset-isolated replay the target is a NOP (`0x00000013`) at
`0x00100100`; the bus grants immediately and answers one cycle later. The
faulted cases change only the **selected response's `instr_err_i`**, not data
or latency. Warm cases arm after a line write, an observed cache hit and at
least four target retirements; the cold case arms at the first target request.
The no-error warm case is a matched negative control.

| Case (one replay) | Selected bus error | Accepted cache-to-IF error | RVFI target trap | Post-response target RVFI retirements | Response data path |
| --- | ---: | ---: | ---: | ---: | --- |
| Warm hit, no injected error | 0 | 0 | 0 | 20 | Cache hit |
| Warm hit, speculative bus error | 1 | 0 | 0 | 20 | Cache hit |
| Cold demanded miss, bus error | 1 | 1 | 1 | 0 | Bus |

The warm pair request at cycle **275** and respond at **276**, with matching
cache-hit signals (`tag_hit=1`, `fill_data_hit=8`, `fill_data_rvd=0`).
Cache-to-IF accepts an error-free NOP in both cases at 276; RVFI retires it
at 278, including when the external response reports an error. The cold
request at 8 responds at 9 with bus-data output and an accepted IF error;
RVFI traps at 11, retires the handler, and reports `mcause=1`,
`mepc=mtval=0x00100100`.

For **three deliberately chosen deterministic replays (n=3, one per case)**,
predicting a *target-PC architectural trap* from a selected bus error gives
TP/FP/FN/TN **1/1/0/1**; from an accepted cache-to-IF error,
**1/0/0/2**. The reference is RVFI trap plus handler/CSR checks, not an IF
checker compared to itself. The 20 retirements in a warm run are **not** 20
independent trials. The one bus false positive is a genuine bus error with
no resulting instruction trap, **not** a spurious bus signal. The comparison
window is approximately 60 cycles after the selected response; no field
failure rate, general detection accuracy, or hardware claim follows.

## What is in this bundle

**Three distinct verification levels:** run `python3 -B scripts/verify.py`
for fast **package/offline validation** of the public frozen evidence and
adversarial checker tests; this does not execute RTL. The
[replay workflow](.github/workflows/replay.yml) separately installs tools and
rebuilds/replays RTL on a disposable GitHub-hosted Ubuntu runner. A workflow
file alone is not a passing run: **a fresh hosted run has now passed**;
see [VERIFICATION.md](VERIFICATION.md) for its actual run, environment and
artifact evidence. **Independent human execution is still unverified.**
The original two agent replays used separate builds on the same WSL host,
not two independent hosts or human reproductions.

- Complete **current-source** [standalone raw observations](observations/results.json)
  and [whole-core raw observations](observations/core_results.json), including
  cycle-tagged events, expected versus actual fields, source hashes and
  checker counts, plus [complete isolated replay JSON and its comparison
  record](VERIFICATION.md). Unaltered [earlier observations](historical/README.md)
  with the former, incorrect generic lowRISC-style author headers are
  explicitly historical, **not** the current raw measurements. Standalone
  observations have **no architectural trap** and are not included in the
  RVFI comparison above.
- Four small [original experiment files](experiment/) (two runners, one cache
  testbench, one six-word RV32I VMEM), the [minimal opt-in Simple System patch](patches/simple-system-fetch-fault.patch),
  an [exact upstream commit](UPSTREAM_COMMIT), [source manifest](SOURCE_MANIFEST.json),
  our [license](LICENSE)/[notice](NOTICE) and the upstream
  [Apache-2.0 license and NOTICE](upstream-notices/) for attribution. **No
  complete Ibex RTL tree, compiled binaries, waveforms, installed tool
  bundles, or the source Ibex worktree's Git history are included.**
- [Reproduction instructions](REPRODUCE.md), a deterministic
  [staging check](scripts/stage.py), [raw-event comparison](scripts/compare.py),
  and [release/privacy review](REVIEW.md).

**Authorship and rights:** The original fixture, program, runner and staging
scripts, measurements and prose are Copyright 2026 Wei-Lun Hsu (WLHsu0827),
Apache-2.0, as explicitly authorized by the user. GitHub Copilot App assisted
experiment implementation, automation and document writing; these runs were
agent-executed, **not** independently reverified by the applicant by hand.
Ibex RTL, Simple System, I-cache docs and the derivative opt-in patch retain
their upstream authorship and Apache-2.0 notices. This is a clear provenance
boundary, **not a legal opinion or lowRISC endorsement**; see
[REVIEW.md](REVIEW.md).

**Negative result and scope:** The injected warm bus error did not become
an IF error or trap; the no-error control also did not trap. Exploratory
instrumentation initially missed a same-cycle handoff and injected before
a demonstrated hit; these *discarded preliminary failures* are not raw
results. Only the corrected three-case observations are recorded. This
pilot does not cover second-halfword faults, varied wait states or
backpressure, pass-through mode, ECC, PMP, cache invalidation races,
repeated errors, other program streams, or physical devices.

**Different future hypothesis (untested):** Data-side misaligned loads
with controlled grant stalls might show a predictable relationship
between granted data-bus beats and RVFI load retirement latency. A new
fixture, controls, and prior-art review are necessary. **No data for that
second question are presented here.**
