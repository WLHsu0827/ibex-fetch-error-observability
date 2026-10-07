# Stock Ibex public workload preparation

**PREPARATION_ONLY / NO_CPU_RUN.** This is an independent preparation package,
not a working/qualified full benchmark, performance result, novel mechanism,
official score or paper-ready artifact. No CPU/program/HDL has been compiled,
linted, built or run under this authorization. No previous raw evidence,
qualification, measurement epochs or budgets are reused.

The research method is bottleneck -> complexity rewrite -> functional
preservation -> architecture tradeoff -> same-boundary whole-application
comparison. This method is attributed to a professor by user-supplied feedback;
the original correspondence was not independently verified. Only the method is
borrowed. Both earlier divider candidates are NO-GO because of direct prior art;
this package does not assume a divider bottleneck. All selected workloads are
**EXPLORATORY**, never retrospective holdouts; a future holdout needs a separate
decision.

## What can be executed now

From the owner checkout, only stdlib synthetic contracts and source sealing:

```powershell
python -I -B stock_profile\validate.py --receipts stock_profile\_receipts\local-run
python -I -B stock_profile\freeze.py
```

Use a fresh receipt directory: existing run/adapter receipts are deliberately
not overwritten. `freeze.py` fetches only the two pinned public archives and
checks their SHA-256, complete Git root tree, individual files, all 19 workload
inputs, license notices and verifier-body hashes. It writes a static external
adapter under ignored `_receipts/adapter/`; it invokes **no** HDL tools.
`--write-manifest` and `lock_tools.py` are explicit maintainer metadata-sealing
operations, not CI regeneration or compilation. They never install local tools.

The independent `stock-profile-prepare.yml` runs offline stdlib contracts and
static source checks on scoped PR changes. Only initial PR opening, explicit
`tools-presence` dispatch, or the owner repair label
`stock-profile-tools-attempt-2` can enter the hosted install/probe stage.
The live Actions-step ledger enforces at most **two** install attempts, including
reruns; source/doc/archive-only changes do not reinstall tools. This workflow is
new on an unmerged branch, so GitHub may not register manual dispatch until it
exists on the default branch; PR events are the current entry point. No default
branch change or merge is needed for preparation publication.
Final offline jobs use the runner's preinstalled Python; the fixed setup-python
binary installer is now confined to a reserved presence stage. The historical
repair-head offline job also ran setup-python (ordinary CI bootstrap, no
dependency/presence stage); its history is not erased or relabeled.

One Ubuntu-24.04 worker, 20-minute job, 5-GiB source/artifact increment and
16-MiB selected receipt caps are hard boundaries. Cap exhaustion means STOP, not
automatic expansion, retries or output-truncated success. Installed `.deb`
contents go into a job-local prefix (no system package mutation); Python uses
fixed hash-locked binary wheels and xPack uses a fixed public release checksum.
The Ubuntu snapshot is fixed to `20240425T000000Z`. jsonschema2md 1.5.2 is chosen
explicitly because it publishes a CPython-3.12-compatible pure wheel; 1.7.0 does
not. This is a preparation dependency choice, not an ISA/toolchain fallback.

Only version/package metadata, RISC-V target/multilib/sysroot/library-selection
read probes execute. FuseSoC is invoked as `python -I -B -m fusesoc.main
--version`, never setup/export/build. GNU Make and host C++ execute `--version`
only. RISC-V GCC executes metadata queries with the exact proposed
`-march=rv32im_zicsr -mabi=ilp32`; it never compiles. Missing or incompatible
libraries/options stop the presence stage, never substitute ISA, ABI or source.
Shared Ubuntu runtime dependencies are not a hermetic qualified CPU model.
The fixed Debian Verilator wrapper is version-probed with `VERILATOR_ROOT`
unset after requiring its job-local sibling `verilator_bin`; this avoids the
wrong `share/verilator/verilator_bin` lookup seen in presence attempt 1. It
does not establish a working HDL build/include configuration. Attempt 1's
original failed status and complete bounded streams are preserved, not replaced.

**Current tool boundary: BLOCKED; 2/2 presence attempts consumed.** Attempt 2
successfully version-probed Python 3.12.10, GNU Make 4.3, Verilator 5.020 and
host g++ 13.2.0, then pip refused the proposed lock: jsonschema2md 1.5.2 requires
PyYAML==6.0.2 and markdown==3.7, while the attempted lock selected 6.0.3/3.9.
The final proposed lock corrects both exact constraints and an offline regression
checks them, but **that revised lock has never been installed/probed**.
FuseSoC/Edalize imports and all RISC-V target/sysroot/multilib/libm probes were
**NOT_REACHED**. No third tool installation, local installation or gate bypass
is authorized or performed. Successful offline/archive checks cannot clear this
blocker; a new preparation decision is needed before further tool attempts.

## Configuration and external binding

`config.json` contains all **19** official small fields at Ibex
`af456e25575013668ab56725268126f6b0feca35`. The custom configuration is named
**small-observe-hpm10-40**, not default small: the only small-field difference is
`MHPMCounterNum: 0 -> 10`, keeping width 40. Observation cost is not zero or
measured. BaseIsa is **BaseIsaRV32I**, RV32E=0, RV32MFast, RV32BNone,
RV32Zca and RegFileFF; BTA/WB/cache/ECC/scrambling/prediction/trigger/security/
PMP are disabled, PMP granularity=0 and region count=4.

Upstream `ibex_config.py` emits `--BaseIsa`, whereas SimpleSystem `.core`
does not declare it and SV falls back through `BASE_ISA` to RV32IorCHERIoT.
`config.py` checks the exact three source blobs and every downstream parameter,
derives an external CAPI overlay with **all** parameters fixed, declares BaseIsa
as a vlogdefine and maps it through a small include shim to `BASE_ISA`.
The original SimpleSystem module/C++/CPU implementation bytes and hierarchy are
unchanged. No BaseIsa flag is discarded and no simplified `GetIsaString` is
used. System-only defaults (instruction delay=0, lockstep offset=1, cache tweak
infection=0, empty SRAM init) are listed explicitly in the adapter receipt.
Static mapping checks are not FuseSoC/HDL/ABI qualification: actual binding is
**NOT_VERIFIED**.

## Workload and result contract

`source_manifest.json` seals the CoreMark vendor tree
`8e634d5b42c34a6e1e049e75a7bc070c50d2326b` and Ibex port tree
`e86619e4e7bbdd084ff0ffa12cc65e7b69798eec`, not pristine upstream bytes.
The proposed fixed port is ITERATIONS=10, seeds 0/0/0x66, TOTAL_DATA_SIZE=2000
(666 per algorithm), MEM_STACK, MULTITHREAD=1. The result parser checks the
complete official known_id=3 semantics: seedcrc=e9f5, list=e714, matrix=1fd7,
state=8e3a, all expected output fields and the official validation sentence,
rejecting errors/unknown seeds/duplicates. `crcfinal` must be present and
well-formed but **has no invented expected value**. The removed ten-second
check means **selfcheck_only**, not an official compliant CoreMark score.
`CLOCKS_PER_SEC=500000` is a port conversion constant, not silicon frequency.

Embench is pinned to `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`, root tree
`b88459b702d04b50488f4ca9c4002d44657fd830`. All 19 original directories are
retained: aha-mont64, crc32, depthconv, edn, huffbench, matmult-int, md5sum,
nettle-aes, nettle-sha256, nsichneu, picojpeg, qrduino, sglib-combined, slre,
statemate, tarfind, ud, wikisort, xgboost. No dummy or DIV-heavy selection is
substituted. GSF=1 and WARMUP_HEAT=1 are explicit. Preserve the official inputs,
algorithms and verifier bodies, including their limits: md5sum calls its check
weak; xgboost's official integer/comma expression gives a zero threshold at
GSF=1. An official verifier PASS is not independent proof of full correctness.

`ports/embench_main.c` is an external main adapter that keeps the official
initialization/warmup/trigger/benchmark/verification order and reports the
**raw verifier classification** (1 verified, 0 failed, -1 not verified;
unexpected values invalidate the record). The original `!correct` and crt0
halt cannot convert -1 or missing output into PASS. The external board port
inhibits/resets/enables counters around the benchmark; no C code in `ports/`
has been compiled or executed. `ports/coremark_main.c` would wrap only the
renamed vendored framework main, leaving algorithms/inputs/port untouched;
CoreMark's unconditional main return never asserts verifier success.

The versioned completion record binds workload, the canonical-LF Git config-file SHA-256,
`selfcheck_only`, verifier state and completion. Real software output is in
SimpleSystem's **ibex_simple_system.log** (not presumed simulator stdout).
The internal runner handles stdout, stderr and a separate program log, requiring
clean bounded termination **and** a single complete valid record. A future
simulator argv template is exactly `--meminit=ram,<ELF>
--term-after-cycles=50000000 +ibex_tracer_enable=0`; it is metadata only.
`Simulation timeout of ...` is a cycle timeout even at process exit 0.

Termination types distinguish zero/nonzero exit, signal, wall/cycle timeout,
trap, spawn/capture failure, resource and output limits. Completion and
VERIFIED/NOT_VERIFIED/FAILED are separate axes. Raw stdout/stderr/program
logs are retained byte-for-byte within caps; truncated logs are explicitly
failure, never successful evidence. Real stdlib child cases cover missing,
duplicate, truncated, malformed, wrong configuration/workload, verifier -1/0/
invalid, invalid UTF-8, marker+hang, timeout-exit0, trap, signal, nonzero exit,
spawn error, wrong-channel/forged CoreMark verifier assertions, and floods in
all three streams. Linux also exercises actual
RLIMIT_CPU/RLIMIT_FSIZE, an actual RLIMIT_AS-induced MemoryError reported by
the resource-aware synthetic child, and a descendant holding output pipes. Windows cannot
enforce those POSIX resource caps; that local subset is explicitly skipped.

## Future observation is not enabled

Counter 3=data-memory wait, 4=instruction-availability wait, 5=load, 6=store,
7=jump, 8=branch, 9=taken branch, 10=compressed retirement, 11=multiply wait,
12=divide wait. These are **marginals, not proven mutually exclusive**; do not
sum them into a 100% stall decomposition. Divide wait is not DIV instruction
count. The original CoreMark port dumps only low 32-bit reads, despite 40-bit
configured HPM counters; full-width capture/overflow and common observation
boundaries still need a separately authorized implementation/qualification.
Start/stop/read/inhibit overhead and perturbation are uncalibrated.

`cpu_observation()` always raises NO_CPU_RUN, including a purported authorization
flag. There is no CLI accepting arbitrary CPU/compiler argv and no automatic
CPU workflow. A new user decision and code review are required before any
model/program build or CPU observation. The earlier proposal of 41 CPU runs
and one model build is **NOT_AUTHORIZED** and supplies no budget here.

**Blocked/untested:** actual HDL binding, program compilation, linker/startup/
libm/ABI compatibility, emitted/executed ISA, workload runtime selfchecks,
full-width counters/overflow handling, timing accuracy, overhead calibration,
same-boundary comparisons, PPA, performance/novelty/paper claims, future holdout,
and source/executable redistribution where individual rights are unclear.
Presence, static seals, synthetic contracts and artifact archival never upgrade
any of these to qualification. See `publication.json` for actual published code,
run and immutable receipt identities when available, and `LICENSES.md` for the
source/license boundary. No existing PR, archive, observation dispatch or
upstream/primary checkout is changed.
