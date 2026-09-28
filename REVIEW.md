# Publication provenance and research boundaries

Wei-Lun Hsu (WLHsu0827) has confirmed authority to release and license
the **original** experiment code, scripts, data and writing under
Apache-2.0. They approved the stated authorship, GitHub Copilot App
assistance, and this separate public research repository after the local
contents/provenance check. These materials do not constitute an
upstream Ibex pull request, CLA submission, independent human rerun or
academic paper. This is a provenance record, **not legal review or advice**.

## Contents, authorship and third-party boundary

- This folder's root [LICENSE](LICENSE) is the Apache License, Version
  2.0; [NOTICE](NOTICE) credits Copyright 2026 Wei-Lun Hsu and discloses
  GitHub Copilot App assistance in experiment implementation, automation
  and documentation. The original `experiment/` files, scripts,
  measurements (including immutable historical JSON) and prose are under
  this license. The three source-code experiment files and VMEM now
  carry Wei-Lun Hsu SPDX headers, not generic lowRISC copyright.
- [UPSTREAM_COMMIT](UPSTREAM_COMMIT) pins Ibex to
  `7cd891ef267e8db36813b29cb8851142ab2636d5`. The two-file
  [patch](patches/simple-system-fetch-fault.patch) changes only the
  upstream Simple System core description and RTL behind a default-off
  switch. Its *applied files* keep their lowRISC/SPDX headers. Derivative
  material remains under Apache-2.0; the full upstream
  [LICENSE and NOTICE](upstream-notices/) are preserved separately,
  without attributing the author's original fixture to lowRISC.
  No upstream RTL tree, object history, binaries, waveforms, packages,
  other students' work, classroom ROM, ASUS data or #1364 changes are
  in this repository. No lowRISC endorsement is claimed.
- [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records source/patched
  file hashes; current [raw JSON](observations/) and [independent
  replay JSON](verification/) were generated **after** changing source
  headers. Earlier [historical JSON](historical/README.md) is preserved
  unchanged and never silently treated as a current-code measurement.
  See [VERIFICATION.md](VERIFICATION.md) for exact case/binary differences.

## Audit and release provenance

Run `python3 scripts/audit.py` here. It checks the exact file allowlist,
binary/size limits, absolute local paths, token-like strings and email
literals; checks corrected source headers, current fixture/manifest/raw
hashes, archived historical byte hashes, the patch hash, and the
Apache/Ibex notices. If run from a newly initialized, independent
repository it excludes `.git` internals from the file scan but checks
local Git email identity and reachable commit messages/author metadata
against the approved noreply identities. A zero-flag scan is **not** a legal
opinion, a guarantee against unidentified secrets or a complete review of
all possible repository metadata. The publication check must review the
exact files and Git metadata, not only this scanner. Independent human
test execution has **not** occurred.

The source Ibex **worktree Git history contains automatically configured
corporate author email**. That Git history was **not imported**: this
standalone repository was created from the 29 bundle files in a new
empty directory, with zero inherited commits/remotes before its first
commit. Only the publication-status documents and `.gitattributes` whitespace
policy changed in this standalone copy; source, observations, historical
records, patch, pin, manifest and upstream notices retain the candidate's
exact bytes. The local author identity was set only in the new repository:

```sh
git init -b main
git config --local user.name 'Wei-Lun Hsu'
git config --local user.email "$(printf '%s%c%s' '151040862+WLHsu0827' 64 'users.noreply.github.com')"
python3 scripts/audit.py
git rev-list --all --count  # Was zero before the first new commit.
```

`151040862` is the publicly provided account ID, **not** a check of
the user's private Git/GitHub settings or a guarantee about account
email configuration. The original Ibex branch must not be pushed in
place of this repository; verify the new repository's author and
reachable commit history with every release. No user's global Git
configuration was changed.

**Local packaging rehearsal:** only the private candidate's 29 text files were
copied to an ignored test directory, with **no original `.git`**. A new
local repo was initialized there with zero commits/remotes and the
above *repository-local* noreply identity, all files staged, and the
19 hash-protected source/JSON/patch/notice files were verified
byte-for-byte against the staged Git blobs. The candidate audit and
current JSON comparator ran successfully from that copy. Its staging
script also applied the expected patch and fixtures to a third clean
pinned checkout; that third checkout was **not** built or replayed.
This preliminary rehearsal itself did not test publication or a fresh
tool installation.

**Still unverified:** fresh installation of the versioned toolchain,
execution on a different OS/host or CI, license/legal review by counsel,
or independent human execution of the RTL tests. The
public-network **upstream Ibex dependency clone itself was exercised**;
hosting this repository does not establish upstream Ibex endorsement.
