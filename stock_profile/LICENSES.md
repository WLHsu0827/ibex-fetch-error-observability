# License and copyright boundary

New Python, JSON and workflow code in this package uses the repository Apache-2.0
license. `ports/embench_main.c` and `ports/embench_board.c` are explicitly
GPL-3.0-or-later, compatible with the Embench wrapper/support they would link to.
Other new port files are Apache-2.0. Linking and executable distribution have
**not** occurred and are not authorized by this preparation.

Public upstream source is downloaded only into ignored `_sources/`, with all
original copyright notices and license files intact. The public git publication
contains source references, hashes and notices, **not** benchmark source archives
or binaries. Do not relabel these sources under the owner repository license.
For unclear individual-file redistribution rights, this package distributes
references/hashes only; source or executable redistribution remains **BLOCKED
pending the applicable license review**.

| Source | License/notice |
|---|---|
| [Pinned lowRISC Ibex](https://github.com/lowRISC/ibex/tree/af456e25575013668ab56725268126f6b0feca35) and original SimpleSystem port | lowRISC contributors; Apache-2.0, original notices retained |
| [Vendored CoreMark LICENSE](https://github.com/lowRISC/ibex/blob/af456e25575013668ab56725268126f6b0feca35/vendor/eembc_coremark/LICENSE.md) | Copyright 2018 EEMBC; Apache-2.0; port also credits lowRISC and original author Shay Gal-on |
| [Embench COPYING](https://github.com/embench/embench-iot/blob/09c2ed8c3b7008c95d08b038de4a3f6dc103ed70/COPYING) | GPL-3.0-or-later overall/support and 16 selected workload directories; individual source copyright/SPDX are in the seal |
| Embench depthconv | Apache-2.0 individual source |
| Embench md5sum, tarfind | MIT individual sources; this does not make the linked GPL support Apache/MIT |
| Embench documentation | GFDL-1.2 source notices; not copied into this package |

`source_manifest.json` inventories **all** Embench files, including embedded
inputs, support, project notices, and individual source SPDX/copyright metadata.
The official verifier function location and hash are sealed separately.
CoreMark uses the bytes already vendored in Ibex, including the removed minimum
ten-second check; the lock's pristine upstream commit is not its byte identity.

Tool distributions are installed into an isolated hosted-job prefix and never
uploaded here. Their public URLs, exact versions, hashes and dependency metadata
are in the tool manifests; refer to the original distributions for their licenses
and corresponding source obligations. No employer, HFT, course, private input,
credential or private toolchain is accessed or published.
