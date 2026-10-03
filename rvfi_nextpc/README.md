# RVFI next-PC: new memory-admission inputs UNVALIDATED

**New user-authorized memory-admission epoch: NOT_QUALIFIED; preparation1/4
STOP, zero new program/CPU builds.** The accepted stable-tools **OFF-QUALIFICATION
STOP / NOT_QUALIFIED** below remains immutable and is not requalified.
[`MEMORY_ADMISSION_AUTHORIZATION.json`](MEMORY_ADMISSION_AUTHORIZATION.json)
quotes the exact new user selection relayed by the coordinator. The continuation
turn began 2026-10-03 16:57:35.079 UTC+8; that is **not** the exact approval
timestamp. New bounds: four total preparations, one conditional pair; no old
unused slots. PR3 remains draft and every old raw/status/auth/manifest/console
gap is preserved.

Preparation1 [37117670041](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37117670041)
consumed one attempt on input `6342f9fe8e92738f5fa01e6d11a4bcf60983a815`.
Stage65 actual miniature lint exited1: new pre-transfer observer read async
reset in a posedge-only process, producing fatal `SYNCASYNCNET`. Its original
raw/status/source/console bytes are retained unchanged; no warning waiver
or DUT edit. The revised observer uses the same async reset domain explicitly,
emitting P only at real rising clocks (reset assertion occurs with clock low).
All final-source gates must requalify; prior tool/loader gates cannot substitute
for the new full preparation. No program/freeze/CPU/pair attempt has occurred.

### Preregistered admission `nonmemory-nextpc-v2`

This is strict next-PC observation on a fixed independently decoded **non-memory
ISA path**, with independently observed no-data-request/transaction controls.
It is **not full memory-RVFI verification**. All four-bit read masks are retained,
domain-checked, compared between readers and reported descriptively; there is
no observed-value whitelist, erase, normalization, or memory metadata PASS.
Write masks, unsupported/load/store opcodes, privilege, trap/halt/intr,
IRQ/debug and write/control/alert predicates remain strict. The new parser
requires an explicit v2 header and cannot admit/requalify the old rejected TSVs.

Pinned stock
[`ibex_core.sv:2092-2093`](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/rtl/ibex_core.sv#L2092-L2093)
gates masks by `data_we_o`, not `data_req_o`, and
[`2259-2267`](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/rtl/ibex_core.sv#L2259-L2267)
maps type00 to mask15. The referenced
[`riscv-formal check:160-175`](https://github.com/SymbioticEDA/riscv-formal/blob/4f29e83a8387a81467716548f165fd97045af617/checks/rvfi_insn_check.sv#L160-L175)
requires spec-needed read bits, not that extra read bits be zero. This justifies
a **new** admission scope, not a claim that the old stricter gate passed or that
extra read-mask bits prove architectural access.

`S` identifies schema/reader/admission, `P` captures settled pre-transfer
controls, `Q` post-rising-eval C++ versus falling-edge SV controls/retirements.
C++ reads exported real ports before rising and after eval; the separately
stock-top-bound SV observer reads controls at rising active/pre-NBA and falling
edges plus initial async reset. Neither reconstructs the other's stream.
Requests even without grant, grant/response without a request, writes,
data-error/alerts and IRQ/debug are forbidden at both observed phases. Idle
byte-enable/address/write-data information is retained/domain-checked without
equating it to a transaction. Initial reset-before-clock and complete pre/post
phase sequencing are mandatory; SV's extra async reset sample is explicit.
Dynamic retirements join by order/PC/instruction and all fields, not cycles.
This covers the sampled synchronous phases, not every simulator transient,
and both readers still share one simulator/DUT.

Hosted actual-module negatives include independent pre-only and post-generated
requests, spurious grant/response, writes/errors/alerts/IRQ/debug, non-memory
encoding rejection despite zero masks, write masks and retirement flags,
reset failures and actual marker+hang timeout. Legal extra masks1/5/15 must
remain raw and descriptively reported. Offline contracts additionally check
all16 read values, malformed/missing/truncated phases/domains, disagreement and
unchanged strict ISA/path/writeback/next-PC requirements.

### Actual recursive driver qualification

Explicit supported make assignments bind `CXX` **and `LINK`** to
`/usr/bin/g++-13`, `CC` to gcc-13, AR to ar, Python/perl helpers and empty
OBJCACHE, with recursive `-j1`/NUM_JOBS1. New preparation exercises the actual
installed Verilator5.020 `verilated.mk` and generated miniature recipe,
retaining original recipe bytes and make-expanded variables. Wrong aliases,
unbound LINK, missing/truncated receipts and multiworker flags fail closed.
Resolved driver/helper bytes/versions, GCC-reported compiler/assembler/linker
subtools and installed Verilator include code/recipes bind preparation,
pair and freeze exactly. Actual model compile/link commands and generated
model recipe are retained after the sole build. No installed/generated stock
recipe or launcher is edited. This is bounded driver/input provenance,
**not universal OS, system-header, shared-library or toolchain closure**.
The supported isolated FuseSoC module and original unused launcher checks
remain mandatory. Each run-local generated recipe is independently validated
and retained; its user-source paths legitimately differ between runs, while
active drivers and installed recipes bind exactly without generic normalization.

## Accepted closed stable-tools OFF-QUALIFICATION STOP

**OFF-QUALIFICATION STOP / NOT_QUALIFIED: one OFF CPU build/run; ON NOT_RUN.**
The new stable-tools preparation and actual entrypoint binding passed. One
fresh program was compiled and frozen before OFF. The OFF process exited 0
at its explicit four-terminal-record boundary, but the unchanged strict
checker rejected `rvfi_mem_rmask=15` from order 1. It stopped before ISA and
next-PC qualification; no completed qualified OFF/ON pair, next-PC PASS/FAIL,
positive/negative anomaly result or architectural conclusion is claimed.
PR3 remains draft/open/unmerged; coordinator acceptance is separate.
Archive integrity, synthetic qualification and descriptive raw counts are
not a waiver of the failed gate. No source/tool/oracle changes or retry
followed OFF compilation.

## Stable-tools epoch: immutable terminal STOP

At 2026-10-03 11:46:59 UTC+8 the coordinator relayed the user's reply
"可以 開始吧" approving the stable-entrypoint repair, requalification and
bounded hosted replay phase. [`STABLE_TOOLS_AUTHORIZATION.json`](STABLE_TOOLS_AUTHORIZATION.json)
records a distinct epoch, `WLHsu0827-2026-10-03-rvfi-nextpc-stable-tools-1`.
The established conservative **four total preparations / one conditional
OFF/ON pair** bounds are retained, not claimed as a newly selected expansion.
Both older epochs remain closed; all prior evidence and collection limitations
are untouched. This epoch consumed **1/4 preparations and 1/1 pair dispatch**,
with no reruns. It is now closed; unused preparation slots cannot authorize
another pair/window. The prior PRE-CPU STOP is preserved below as history,
not the current build count.

| Identity/stage | Exact value/result |
| --- | --- |
| Qualified/attempted source | `e2cede4e8b89dba481665fdcda370e1e9d9aebaa` |
| Stable-tools evidence archive | `bdc93ceefebbdde0c4352beaf5ebb59c5db9ae00` |
| [Preparation 1](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37094924126) | All 56 stages PASS, 37 hosted stdlib contracts, loader/actual sampler/reset miniature, both stock bind lints and generated build command checks |
| [Sole pair](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37095066929) | 64 stages; fresh program/freeze, one OFF build/run; strict OFF rejection; ON not started |
| OFF process | Build exited 0 in 13.3508 seconds; run exited 0 in 0.00624 seconds, `NEXTPC_COMPLETE terminal_records=4 cycles=99`; bounded receipts, not performance claims |
| OFF actual raw streams | 63 retirement records each, complete fields identical, 99 C++/100 SV control samples; not official sampler qualification PASS |
| OFF rejected field | `rmask=15` on all 63 records, including first order 1 / PC `0x80000080` / instruction `0x00000a13` |
| OFF control/ISA/next-PC gates | Memory-mask predicate rejected; ISA/next-PC qualification not reached, NOT_QUALIFIED |
| ON | No compile-start receipt, model, run or stream; NOT_RUN |

No interrupt/debug/trap/halt field is nonzero in the retained raw samples.
The C++ run's data-request/alert guards did not fire. Nevertheless, the
preregistered mask predicate rejects and was **not** weakened. Pinned public
[`ibex_core.sv:2088-2093`](https://github.com/lowRISC/ibex/blob/4dd3932a36b5af5ac002bddbe16a1b4ead1a6fd8/rtl/ibex_core.sv#L2088-L2093)
captures the read mask from `data_we_o ? 4'b0000 : rvfi_mem_mask_int`;
this supports reviewing the checker/metadata-contract boundary in a separately
authorized future phase, not an architectural-memory-access or new-bug claim.
There is no posthoc permissive checker, record filtering or metadata result.

The pre-OFF frozen path has **63 retirements / 18 branches**, with all eight
width/direction/outcome cells. Descriptive counts decoded independently from
actual OFF instruction bits and retired operands have the same counts below;
they are **unqualified raw diagnostics**, not ISA/next-PC acceptance:

| Width | Direction | Not taken | Taken |
| --- | --- | --- | --- |
| 16 | backward | 2 | 3 |
| 16 | forward | 2 | 2 |
| 32 | backward | 2 | 3 |
| 32 | forward | 2 | 2 |

All raw records are retained: 56 program, 3 explicit RV32 NOP drain, 4 terminal
`jal x0,0` records; boot `0x80000080`, drain `0x8000011c`, terminal `0x80000128`.
Fresh image: 172 bytes, SHA256
`58d63f5b5ae10fa1cb759dcb674b0e91e27338a8b404cc8c193af0b4d737266d`.
Fresh ELF: 1280 bytes, SHA256
`33ac01e94d46005de0ca1ac1cf2bb8c866794124ca758ef043c3730d932be46a`.
Exclusive freeze: 44744 bytes, SHA256
`0b2d303265b2b4c33810ee961920a60bfc409aaf1e924e0a233a9fc6e664bc24`.
Every frozen prior receipt remains byte-identical after the run; hashes alone
do not prove trusted timestamps or human replication.

[`evidence/STABLE_TOOLS_INDEX.json`](evidence/STABLE_TOOLS_INDEX.json) records
machine-computed statuses, artifact/raw/console identities, active entrypoint,
raw-only counts and limitations. Its authorization identity uses the actual
immutable Git LF blob (3002 bytes, SHA256
`8ca24e4dc4b743bedbd4ba7f39ee3d3be5f8039e01861da3e1587e23297ab65d`),
equal to both hosted snapshots, not local CRLF working bytes. Each new archive
has all 33 source snapshot members equal to its input Git blobs.
Preparation manifest: 36319 bytes / 241 members, SHA256
`c849f7f161d6b16fc6ba888f322871c2097d642bde0a56bf3b258d63aae5d7d3`.
Pair manifest: 41484 bytes / 276 members, SHA256
`baf900a5eabfa5b23642707c9e8941e0e9ada2567382115deb11630dc5e73edb`.
The unchanged terminal traceback is 1196 bytes, SHA256
`b028ac93d23160c427691573061ff02666b8ee613040eb9638c4599f1af09ea7`;
complete original pipeline-step console is separately retained (1695 bytes,
SHA256 `76268659f53cb508c71458542c5081c064ab0cc5b7ab90ac10dc32ab514c20e9`).
Neither is substituted for or inserted into the hosted manifest.

Pinned FuseSoC 2.4.3 has no package `__main__`, but public
[`fusesoc/main.py`](https://github.com/olofk/fusesoc/blob/2.4.3/fusesoc/main.py)
explicitly supports `__main__` and its distribution declares
`fusesoc.main:main`. The active command is the resolved qualified venv Python
with **`-I -B -m fusesoc.main`**, not its generated console-script launcher.
New hosted gates exercise that exact CLI (`--version`, help and actual setup).
Receipts bind interpreter bytes, CPython version, module bytes, exact locked
distribution and installed package code, source/config identities and command.
`-I` excludes caller Python-path/user-site overrides. No active identity is
normalized or exempted.

The preparation/pair/off active receipts agree exactly: CPython 3.12.3 binary
8020928 bytes / SHA256
`e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f`,
FuseSoC module 23564 bytes / SHA256
`f427929f52aac67c80a9c8e070d41bf19e651ce82bb17974fadbe23d5dbf9d53`.
The two retained **new** launchers are each 213 bytes:
preparation SHA256 `d4f4dcb6c4f5f178af74081e1ff3fc446e7c02a481e8c0e4e4b08bd615714fd2`,
pair SHA256 `30e04f940176ff6a75afc54cb15e20b899865dd7406fb74119f4c90ae0d32506`.
Their original bytes demonstrate only the new run-specific shebang difference;
their exact common 165-byte body is unchanged. This does not retroactively
prove anything about the unretained old 240-byte launchers.

The **unused** generated launcher is still retained as original text with
its full length/SHA256, exact shebang, active interpreter path/resolution and
public pinned pip-template provenance. Its body must match the exact
pip 25.3 `PipScriptMaker` body; unrelated edits, invalid paths/resolution,
missing/duplicate/truncated receipts and active identity changes reject.
Only the explicitly qualified per-run venv path in this unused diagnostic
may differ across runs. New launcher bytes cannot prove the missing old bytes.
The pinned runtime installer is explicitly upgraded to locked pip 25.3
before creating these diagnostics. Runtime24/build52 closure pins are unchanged.

The remaining execution-path audit also found that Edalize 0.6.2 joins
`verilator_options` into a make shell command: the former multiword CFLAGS
were unquoted in the exported `config.mk`. The new harness core quotes the
single CFLAGS argument and checks actual exported shell parsing before
measurement, without adding a warning waiver. Fresh ELF class/ISA/entry,
allocated text versus objcopy image and unique boot/drain/terminal symbols
now fail closed before freezing. No program/RTL has been compiled locally.
Pure-stdlib contracts cover both repairs, all three authorization epochs,
malicious identity/input changes and immutable Git versus CRLF receipt bytes.
All locked 24-runtime/52-build closures, actual package/executable versions,
176-source manifests and OFF/ON effective config equivalence requalified.
Only BranchPredictor differs. The generated stock recursive link command uses
the `g++` alias; its command is retained, but that alias was not independently
hashed beyond the recorded `g++-13` compiler identity. No broader complete-tool
identity claim is made. No binaries/models/waves/build trees or full job
environment dumps are published, except the expressly allowed fresh program
ELF/image.

## Closed recovery-1 PRE-CPU STOP and immutable identities

| Identity/stage | Actual result |
| --- | --- |
| Final qualified/attempted input | `8afa40840e9ff469a2a74713d12c01154f2471df` |
| Distinct recovery evidence archive | `6491399f5f139e2087c37d3581014d7f188dd7e0` |
| [Recovery preparation 1](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37064524358), input `69d0265af7f985e968eb5eabc5f687e48596d486` | STOP: unsupported gh flag combination, before tools/source snapshot; original raw bytes retained, absent snapshot not reconstructed |
| [Recovery preparation 2](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37065211892), final input | PREPARATION_PASS: all 51 stages, zero real CPU builds |
| [Sole pair dispatch](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37065546781), same final input | STOP after stage 52 successful preparation download; strict cross-run FuseSoC launcher-byte mismatch |
| Recovery attempts | 2/4 preparation dispatches, 1/1 pair dispatch; no reruns |
| Fresh program/freeze/OFF/ON | 0 program compilations, no program/ISA freeze, 0 OFF/ON CPU builds or runs |
| Actual core retirement / branch / coverage | 0 / 0 because NOT_RUN; widths/directions/outcomes NOT_MEASURED |
| Instrumentation-only results | 26 hosted stdlib contracts, 11 actual shared-loader cases, independent three-retirement miniature and reset negatives PASS; fatal-warning stock bind lint PASS OFF/ON |

The epoch is closed. Unused preparation slots do **not** authorize another
pair, runner/window, retry or refreeze. No source/tool/oracle gate was
normalized, waived or weakened to proceed.

The sole different executable identity is the **240-byte FuseSoC launcher**:
preparation SHA256
`a46ebf6e3f241c340aeed6047334c995acfb930502b91b5ba6556609c3fd82bc`
versus pair SHA256
`d268907d8eac2653b89b06fff10ce8df2a5890943c31c36446bb17cff4d1a0ae`.
Other executable identities match. Independent post-run comparison confirms
byte-identical installed runtime/build code manifests, all 176 exported
source identities per configuration, both config manifests and input
equivalence; OFF/ON exported sources/EDAM differ only BranchPredictor.
That consistency does **not** override the failed executable gate.
A run-specific virtualenv shebang is a source-supported likely explanation,
not established from the actual launcher bytes (only their hashes/lengths
were retained). Repair/requalification/replay requires a separate decision.

Stage 52 itself typed **exited:0**, with both streams empty. The subsequent
Python RuntimeError terminated the Actions pipeline with exit 1:
`STOP: qualified preparation identity changed: tool-identities.json`.
The unchanged traceback is 658 bytes, SHA256
`f7be300b8249ed668669a4f668a49f47b44ce4d2f46937bcda60bcff5d14c811`.
Complete original pipeline-step console bytes, including that terminal error
and final summary, are retained separately with collection receipts; they
are not inserted into or substituted for the original hosted manifests.
No full job/environment dump, generated tool/model binary or wave is published.

[`evidence/RECOVERY_INDEX.json`](evidence/RECOVERY_INDEX.json) records all
machine-computed run/artifact/raw/summary/console identities and actual counts.
Its derived authorization-receipt field initially used Windows working-file
CRLF bytes. A separate, non-overwriting
[`RECOVERY_INDEX_AUTHORIZATION_CORRECTION.json`](evidence/RECOVERY_INDEX_AUTHORIZATION_CORRECTION.json)
identifies this indexing error and the actual immutable Git/source-snapshot
receipt: **1607 bytes**, SHA256
`055ac91448def03127ed21a0f017fd64320df222a71fdb54cffb43ff97f67a8d`.
The original index and every hosted source/raw/status/manifest remain unchanged;
no posthoc correction is a claim about pre-run history.
Preparation-2 and pair source snapshots each match all 29 immutable public
input blobs byte-for-byte, including the hidden workflow.

Recovery raw manifest SHA256 values are:
preparation 1 `fb8537cbdfd5dfac2c14ba6d4906d354e0ccab1f099e01edeb4870f9f3875b37`
(1937 bytes, 12 members);
preparation 2 `1265e87a30f929a135ecbcb4d779ce8fa89e96b1abacfb4a9f818878a5255945`
(32926 bytes, 219 members);
pair STOP `b55807710041b72766f5c8ad99019a51f83fe87c366d42f80198a7853c606927`
(33553 bytes, 223 members).
The successful miniature alone has 3 retirements, zero branches, 20 C++/21 SV
control samples, sampler/ISA/next-PC PASS; missing-reset and reset-after-start
are prompt SIGABRT 6 plus markers, while marker+hang remains typed timeout.
These are not measured fresh-core retirement or branch counts.

## Distinct recovery authorization and input changes

Recovery preparation **1/4**:
[run 37064524358](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/37064524358),
input `69d0265af7f985e968eb5eabc5f687e48596d486`, STOP before tooling:
the new history command incorrectly combined gh `--slurp` and `--jq`.
The typed command exited 1; stdout is empty and stderr is 1578 unchanged
bytes. No install, RTL, HDL, program or CPU stage ran. The exact original
artifact is preserved under `evidence/run-37064524358`; raw-byte integrity
PASS does not imply full source collection or instrumentation qualification.
Source capture had not run yet in that attempt, so its immutable public input
commit supplies the source identity, **not reconstructed artifact members**.
The next input corrects the command to supported `--paginate`/`--jq`, parses
separate JSON page documents with complete total-count/unique-ID closure, and
captures reviewed source after exact-head/clean checks but before the history
guard. All authorization/history guards still precede every tools/HDL stage.
All affected gates still require requalification. Three preparation slots
remained at that point; the epoch is now closed by the sole pair STOP. This
failure is counted, not erased/retried.

[`RECOVERY_AUTHORIZATION.json`](RECOVERY_AUTHORIZATION.json) records the
user-directed decision relayed at 2026-10-03 04:46 UTC+8, identity
`WLHsu0827-2026-10-03-rvfi-nextpc-recovery-1`, four preparation attempts
**total** and one pair dispatch. Every created preparation run counts,
including tools-only/pre-HDL failures. Reruns, automatic retries, erased
attempts and source/counter resets are forbidden; infrastructure/resource
breaches stop the epoch. ON requires qualified OFF; CPU builds/runs are at
most once each. No harness/program/oracle/source changes or refreeze are
permitted after OFF compilation starts. No named-config extra pair, local
HDL/install, private input, DUT patch, oracle weakening or merge is authorized.
Coordinator acceptance is separate.

The complete artifact lock is [`DEPENDENCY_LOCK.json`](DEPENDENCY_LOCK.json):
the retained report's 23 exact runtime distributions plus pinned pip, with
canonical names, complete nested requirements/markers, CPython 3.12.3/Linux
x86_64 compatibility, public artifact lengths/SHA256 and license provenance.
`jsonschema2md 1.7.0` has no compatible CPython-3.12 wheel; its sdist is
retained at the original hash, not silently substituted. Its separate
52-distribution build closure includes the required Poetry plugin and Babel
2.17.0; runtime Babel remains 2.18.0. Hosted preparation inspects actual
wheel/sdist metadata before installation, installs only verified artifacts
without dependency downloads or build isolation, and independently validates
installed closure with the packaging PEP-508 parser and pip check. Public
metadata generation is stdlib-only; it does not install or execute package
source locally. License file identities are retained without author or
environment dumps. `dependencies.py --create` is a lock-authoring command,
not part of normal CI; CI only verifies the frozen lock.

Source review also corrected FuseSoC's explicit work directory and stock
first-order contract (reset order 0 is incremented before the first RVFI
retirement, so the first observed order is **1**). Actual shared C++ loader
negative contracts must qualify on the hosted runner before CPU work.
Host G++13 package 13.3.0-6ubuntu2~24.04.1 / executable 13.3.0 and Make
4.3-4.1build2 / executable 4.3 are explicit, not silent compiler substitutes.
All actual package/executable identities and installed Python code hashes
must match the same-source successful preparation before the pair.
Real build bounds are tightened to 1400 seconds each (below the original
1500 ceiling), with 60 seconds/20000 cycles per run, a 57-minute pipeline
deadline and a 60-minute job. Pair admission reserves both worst-case builds,
both runs and closure before OFF. Compilation explicitly selects G++13 and
one worker, including recursive make.

## Preserved original authorization STOP

**Original epoch PRE-HDL STOP / NOT_QUALIFIED: zero real CPU builds.** Both
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
Ibex boots at +0x80). The first RVFI record must be dynamic order 1 at the
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
identity in `RECOVERY_AUTHORIZATION.json`. GitHub run history, run-attempt=1 and an
exclusive receipt gate at most four recovery preparation-only dispatches and one pair.
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
to 1400 seconds, and the job to 60 minutes (pipeline budget 57 minutes).
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
(shown for provenance, **not to run this closed epoch again**; independent
human replay requires a new explicit scope/identity and qualification):

```sh
gh workflow run rvfi-nextpc.yml --repo WLHsu0827/ibex-fetch-error-observability --ref OWNER_BRANCH_AT_INPUT_SHA -f mode=pair -f source_sha=INPUT_SHA -f authorization=WLHsu0827-2026-10-03-rvfi-nextpc-recovery-1 -f preparation_attempt=0 -f preparation_run=SUCCESSFUL_SAME_SOURCE_PREPARATION_RUN
```

Preparation uses the same command with `mode=prepare`,
`preparation_attempt=1` (up to 4 total in the new epoch) and no
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
