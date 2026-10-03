# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
.section .text
.option norelax
.option norvc
.globl _start, drain, terminal
_start:
  addi x20, x0, 0
  addi x8, x0, -1
back_ceq:
  addi x8, x8, 1
  addi x20, x20, 1
.option rvc
  c.beqz x8, back_ceq
.option norvc
  addi x8, x0, 3
back_cne:
  addi x8, x8, -1
  addi x20, x20, 1
.option rvc
  c.bnez x8, back_cne
.option norvc
  addi x10, x0, 0
  addi x11, x0, 1
back_eq:
  addi x10, x10, 1
  addi x20, x20, 1
  beq x10, x11, back_eq
  addi x10, x0, 3
  addi x11, x0, 0
back_ne:
  addi x10, x10, -1
  addi x20, x20, 1
  bne x10, x11, back_ne

  addi x8, x0, 0
.option rvc
  c.beqz x8, forward_ceq_taken
.option norvc
  addi x20, x20, 101
forward_ceq_taken:
  addi x8, x0, 1
.option rvc
  c.beqz x8, forward_ceq_not_taken
.option norvc
  addi x20, x20, 2
forward_ceq_not_taken:
.option rvc
  c.bnez x8, forward_cne_taken
.option norvc
  addi x20, x20, 103
forward_cne_taken:
  addi x8, x0, 0
.option rvc
  c.bnez x8, forward_cne_not_taken
.option norvc
  addi x20, x20, 3
forward_cne_not_taken:
  addi x10, x0, 5
  addi x11, x0, 5
  beq x10, x11, forward_eq_taken
  addi x20, x20, 107
forward_eq_taken:
  addi x11, x0, 6
  beq x10, x11, forward_eq_not_taken
  addi x20, x20, 4
forward_eq_not_taken:
  bne x10, x11, forward_ne_taken
  addi x20, x20, 109
forward_ne_taken:
  addi x11, x0, 5
  bne x10, x11, forward_ne_not_taken
  addi x20, x20, 5
forward_ne_not_taken:
drain:
  addi x0, x0, 0
  addi x0, x0, 0
  addi x0, x0, 0
terminal:
  jal x0, terminal
