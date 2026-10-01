# Persistent public hosted evidence (not original observations)

These small archives persist **already-downloaded public artifacts** after
GitHub Actions' 14-day artifact retention expires. Every file under a run's
`raw/` directory was copied byte-for-byte from the previously downloaded
artifact. The runner's original sanitization and log-tail limits are
preserved; no raw file was rewritten, newly redacted, reconstructed from
GitHub console text, or generated locally. No binaries, waves, installed
tools, local execution logs or private paths are included.

| Archive | Proof input bundle commit | Retained raw files / bytes | Scope |
| --- | --- | ---: | --- |
| [run-36887152817](run-36887152817/manifest.json) | `cfeeb13460b1b4efdf924666d12df79153616638` | 30 / 55,971 | Final-tip automated hosted RTL success: cache 3/3, core 3/3, lint, compare and final audit; all 24 recorded commands exit 0 |
| [run-36885980667](run-36885980667/manifest.json) | `be309fb4e54363b6f39e7e2b4401486d6a89a27c` | 23 / 34,691 | Initial failed hosted attempt: cache 3/3; whole-core pre-build hook exits 1 because `packaging` is missing |

The success proof's input remains **`cfeeb134...`**, even though the commit
publishing this archive is newer. Both runs use upstream
`7cd891ef267e8db36813b29cb8851142ab2636d5`. Their `raw/environment.json`
also preserves the distinct GitHub event/merge commit. The original
`SOURCE_MANIFEST.json`, eight original/historical observation/replay JSONs,
experiment files, upstream pin, patch and licenses/notices are unchanged.

## Original outputs versus derived archive metadata

- **Original output bytes:** `raw/commands.json`, `raw/environment.json`,
  `raw/hashes.json`, `raw/replayed_cache.json`, and `raw/logs/*.log`, plus
  `raw/replayed_core.json` and `raw/summary.json` **only for the success**.
  The existing runner-generated hashes and summary are retained as original
  artifact output, not replaced by new measurements.
- **Derived here:** each sibling `manifest.json` is clearly labeled
  `DERIVED archive provenance and byte checksums, not simulator output`.
  It records run/artifact IDs, the original input and upstream commits,
  the unchanged source manifest hash, exact per-file SHA-256/byte counts
  and aggregate raw bytes. `github_reported_zip_*` values are GitHub API
  metadata about the original ZIP, not a locally reconstructed ZIP hash.
  This README is also a derived description, not simulator output.

Manifest byte identities:

| Derived manifest | Bytes | SHA-256 |
| --- | ---: | --- |
| Success `run-36887152817/manifest.json` | 5,236 | `4890012b5d20c6e42937f7c2910bc69151889d2274913505e26a4ef1132ff46c` |
| Failure `run-36885980667/manifest.json` | 4,236 | `4d48e6cedb3da0278a88e1465496dd49e9d58b66da18221fcf86664e0f0b187a` |

The exact package audit pins these two manifest hashes, then verifies their
precise raw file inventories, lengths and hashes. It does not generally
allow arbitrary new files under `verification/hosted/`. The archive's
`-text` Git attribute preserves mixed LF/CRLF output bytes in future clones.

## Retained success, retained failure, and gaps

[Success run 36887152817](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/36887152817)
completed both package and fresh-RTL jobs. The package job ran the original
12 offline tests; its console log is **not** inside this downloaded
fresh-RTL artifact. The raw archive directly preserves the fresh job's
24 command outcomes, three cases per suite, lint, comparison and audit.
It is not a new RTL run or independent human verification.

[Initial failure run 36885980667](https://github.com/WLHsu0827/ibex-fetch-error-observability/actions/runs/36885980667)
passed package validation and the freshly built cache suite, then failed
the upstream whole-core pre-build check. **Whole-core replay, default-off
lint, strict comparison and final package audit were not executed** in
that attempt. There is no failed-run core JSON or success summary; neither
has been invented. Its existing failure log, cache JSON and failure
environment/command records are retained unchanged.

Logs are the originally uploaded, sanitized tails, at most 200,000 bytes
per command; unuploaded compiler subprocess output is not reconstructed.
This repository does not archive the GitHub action setup/cleanup console
or the full original ZIP. It preserves all 53 downloaded payload files
(90,662 bytes total), plus separately derived metadata/prose. For the
original same-host WSL measurements and the first successful hosted run,
see [VERIFICATION.md](../../VERIFICATION.md); they are not relabeled as
human execution or replaced by this newer archive.

## Offline verification, rights and attribution

From the repository root:

```sh
python3 -B scripts/verify.py
python3 -B scripts/compare.py \
  --cache verification/hosted/run-36887152817/raw/replayed_cache.json \
  --core verification/hosted/run-36887152817/raw/replayed_core.json
```

These commands validate **stored evidence only**, without EDA installation
or RTL execution. The package tests also reject changed/missing archived
bytes or changed manifests and assert that the failed attempt did not
execute the missing steps. The original source manifest and frozen byte
expectations are not weakened.

The original measurement JSON, archive provenance/checksums and prose
remain covered by this repository's [Apache-2.0 LICENSE](../../LICENSE)
and [NOTICE](../../NOTICE). Logs retain verbatim public diagnostic,
package and version output identifying upstream Ibex and the execution
tools (Verilator, FuseSoC, Edalize, GNU Make, apt and pip). Their existing
copyright/license text, including GNU Make's GPLv3+ version banner, is
preserved; this archive neither redistributes nor relicenses the tool
implementations or claims authorship of their notices. Upstream Ibex
attribution remains in [upstream-notices](../../upstream-notices/).
Publication review found only bounded text/JSON, no credential signatures,
personal email literals, private paths or redistributed tool/source trees.
This is a provenance/content review, not a legal opinion.

The same directed pilot boundaries remain: no general fault rate, novel
CPU bug, established cause of binary differences, general binary
reproducibility, or independently human-executed reproduction is claimed.
