# Reproduce from this repository

All paths in these commands are relative to **this directory**, not the
original Ibex worktree. Only `experiment/`, `observations/`, `verification/`,
`historical/`, `patches/`, `scripts/`, `UPSTREAM_COMMIT`, `SOURCE_MANIFEST.json`,
license/notice and docs belong to this repository. Keep the full Ibex
checkout, its `.git`, builds, JSON replays
and waveforms **outside this directory**.

## One-command package verification (no RTL or EDA installation)

```sh
python3 -B scripts/verify.py
```

On Windows with the Python launcher, use `py -3.12 -B scripts\verify.py`.
This audits source/provenance and frozen byte hashes, compares the **existing
public** replay JSON, and runs standard-library `unittest` checks. Positive
fixtures are frozen evidence, not freshly simulated RTL. Negative fixtures
are tiny temporary copies: missing/extra/duplicate cases, required source
hashes, RVFI/CSR results, classifications, event order/cycles, failure flags,
and staging refusal must fail. No tool download or local RTL build occurs.
`-B` keeps bytecode out of the exact package allowlist.

## Automated fresh installation and RTL gate

[`.github/workflows/replay.yml`](.github/workflows/replay.yml) has separate
package/offline and fresh-RTL jobs. The latter uses GitHub-hosted Ubuntu
24.04, Python **3.12.3**, apt Verilator **5.020-1**, g++-13 **13.3.0**, GNU
make **4.3**, FuseSoC **2.4.3**, Edalize **0.6.8**, and apt `libelf-dev`.
Installed Debian package revisions (including libelf and compiler revisions)
and the complete resolved Python package list are captured, not inferred
from this specification. It requires exact tool-version checks before replay.

The upstream checkout is in the runner's separate temporary dependency
directory, pinned and hash-checked by `stage.py`, with `core.autocrlf=true`
set **only there**. Both models are freshly built without a restored
compiled cache. Standalone already caps Verilator at `-j 2`; for the
Edalize 0.6.8 Verilator backend, the supported **`--make_options=-j2`**
caps the nested compilation make, and `MAKEFLAGS=-j2` also caps the
outer make. `--setup --build` alone does **not** specify a thread limit.
The job checks the installed backend help before using that option.

The fresh job requires both three-case replays, default-off lint, strict
comparison and final audit to exit zero, within 35 minutes. Only bounded
public JSON and log tails are uploaded for 14 days: environment and commits,
command/exit/timeout records, replay JSON/hashes, and success summary (only
after every required step passes). Runner checkout/home paths are redacted;
logs are capped at 200,000 bytes per command. No compiled binaries, tool
bundles, VCD/FST or upstream checkout are uploaded. Newly generated data stay
in run artifacts, never in `observations/`, `verification/` or `historical/`.
The installer explicitly refuses execution outside a GitHub-hosted Linux
runner; it is not a local installation entry point.

See [VERIFICATION.md](VERIFICATION.md) for **actual run evidence**. Automated
fresh-host reproduction and independent human reproduction are different
claims; neither package tests nor a newly added workflow prove either one.

## Inputs and execution environment

- Upstream Ibex pin: [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT) =
  `7cd891ef267e8db36813b29cb8851142ab2636d5`. `scripts/stage.py`
  refuses a different commit or a dirty checkout and verifies fixture,
  upstream and patched source bytes against the
  [source manifest](SOURCE_MANIFEST.json); `scripts/audit.py` cross-checks
  the manifest against the [new recorded raw JSON](observations/). Preserve the
  bundle's [`.gitattributes`](.gitattributes): its `-text` entries keep the
  experiment files' recorded CRLF bytes and JSON/patch/pin LF bytes unchanged
  across future Git checkouts (including Linux clones). The same paths set
  `whitespace=-blank-at-eol` so an unqualified `git diff --check` does not
  mistake their preserved CRLF or upstream license/nested patch formatting
  for new whitespace errors; all other files retain normal whitespace checks.
  Historical JSON has old fixture hashes and is **not** used as the current
  replay reference.
- Recorded environment: **Ubuntu 24.04.5 LTS (WSL2)**, Python **3.12.3**,
  Verilator **5.020** (Debian `5.020-1`), FuseSoC **2.4.3**, Edalize **0.6.8**,
  `g++` **13.3.0**, GNU make and libelf development headers/library. No UVM/VCS
  license. An independently installed toolchain should expose `verilator`,
  `fusesoc`, `g++`, `make` and Python on `PATH`, and provide libelf headers
  and a linkable library.
  These are the historical same-host tool versions. The fresh hosted gate
  has a separate execution record in [VERIFICATION.md](VERIFICATION.md).
- For the **previously provisioned tools on the originating WSL host only**,
  set `TOOLS_ROOT` to the absolute path of that host's *ignored*,
  versioned execution-tools directory **outside this bundle**, then run before replay
  (normal system installations do not need these overrides):

  ```sh
  TOOLS_ROOT="${TOOLS_ROOT:?supply the host's tools directory}"
  export VERILATOR_ROOT="$TOOLS_ROOT/verilator/usr/share/verilator"
  export PYTHONPATH="$TOOLS_ROOT/pydeps"
  export PATH="$TOOLS_ROOT/verilator/usr/bin:$TOOLS_ROOT/pydeps/bin:$PATH"
  export CPATH="$TOOLS_ROOT/libelf-dev/usr/include"
  export LIBRARY_PATH="$TOOLS_ROOT/libelf-dev/usr/lib/x86_64-linux-gnu"
  ```
- Both simulators use immediate instruction grant and one-cycle response
  latency. The standalone target is `0x00001000`; full core executes the
  VMEM target NOP at `0x00100100`. The full-core negative control has the
  same warm cache state and timing but no selected error. Each runner checks
  actual measurements against expectations; the architectural truth is
  independent RVFI trap/retirement, handler activity and exception CSRs.

## Assemble a clean, isolated upstream checkout

From this bundle's root in a Linux shell, create a **separate local
checkout**. The following public clone is a *read-only dependency fetch*;
it does not modify this repository or publish an upstream Ibex change:

```sh
BUNDLE="$(pwd -P)"
REPLAY_DIR="${REPLAY_DIR:-$(dirname "$BUNDLE")/ibex-fetch-replay}"
git clone --no-checkout https://github.com/lowRISC/ibex.git "$REPLAY_DIR"
git -C "$REPLAY_DIR" config --local core.autocrlf true
git -C "$REPLAY_DIR" checkout --detach "$(cat "$BUNDLE/UPSTREAM_COMMIT")"
python3 "$BUNDLE/scripts/stage.py" --checkout "$REPLAY_DIR"
```

Choose a new `REPLAY_DIR` (or remove only a previously inspected throwaway
checkout) before retrying: `stage.py` deliberately refuses a dirty tree.
`core.autocrlf=true` is **local to the throwaway checkout** and reproduces
the recorded Windows/WSL source bytes; a default LF-only clone could be
semantically equivalent but fail the recorded *bytewise* source hash
comparison. It does not change this repository's files or their notices.
The script applies only the two-file Simple System patch and copies only
`experiment/{tb.sv,run.py,run_core.py,core_program.vmem}` to
`$REPLAY_DIR/dv/verilator/icache_fetch_fault/`. It does not copy any
observations as test input or take compiled artifacts from the old
worktree.

## Rebuild, replay, and compare

Continue in that isolated checkout with the **commands below**, in
order. All generated outputs are inside its ignored `build/` folder:

```sh
cd "$REPLAY_DIR"
export MAKEFLAGS=-j2
python3 dv/verilator/icache_fetch_fault/run.py --trace \
  --output build/fetch_error_pilot/replayed_cache.json
fusesoc --cores-root=. run --target=sim \
  --work-root=build/fetch_error_pilot/system_pilot --setup --build \
  lowrisc:ibex:ibex_simple_system --make_options=-j2 --ICache=1 --FetchFaultPilot=1
python3 dv/verilator/icache_fetch_fault/run_core.py \
  --output build/fetch_error_pilot/replayed_core.json
fusesoc --cores-root=. run --target=lint \
  --work-root=build/fetch_error_pilot/lint_default --setup --build \
  lowrisc:ibex:ibex_simple_system --make_options=-j2 --ICache=1
python3 "$BUNDLE/scripts/compare.py" \
  --cache build/fetch_error_pilot/replayed_cache.json \
  --core build/fetch_error_pilot/replayed_core.json
python3 "$BUNDLE/scripts/audit.py"
```

Both experiment runners use their location under `dv/verilator/icache_fetch_fault/`
to find **this** isolated Ibex checkout. `run_core.py` checks that the
compiled Simple System was built from the staged source; it does not reuse
the original worktree's binary. `compare.py` requires all cases, source
hashes, full cycle-tagged events and bus/IF/RVFI classifications to agree
with the unabridged raw JSON. It reports separately whether the compiled
binary SHA-256 and JSON bytes match; matching waveforms or a new
installation are *not* inferred from that comparison alone. The standalone results have
`trap_observed: null`, so do not count them as independent architectural
trials.

**Replay environment caveat:** the public-network upstream clone and pinned
checkout were exercised on the originating Windows/WSL host. System
`verilator`/`fusesoc` were not installed; only the **execution tools** were
temporarily provided from another ignored `build/fetch_error_pilot/tools/`
directory in this Ibex worktree; this included a separately provisioned
libelf development header/library after an initial missing-header build
attempt. Their packages, old build
products, source checkout, and Git history were **not** copied into this
repository or the staged source. The independent upstream checkout and its
fresh build outputs are distinct. A fresh tool installation or a separate
host/OS was not exercised by those historical runs. Hosted execution is
recorded separately in [VERIFICATION.md](VERIFICATION.md); see
[REVIEW.md](REVIEW.md) for provenance boundaries.
