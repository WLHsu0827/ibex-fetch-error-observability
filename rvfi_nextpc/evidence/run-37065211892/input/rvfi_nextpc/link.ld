/* SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 Wei-Lun Hsu
 */
OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
  . = 0x80000080;
  .text : { *(.text) }
  /DISCARD/ : { *(.riscv.attributes) *(.comment) }
}
